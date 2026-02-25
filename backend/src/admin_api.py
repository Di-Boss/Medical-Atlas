# src/admin_api.py
import os
import bcrypt
from dotenv import load_dotenv
load_dotenv()  # Load environment variables

import logging
from typing import Optional, List, Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection as PsycopgConnection
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from pydantic import BaseModel, constr

# ==========================
# Logging
# ==========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("medportal-admin-api")

# ==========================
# Environment & DB Config
# ==========================
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
POOL_MINCONN = int(os.getenv("DB_POOL_MIN", "1"))
POOL_MAXCONN = int(os.getenv("DB_POOL_MAX", "10"))

if not all([DB_NAME, DB_USER, DB_PASSWORD]):
    raise RuntimeError("Missing required DB environment variables: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")

_db_pool: Optional[pool.SimpleConnectionPool] = None


# ==========================
# Proper DB Dependency with Transaction Safety
# ==========================
def get_db_conn() -> Generator[PsycopgConnection, None, None]:
    global _db_pool
    if _db_pool is None:
        raise HTTPException(status_code=500, detail="Database connection pool not initialized")

    conn = _db_pool.getconn()
    try:
        yield conn
        conn.commit()          # Commit only if no exception occurred
    except Exception:
        conn.rollback()        # Rollback on any error
        raise
    finally:
        _db_pool.putconn(conn)  # Always return connection to pool


# ==========================
# FastAPI App & Router
# ==========================
app = FastAPI(title="MedPortal Admin API")
admin_router = APIRouter(prefix="/admin")


@app.on_event("startup")
async def startup():
    global _db_pool
    logger.info("Starting Admin API and initializing DB connection pool...")
    try:
        _db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=POOL_MINCONN,
            maxconn=POOL_MAXCONN,
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )
        logger.info("Database connection pool created successfully (%d-%d connections)", POOL_MINCONN, POOL_MAXCONN)
    except Exception as e:
        logger.exception("Failed to create database connection pool")
        raise


@app.on_event("shutdown")
async def shutdown():
    global _db_pool
    if _db_pool:
        logger.info("Closing database connection pool...")
        _db_pool.closeall()
        _db_pool = None


# ==========================
# Pydantic Models
# ==========================
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


# ==========================
# Hospital Endpoints
# ==========================
@admin_router.get("/hospitals", response_model=List[dict])
def list_hospitals(conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute("SELECT hospital_id, name, region, status FROM public.hospitals ORDER BY hospital_id")
        rows = cur.fetchall()
    return [dict(zip(["id", "name", "region", "status"], row)) for row in rows]


@admin_router.post("/hospitals", response_model=dict)
def create_hospital(hosp: HospitalCreate, conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.hospitals (name, region, status)
            VALUES (%s, %s, %s)
            RETURNING hospital_id, name, region, status
            """,
            (hosp.name, hosp.region, hosp.status)
        )
        row = cur.fetchone()
    return dict(zip(["id", "name", "region", "status"], row))


@admin_router.put("/hospitals/{hospital_id}", response_model=dict)
def update_hospital(hospital_id: int, hosp: HospitalUpdate, conn=Depends(get_db_conn)):
    updates = []
    values = []
    if hosp.name is not None:
        updates.append("name = %s")
        values.append(hosp.name)
    if hosp.region is not None:
        updates.append("region = %s")
        values.append(hosp.region)
    if hosp.status is not None:
        updates.append("status = %s")
        values.append(hosp.status)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    values.append(hospital_id)
    query = f"""
        UPDATE public.hospitals
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE hospital_id = %s
        RETURNING hospital_id, name, region, status
    """

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Hospital not found")
    return dict(zip(["id", "name", "region", "status"], row))


@admin_router.delete("/hospitals/{hospital_id}")
def delete_hospital(hospital_id: int, conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM public.hospitals WHERE hospital_id = %s RETURNING hospital_id", (hospital_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Hospital not found")
    return {"detail": "Hospital deleted successfully"}


# ==========================
# Doctor Endpoints
# ==========================
@admin_router.get("/doctors", response_model=List[dict])
def list_doctors(conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT doctor_id, name, role, region, hospital, status FROM medportal.doctors ORDER BY doctor_id"
        )
        rows = cur.fetchall()
    return [
        dict(zip(["id", "name", "role", "region", "hospital", "status"], row))
        for row in rows
    ]
@admin_router.post("/doctors", response_model=dict)
def create_doctor(doc: DoctorCreate, conn=Depends(get_db_conn)):
    password_hash = bcrypt.hashpw(doc.password.encode(), bcrypt.gensalt()).decode('utf-8')
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO medportal.doctors (doctor_id, name, role, region, hospital, status, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING doctor_id, name, role, region, hospital, status
            """,
            (doc.doctor_id, doc.name, doc.role, doc.region, doc.hospital, doc.status, password_hash)
        )
        row = cur.fetchone()
    return dict(zip(["id", "name", "role", "region", "hospital", "status"], row))

@admin_router.put("/doctors/{doctor_id}", response_model=dict)
def update_doctor(doctor_id: str, doc: DoctorUpdate, conn=Depends(get_db_conn)):
    updates = []
    values = []

    if doc.name is not None:
        updates.append("name = %s")
        values.append(doc.name)
    if doc.role is not None:
        updates.append("role = %s")
        values.append(doc.role)
    if doc.region is not None:
        updates.append("region = %s")
        values.append(doc.region)
    if doc.hospital is not None:
        updates.append("hospital = %s")
        values.append(doc.hospital)
    if doc.status is not None:
        updates.append("status = %s")
        values.append(doc.status)
    if doc.password is not None:
        hashed = bcrypt.hashpw(doc.password.encode(), bcrypt.gensalt()).decode('utf-8')
        updates.append("password_hash = %s")
        values.append(hashed)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

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
            raise HTTPException(status_code=404, detail="Doctor not found")
    return dict(zip(["id", "name", "role", "region", "hospital", "status"], row))


@admin_router.delete("/doctors/{doctor_id}", status_code=200)
def delete_doctor(doctor_id: str, conn=Depends(get_db_conn)):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM medportal.doctors WHERE doctor_id = %s RETURNING doctor_id",
            (doctor_id,)
        )
        result = cur.fetchone()  # ← fetch once

        if not result:
            raise HTTPException(status_code=404, detail="Doctor not found")

    return {"detail": "Doctor deleted successfully"}

# ==========================
# Include Router
# ==========================
app.include_router(admin_router)