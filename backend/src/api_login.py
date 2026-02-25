import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Generator

import bcrypt
import jwt  # PyJWT
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# === Load env ===
load_dotenv()

# === Config / env validation ===
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
POOL_MINCONN = int(os.getenv("DB_POOL_MIN", "1"))
POOL_MAXCONN = int(os.getenv("DB_POOL_MAX", "10"))

REQUIRED = {
    "POSTGRES_DB": POSTGRES_DB,
    "POSTGRES_USER": POSTGRES_USER,
    "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
    "JWT_SECRET": JWT_SECRET,
}
missing = [k for k, v in REQUIRED.items() if not v]
if missing:
    raise RuntimeError(f"Missing required env vars: {missing}")

# === Logging ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("medportal-api")

# === App ===
app = FastAPI(title="MedPortal Auth API")

# CORS — adjust the origins for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # change as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === DB pool (global) ===
_db_pool: Optional[pool.SimpleConnectionPool] = None

def get_db_conn() -> Generator:
    """
    Dependency that yields a connection from the pool.
    Remember to commit/rollback as needed in handlers.
    """
    conn = None
    try:
        conn = _db_pool.getconn()
        yield conn
    finally:
        if conn:
            _db_pool.putconn(conn)


# === Pydantic models ===
class LoginRequest(BaseModel):
    doctor_id: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    password: str = Field(..., min_length=1)



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class ValidateResponse(BaseModel):
    valid: bool
    doctor_id: Optional[str] = None
    expires_at: Optional[datetime] = None


# === JWT helpers ===
def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "exp": expire, "type": "access"}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# === Utility: write audit record ===
def write_audit(conn, doctor_id: Optional[str], ip: str, user_agent: str, action: str, success: bool, reason: Optional[str] = None):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO medportal.auth_audit (doctor_id, ip_address, user_agent, action, success, reason)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (doctor_id, ip, user_agent, action, success, reason)
        )
        conn.commit()


# === App lifecycle events ===
@app.on_event("startup")
def startup():
    global _db_pool
    logger.info("Starting app and creating DB pool...")
    _db_pool = psycopg2.pool.SimpleConnectionPool(
        POOL_MINCONN,
        POOL_MAXCONN,
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        port=POSTGRES_PORT
    )
    if not _db_pool:
        raise RuntimeError("Failed to create DB pool")


@app.on_event("shutdown")
def shutdown():
    global _db_pool
    if _db_pool:
        logger.info("Closing DB pool...")
        _db_pool.closeall()


# === Health endpoint ===
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# === Login endpoint ===
@app.post("/login", response_model=TokenResponse)
def login(request_data: LoginRequest, request: Request, conn=Depends(get_db_conn)):
    """
    Authenticate doctor_id + password. Returns access + refresh tokens.
    Also writes audit logs (attempts + success/failure).
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    # Step 1: fetch user
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT password_hash FROM medportal.doctors WHERE doctor_id = %s LIMIT 1",
                (request_data.doctor_id,)
            )
            row = cur.fetchone()
    except Exception as e:
        logger.exception("DB error during login fetch")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        # record failed attempt with no doctor match
        try:
            write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_attempt", False, "doctor_not_found")
        except Exception:
            logger.exception("Failed to write audit (doctor_not_found)")
        raise HTTPException(status_code=401, detail="Invalid ID or password")

    stored_hash = row[0]

    # Step 2: verify password
    try:
        password_matches = bcrypt.checkpw(request_data.password.encode(), stored_hash.encode())
    except Exception:
        logger.exception("bcrypt error")
        # write audit
        try:
            write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_attempt", False, "bcrypt_error")
        except Exception:
            logger.exception("Failed to write audit (bcrypt_error)")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not password_matches:
        # wrong password
        try:
            write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_attempt", False, "wrong_password")
        except Exception:
            logger.exception("Failed to write audit (wrong_password)")
        raise HTTPException(status_code=401, detail="Invalid ID or password")

    # Step 3: success - create tokens, write audit, store refresh token
    access_token = create_access_token(request_data.doctor_id)
    refresh_token = create_refresh_token(request_data.doctor_id)
    access_expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    try:
        # persist refresh token in sessions table with expiry
        refresh_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO medportal.sessions (doctor_id, refresh_token, expires_at)
                VALUES (%s, %s, %s)
                """,
                (request_data.doctor_id, refresh_token, refresh_expires_at)
            )
            conn.commit()
    except Exception:
        logger.exception("Failed to save refresh token")
        # continue — token still returned but we log the failure
    try:
        write_audit(conn, request_data.doctor_id, client_ip, user_agent, "login_success", True, None)
    except Exception:
        logger.exception("Failed to write audit (login_success)")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": access_expires_in,
        "refresh_token": refresh_token
    }


# === Session validate endpoint ===
@app.post("/session/validate", response_model=ValidateResponse)
def validate_session(token: str):
    """
    Validate an access token (simple). If valid, return doctor_id and expiry.
    """
    payload = decode_token(token)
    # token contains 'sub' and 'exp'
    doctor_id = payload.get("sub")
    exp_ts = payload.get("exp")
    expires_at = datetime.utcfromtimestamp(exp_ts) if exp_ts else None
    return {"valid": True, "doctor_id": doctor_id, "expires_at": expires_at}


# === Refresh token endpoint (simple) ===
class RefreshRequest(BaseModel):
    refresh_token: str

@app.post("/token/refresh", response_model=TokenResponse)
def refresh_token_endpoint(body: RefreshRequest, request: Request, conn=Depends(get_db_conn)):
    """
    Exchange a refresh token for a new access token (and optionally a new refresh token).
    Basic checks: token validity and that it exists in sessions table.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    try:
        payload = decode_token(body.refresh_token)
    except HTTPException as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token")

    doctor_id = payload.get("sub")
    # verify refresh token exists in sessions table and not expired
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, expires_at FROM medportal.sessions WHERE doctor_id = %s AND refresh_token = %s LIMIT 1",
                (doctor_id, body.refresh_token)
            )
            row = cur.fetchone()
    except Exception:
        logger.exception("DB error during refresh lookup")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        write_audit(conn, doctor_id, client_ip, user_agent, "refresh_failure", False, "session_not_found")
        raise HTTPException(status_code=401, detail="Refresh token not found")

    session_id, expires_at = row
    if expires_at and expires_at < datetime.utcnow():
        write_audit(conn, doctor_id, client_ip, user_agent, "refresh_failure", False, "expired")
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # create new tokens
    access_token = create_access_token(doctor_id)
    refresh_token_new = create_refresh_token(doctor_id)

    # update session with new refresh token and new expiry
    new_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE medportal.sessions SET refresh_token = %s, expires_at = %s WHERE id = %s",
                (refresh_token_new, new_expires_at, session_id)
            )
            conn.commit()
    except Exception:
        logger.exception("Failed to rotate refresh token")

    write_audit(conn, doctor_id, client_ip, user_agent, "refresh_success", True, None)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh_token_new
    }
