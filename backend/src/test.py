from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()  # <- this loads the .env file

conn = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT")
)

cur = conn.cursor()
cur.execute("SELECT hospital_id, name, region, status FROM public.hospitals ORDER BY hospital_id")
print(cur.fetchall())
conn.close()
