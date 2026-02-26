"""
One-off script to create or update an admin user.
Usage: from backend folder run: python -m src.create_admin_user
Or: cd src && python create_admin_user.py
"""
import os
import sys
import bcrypt
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

ADMIN_ID = "333333"
ADMIN_PASSWORD = "123321"
ADMIN_NAME = "Admin User"
ADMIN_ROLE = "Admin"
ADMIN_REGION = "California"
ADMIN_HOSPITAL = "Medical Atlas HQ"
ADMIN_STATUS = "Active"


def main():
    if not all([DB_NAME, DB_USER, DB_PASSWORD]):
        print("Missing POSTGRES_DB, POSTGRES_USER, or POSTGRES_PASSWORD in .env")
        sys.exit(1)

    password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        conn.autocommit = False
        cur = conn.cursor()

        # Try full insert (table has name, role, region, hospital, status)
        try:
            cur.execute(
                """
                INSERT INTO medportal.doctors (doctor_id, name, role, region, hospital, status, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doctor_id) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role,
                    name = EXCLUDED.name,
                    region = EXCLUDED.region,
                    hospital = EXCLUDED.hospital,
                    status = EXCLUDED.status
                """,
                (ADMIN_ID, ADMIN_NAME, ADMIN_ROLE, ADMIN_REGION, ADMIN_HOSPITAL, ADMIN_STATUS, password_hash),
            )
        except psycopg2.Error as e:
            if "column" in str(e).lower() and "does not exist" in str(e).lower():
                # Minimal schema: only doctor_id, password_hash; then set role if column exists
                cur.execute(
                    "INSERT INTO medportal.doctors (doctor_id, password_hash) VALUES (%s, %s) ON CONFLICT (doctor_id) DO UPDATE SET password_hash = EXCLUDED.password_hash",
                    (ADMIN_ID, password_hash),
                )
                try:
                    cur.execute("UPDATE medportal.doctors SET role = %s WHERE doctor_id = %s", (ADMIN_ROLE, ADMIN_ID))
                except psycopg2.Error:
                    pass
            else:
                raise

        conn.commit()
        print("Admin user created/updated successfully.")
        print(f"  Doctor ID: {ADMIN_ID}")
        print(f"  Password:  {ADMIN_PASSWORD}")
        print(f"  Role:      {ADMIN_ROLE}")
        print("Log in at the sign-in page, then go to /admin.")

    except Exception as e:
        print("Error:", e)
        sys.exit(1)
    finally:
        if "cur" in dir():
            cur.close()
        if "conn" in dir():
            conn.close()


if __name__ == "__main__":
    main()
