# src/api.py
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Generator, List

import bcrypt
import jwt  # PyJWT
import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection as PsycopgConnection
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, Depends, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, constr

from src.predict import predict_resistance


# === Load env ===
load_dotenv()


# === Config / env validation ===
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
POOL_MINCONN = int(os.getenv("DB_POOL_MIN", "1"))
POOL_MAXCONN = int(os.getenv("DB_POOL_MAX", "10"))

REQUIRED = {
    "POSTGRES_DB": DB_NAME,
    "POSTGRES_USER": DB_USER,
    "POSTGRES_PASSWORD": DB_PASSWORD,
    "JWT_SECRET": JWT_SECRET,
}
missing = [k for k, v in REQUIRED.items() if not v]
if missing:
    raise RuntimeError(f"Missing required env vars: {missing}")


# === Logging ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("medportal-api")


# === FastAPI app ===
app = FastAPI(title="MedPortal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === DB pool (shared across all endpoints) ===
_db_pool: Optional[pool.SimpleConnectionPool] = None


def get_db_conn() -> Generator[PsycopgConnection, None, None]:
    """Reusable DB dependency with auto commit/rollback"""
    global _db_pool
    if _db_pool is None:
        raise RuntimeError("DB pool not initialized")
    conn = _db_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _db_pool.putconn(conn)


# === App lifecycle ===
@app.on_event("startup")
def startup():
    global _db_pool
    logger.info("Starting MedPortal API + Admin API...")
    _db_pool = psycopg2.pool.SimpleConnectionPool(
        POOL_MINCONN,
        POOL_MAXCONN,
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
    )
    logger.info("Database pool ready (%d-%d connections)", POOL_MINCONN, POOL_MAXCONN)


@app.on_event("shutdown")
def shutdown():
    global _db_pool
    if _db_pool:
        logger.info("Closing database pool...")
        _db_pool.closeall()


# === JWT helpers ===
def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# === Pydantic Models - Public API ===
class LoginRequest(BaseModel):
    doctor_id: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    role: Optional[str] = None


class ValidateResponse(BaseModel):
    valid: bool
    doctor_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class PredictionRequest(BaseModel):
    age: int
    weight_kg: float
    gender: str
    admission_date: str
    cancer_type: str
    pathogen_id: int
    antibiotic_id: int
    duration_days: int
    region: str


# === Pydantic Models - Admin API ===
class DoctorCreate(BaseModel):
    name: str
    doctor_id: constr(min_length=6, max_length=6)
    password: str
    role: str = "Doctor"
    region: str
    hospital: str
    status: str = "Active"


class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    region: Optional[str] = None
    hospital: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None


class HospitalCreate(BaseModel):
    name: str
    region: str
    status: str = "Active"


class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    status: Optional[str] = None


# === Utility: audit logging ===
def write_audit(
    conn,
    doctor_id: Optional[str],
    ip: str,
    user_agent: str,
    action: str,
    success: bool,
    reason: Optional[str] = None,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO medportal.auth_audit
            (doctor_id, ip_address, user_agent, action, success, reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (doctor_id, ip, user_agent, action, success, reason),
        )


# === Health & Root ===
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/")
def root():
    return {"status": "MedPortal API + Admin API running"}


# ============================
# PUBLIC AUTH ENDPOINTS
# ============================
# Development-only: allow demo login so you can reach Admin and set/reset real passwords
DEMO_DOCTOR_ID = "111111"
DEMO_PASSWORD = "demo"


@app.post("/login")
def login(request_data: LoginRequest, request: Request, conn=Depends(get_db_conn)):
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    # Demo bypass so you can log in and use Admin to add/reset real doctors
    if request_data.doctor_id == DEMO_DOCTOR_ID and request_data.password == DEMO_PASSWORD:
        write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_success", True)
        return {
            "access_token": create_access_token(request_data.doctor_id),
            "refresh_token": create_refresh_token(request_data.doctor_id),
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "role": "Admin",
        }

    with conn.cursor() as cur:
        cur.execute(
            "SELECT password_hash, role FROM medportal.doctors WHERE doctor_id = %s",
            (request_data.doctor_id,),
        )
        row = cur.fetchone()

    if not row:
        write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_attempt", False, "doctor_not_found")
        raise HTTPException(status_code=401, detail="Invalid ID or password")

    stored_hash = row[0]
    if not stored_hash or (isinstance(stored_hash, str) and not stored_hash.strip()):
        write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_attempt", False, "no_password_set")
        raise HTTPException(status_code=401, detail="Password not set. Use Admin to reset password.")
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")
    # Try UTF-8 first (Admin panel / API), then default encoding (create_doctor.py or older scripts)
    password_utf8 = request_data.password.encode("utf-8")
    password_default = request_data.password.encode()
    try:
        ok = bcrypt.checkpw(password_utf8, stored_hash) or bcrypt.checkpw(password_default, stored_hash)
    except Exception:
        ok = False
    if not ok:
        write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_attempt", False, "wrong_password")
        raise HTTPException(status_code=401, detail="Invalid ID or password")

    access_token = create_access_token(request_data.doctor_id)
    refresh_token = create_refresh_token(request_data.doctor_id)
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    refresh_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO medportal.sessions (doctor_id, refresh_token, expires_at) VALUES (%s, %s, %s)",
            (request_data.doctor_id, refresh_token, refresh_expires_at),
        )

    write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_success", True)

    role_from_db = row[1]
    if not role_from_db or not role_from_db.strip():
        role_from_db = "Doctor"  # fallback

    final_role = role_from_db.strip()

    print(f"LOGIN SUCCESS → doctor_id={request_data.doctor_id} → role='{final_role}'")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "role": final_role
    }

@app.post("/session/validate", response_model=ValidateResponse)
def validate_session(token: str):
    payload = decode_token(token)
    exp_ts = payload.get("exp")
    return {
        "valid": True,
        "doctor_id": payload.get("sub"),
        "expires_at": datetime.utcfromtimestamp(exp_ts) if exp_ts else None,
    }


@app.post("/token/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, request: Request, conn=Depends(get_db_conn)):
    client_ip = request.client.host or "unknown"
    user_agent = request.headers.get("user-agent", "")

    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    doctor_id = payload["sub"]

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, expires_at FROM medportal.sessions WHERE doctor_id = %s AND refresh_token = %s",
            (doctor_id, body.refresh_token),
        )
        row = cur.fetchone()

    if not row or row[1] < datetime.utcnow():
        write_audit(conn, doctor_id, client_ip, user_agent, "refresh_failure", False, "invalid_or_expired")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    new_access = create_access_token(doctor_id)
    new_refresh = create_refresh_token(doctor_id)
    new_exp = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE medportal.sessions SET refresh_token = %s, expires_at = %s WHERE id = %s",
            (new_refresh, new_exp, row[0]),
        )

    write_audit(conn, doctor_id, client_ip, user_agent, "refresh_success", True)
    return {
        "access_token": new_access,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": new_refresh,
    }


# ============================
# PREDICTION & DASHBOARD
# ============================
def log_prediction(req: dict, prediction: dict, doctor_id: str = "D00001"):
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.prediction_logs
            (doctor_id, age, weight_kg, gender, admission_date, cancer_type,
             pathogen_id, antibiotic_id, duration_days, region, result)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                doctor_id[:6],
                req["age"], req["weight_kg"], req["gender"], req.get("admission_date"),
                req["cancer_type"], req["pathogen_id"], req["antibiotic_id"],
                req["duration_days"], req.get("region"), json.dumps(prediction)
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.exception("Failed to log prediction: %s", e)


@app.post("/predict")
def predict(req: PredictionRequest):
    result = predict_resistance(
        age=req.age,
        weight_kg=req.weight_kg,
        gender=req.gender,
        admission_date=req.admission_date,
        cancer_type=req.cancer_type,
        pathogen_id=req.pathogen_id,
        antibiotic_id=req.antibiotic_id,
        duration_days=req.duration_days,
        region=req.region,
    )
    log_prediction(req.dict(), result)
    return result


@app.get("/dashboard-stats")
def dashboard_stats():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM public.prediction_logs WHERE created_at >= NOW() - INTERVAL '7 days'")
        checks_this_week = cur.fetchone()[0]

        cur.execute("""
            SELECT
                SUM((result->>'resistant')::int),
                SUM(CASE WHEN (result->>'resistant')::int = 0 THEN 1 ELSE 0 END)
            FROM public.prediction_logs
        """)
        resistant, sensitive = cur.fetchone()
        resistant_count = resistant or 0
        not_resistant_count = sensitive or 0

        cur.execute("SELECT antibiotic_id, COUNT(*) FROM public.prediction_logs GROUP BY antibiotic_id ORDER BY 2 DESC LIMIT 5")
        top_rows = cur.fetchall()
        names = {1:"Ceftriaxone",2:"Amoxicillin",3:"Levofloxacin",4:"Meropenem",5:"Vancomycin",
                 6:"Piperacillin-Tazobactam",7:"Nitrofurantoin",8:"Ciprofloxacin"}
        top_antibiotics = [{"name": names.get(i, f"Antibiotic {i}"), "count": c} for i, c in top_rows]

        cur.execute("SELECT AVG(age) FROM public.prediction_logs")
        avg_age = float(cur.fetchone()[0] or 0)

        cur.close()
        conn.close()

        return {
            "checks_this_week": checks_this_week,
            "resistant_count": resistant_count,
            "not_resistant_count": not_resistant_count,
            "top_antibiotics": top_antibiotics,
            "average_age": round(avg_age, 1),
        }
    except Exception as e:
        logger.exception("Dashboard stats error")
        return {"checks_this_week":0,"resistant_count":0,"not_resistant_count":0,"top_antibiotics":[],"average_age":0}


# ============================
# ADMIN ROUTER
# ============================
admin_router = APIRouter(prefix="/admin", tags=["admin"])


# --- Hospitals ---
@admin_router.get("/hospitals", response_model=List[dict])
def list_hospitals(conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute("SELECT hospital_id, name, region, status FROM public.hospitals ORDER BY hospital_id")
        rows = cur.fetchall()
    return [dict(zip(["id", "name", "region", "status"], r)) for r in rows]


@admin_router.post("/hospitals", response_model=dict)
def create_hospital(h: HospitalCreate, conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.hospitals (name, region, status) VALUES (%s, %s, %s) RETURNING hospital_id, name, region, status",
            (h.name, h.region, h.status)
        )
        row = cur.fetchone()
    return dict(zip(["id", "name", "region", "status"], row))


@admin_router.put("/hospitals/{hospital_id}", response_model=dict)
def update_hospital(hospital_id: int, h: HospitalUpdate, conn=Depends(get_db_conn)):
    updates, values = [], []
    if h.name is not None: updates.append("name = %s"); values.append(h.name)
    if h.region is not None: updates.append("region = %s"); values.append(h.region)
    if h.status is not None: updates.append("status = %s"); values.append(h.status)
    if not updates:
        raise HTTPException(400, "No fields to update")
    values.append(hospital_id)
    query = f"UPDATE public.hospitals SET {', '.join(updates)}, updated_at = NOW() WHERE hospital_id = %s RETURNING hospital_id, name, region, status"
    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Hospital not found")
    return dict(zip(["id", "name", "region", "status"], row))


@admin_router.delete("/hospitals/{hospital_id}")
def delete_hospital(hospital_id: int, conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM public.hospitals WHERE hospital_id = %s RETURNING hospital_id",
            (hospital_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Hospital not found")
    return {"detail": "Hospital deleted"}

# --- Doctors ---
@admin_router.get("/doctors", response_model=List[dict])
def list_doctors(conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT doctor_id, name, role, region, hospital, status
            FROM medportal.doctors
            ORDER BY doctor_id
        """)
        rows = cur.fetchall()

    # Return role exactly as stored in DB
    return [
        {
            "id": r[0],
            "name": r[1],
            "role": r[2],  # <-- keep original capitalization
            "region": r[3],
            "hospital": r[4],
            "status": r[5]
        }
        for r in rows
    ]


@admin_router.post("/doctors", response_model=dict)
def create_doctor(d: DoctorCreate, conn=Depends(get_db_conn)):
    pwd_hash = bcrypt.hashpw(d.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Normalize role before saving
    normalized_role = d.role.capitalize()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO medportal.doctors
            (doctor_id, name, role, region, hospital, status, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING doctor_id, name, role, region, hospital, status
            """,
            (d.doctor_id, d.name, normalized_role, d.region, d.hospital, d.status, pwd_hash)
        )
        row = cur.fetchone()

    return {
        "id": row[0],
        "name": row[1],
        "role": row[2],  # <-- keep DB capitalization
        "region": row[3],
        "hospital": row[4],
        "status": row[5],
    }


@admin_router.put("/doctors/{doctor_id}", response_model=dict)
def update_doctor(doctor_id: str, d: DoctorUpdate, conn=Depends(get_db_conn)):
    updates, values = [], []

    if d.name is not None:
        updates.append("name = %s")
        values.append(d.name)

    if d.role is not None:
        updates.append("role = %s")
        values.append(d.role.capitalize())  # Save with proper capitalization

    if d.region is not None:
        updates.append("region = %s")
        values.append(d.region)

    if d.hospital is not None:
        updates.append("hospital = %s")
        values.append(d.hospital)

    if d.status is not None:
        updates.append("status = %s")
        values.append(d.status)

    if d.password is not None:
        pwd_hash = bcrypt.hashpw(d.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        updates.append("password_hash = %s")
        values.append(pwd_hash)

    if not updates:
        raise HTTPException(400, "No fields to update")

    values.append(doctor_id)

    query = f"""
        UPDATE medportal.doctors
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE doctor_id = %s
        RETURNING doctor_id, name, role, region, hospital, status
    """

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Doctor not found")

    return {
        "id": row[0],
        "name": row[1],
        "role": row[2],  # <-- return as-is
        "region": row[3],
        "hospital": row[4],
        "status": row[5],
    }

@admin_router.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: str, conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM medportal.doctors WHERE doctor_id = %s RETURNING doctor_id", (doctor_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Doctor not found")
    return {"detail": "Doctor deleted"}



# === Include Admin Router ===
app.include_router(admin_router)