import os
import random
import bcrypt
import psycopg2
from dotenv import load_dotenv
import getpass

# === LOAD ENV VARIABLES ===
load_dotenv()

DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")


def generate_unique_doctor_id(cursor):
    """Generate a 6-digit doctor ID that doesn't already exist."""
    while True:
        doctor_id = str(random.randint(100000, 999999))
        cursor.execute(
            "SELECT 1 FROM medportal.doctors WHERE doctor_id = %s LIMIT 1;",
            (doctor_id,)
        )
        if cursor.fetchone() is None:
            return doctor_id


def create_doctor(password: str):
    """Creates a new doctor profile with random 6-digit ID and hashed password."""

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        doctor_id = generate_unique_doctor_id(cursor)

        cursor.execute(
            "INSERT INTO medportal.doctors (doctor_id, password_hash) VALUES (%s, %s) RETURNING id;",
            (doctor_id, password_hash)
        )
        doctor_pk = cursor.fetchone()[0]

        conn.commit()

        print("Doctor profile created!")
        print(f"Doctor ID: {doctor_id}")
        print(f"Password: {password}")
        print(f"Primary key: {doctor_pk}")

        return doctor_id, doctor_pk

    except Exception as e:
        print("Error creating doctor:", e)
        return None, None

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    password = getpass.getpass("Enter doctor password: ")
    create_doctor(password)
