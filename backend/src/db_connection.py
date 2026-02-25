# src/create_doctor.py
import os
import psycopg2
import bcrypt
from dotenv import load_dotenv
import random

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "atlas_db")  # Connect to atlas_db
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
    cursor = conn.cursor()
    print("✅ Connected to atlas_db database")
except Exception as e:
    print("❌ Connection failed:", e)
    exit()

# Generate a random 6-digit doctor ID
doctor_id = str(random.randint(100000, 999999))
password = input("Enter password for doctor: ").strip()
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Ensure schema exists
cursor.execute("CREATE SCHEMA IF NOT EXISTS medportal")

# Create table inside the schema
cursor.execute("""
CREATE TABLE IF NOT EXISTS medportal.doctors (
    id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(6) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
)
""")

# Insert data into medportal.doctors
try:
    cursor.execute(
        "INSERT INTO medportal.doctors (doctor_id, password_hash) VALUES (%s, %s)",
        (doctor_id, password_hash)
    )
    conn.commit()
    print(f"✅ Doctor account created! ID: {doctor_id}")
except Exception as e:
    print("❌ Error inserting doctor:", e)
finally:
    cursor.close()
    conn.close()
