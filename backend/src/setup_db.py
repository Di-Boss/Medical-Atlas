# src/setup_db.py
import os
import psycopg2
from psycopg2.extras import execute_values
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker
import numpy as np
from dotenv import load_dotenv

faker = Faker()
random.seed(42)
np.random.seed(42)

# Load .env
load_dotenv()

# -------------------- CONFIG --------------------
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "atlas_db"
DB_USER = "postgres"
DB_PASS = os.getenv("POSTGRES_PASSWORD")

NEW_PATIENTS = 2_000_000
BATCH_SIZE = 20_000
START_DATE = datetime(2020, 1, 1)
RESISTANT_BOOST = 0.38  # high probability for boosted resistance
TARGET_TREATMENTS = 4_000_000  # total treatments to generate

# US top 7 states by population as regions
US_REGIONS = ["California", "Texas", "Florida", "New York", "Pennsylvania", "Illinois", "Ohio"]

HOSPITAL_SUFFIX = ["Oncology Center", "Cancer Hospital", "Onco Clinic", "University Hospital"]
CANCER_TYPES = ["Leukemia", "Lymphoma", "Breast", "Lung", "Colon", "Prostate"]
ANTIBIOTICS = [("Ceftriaxone", 2000), ("Amoxicillin", 500), ("Levofloxacin", 500),
               ("Meropenem", 1000), ("Vancomycin", 1000), ("Piperacillin-Tazobactam", 4000),
               ("Nitrofurantoin", 100), ("Ciprofloxacin", 500)]
PATHOGENS = ["E. coli", "Klebsiella pneumoniae", "Staphylococcus aureus",
             "Pseudomonas aeruginosa", "Enterococcus faecalis", "Acinetobacter baumannii"]

# -------------------- CONNECT --------------------
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS
)
cursor = conn.cursor()

# -------------------- WIPE EXISTING DATA --------------------
print("Wiping existing hospitals, patients, and treatments...")
cursor.execute("TRUNCATE TABLE treatments CASCADE;")
cursor.execute("TRUNCATE TABLE patients CASCADE;")
cursor.execute("TRUNCATE TABLE hospitals CASCADE;")
conn.commit()
print("✅ Tables wiped.")

# -------------------- HOSPITALS --------------------
print("Creating hospitals...")
hospitals = []
for region in US_REGIONS:
    for _ in range(10):
        hospitals.append((f"{region} {faker.company()} {random.choice(HOSPITAL_SUFFIX)}", region))
execute_values(cursor,
               "INSERT INTO hospitals (name, region) VALUES %s ON CONFLICT DO NOTHING", hospitals)
conn.commit()

cursor.execute("SELECT hospital_id, region FROM hospitals")
hospital_map = {row[0]: row[1] for row in cursor.fetchall()}
hospital_ids = list(hospital_map.keys())

# -------------------- PATHOGENS --------------------
execute_values(cursor,
               "INSERT INTO pathogens (name) VALUES %s ON CONFLICT DO NOTHING",
               [(p,) for p in PATHOGENS])
conn.commit()
cursor.execute("SELECT pathogen_id, name FROM pathogens")
pathogen_list = cursor.fetchall()

# -------------------- ANTIBIOTICS --------------------
execute_values(cursor,
               "INSERT INTO antibiotics (name, standard_dose_mg) VALUES %s ON CONFLICT DO NOTHING",
               ANTIBIOTICS)
conn.commit()
cursor.execute("SELECT antibiotic_id, name FROM antibiotics")
antibiotic_list = cursor.fetchall()

# -------------------- GENERATE NEW PATIENTS --------------------
print("Generating new patients...")
for start in range(0, NEW_PATIENTS, BATCH_SIZE):
    batch = []
    for _ in range(min(BATCH_SIZE, NEW_PATIENTS - start)):
        patient_id = str(uuid.uuid4())
        age = random.randint(18, 90)
        weight = round(random.uniform(45, 120), 1)
        gender = random.choice(["Male", "Female"])
        cancer = random.choice(CANCER_TYPES)
        hospital_id = random.choice(hospital_ids)
        region = hospital_map[hospital_id]
        ssn = faker.ssn()
        batch.append((patient_id, age, weight, gender, cancer, hospital_id, region, ssn))
    execute_values(cursor,
                   """INSERT INTO patients (patient_id, age, weight_kg, gender, cancer_type, hospital_id, region, ssn)
                      VALUES %s""",
                   batch)
    conn.commit()
    print(f"Inserted patients: {start + len(batch)}/{NEW_PATIENTS}")

# -------------------- HELPER FUNCTIONS --------------------
def simulate_lab_values(cancer_type):
    wbc = np.random.normal(5.0, 4.0) if cancer_type in ["Leukemia", "Lymphoma"] else np.random.normal(7.0, 3.0)
    wbc = max(0.1, min(40.0, wbc))
    neutrophils_pct = max(5.0, min(95.0, np.random.normal(60.0, 15.0)))
    crp = abs(np.random.normal(20.0, 25.0))
    return round(wbc,2), round(neutrophils_pct,1), round(crp,1)

def compute_resistance(pathogen_name, antibiotic_name, neutrophils_pct, prev_abx_count):
    base = 0.2
    if "Acinetobacter" in pathogen_name or "Pseudomonas" in pathogen_name: base = 0.3
    if "Meropenem" in antibiotic_name: base *= 0.6
    if neutrophils_pct < 20: base += 0.15
    base += min(0.15, 0.03 * prev_abx_count)
    base += np.random.normal(0, 0.03)
    base = max(0.01, min(0.99, base))
    return int(np.random.rand() < base), round(base, 4)

# -------------------- GENERATE TREATMENTS --------------------
print("Generating treatments...")
treatment_counter = 0

cursor.execute("SELECT patient_id, cancer_type FROM patients")
all_patients = cursor.fetchall()
treatments = []

while treatment_counter < TARGET_TREATMENTS:
    for patient_id, cancer_type in all_patients:
        if treatment_counter >= TARGET_TREATMENTS:
            break
        num_treatments = random.randint(1, 3)
        for _ in range(num_treatments):
            if treatment_counter >= TARGET_TREATMENTS:
                break
            antibiotic_id, antibiotic_name = random.choice(antibiotic_list)
            pathogen_id, pathogen_name = random.choice(pathogen_list)
            dose = int(round([b for a,b in ANTIBIOTICS if a==antibiotic_name][0] * random.uniform(0.8,1.2)))
            duration = random.choice([3,5,7,10,14])
            prev_abx = np.random.poisson(0.4)
            wbc, neutrophils_pct, crp = simulate_lab_values(cancer_type)
            resistant, prob = compute_resistance(pathogen_name, antibiotic_name, neutrophils_pct, prev_abx)

            if random.random() < RESISTANT_BOOST:
                resistant = 1
                prob = max(prob, 0.8)
                stay = int(max(1, np.random.normal(14,5))) + random.randint(7,15)
            else:
                stay = int(max(1, np.random.normal(7,3))) + (random.randint(7,25) if resistant else random.randint(0,5))

            admission_date = START_DATE + timedelta(days=random.randint(0,(datetime.now()-START_DATE).days))
            treatments.append((patient_id, antibiotic_id, pathogen_id, dose, duration, prev_abx,
                               wbc, neutrophils_pct, crp, resistant, prob, stay, admission_date))
            treatment_counter += 1

            if treatment_counter % BATCH_SIZE == 0:
                execute_values(cursor,
                    """INSERT INTO treatments (patient_id, antibiotic_id, pathogen_id, dose_mg, duration_days,
                       previous_antibiotics_count, wbc, neutrophils_pct, crp_mg_l, resistant, resistant_prob,
                       hospital_stay_days, admission_date) VALUES %s""",
                    treatments)
                conn.commit()
                print(f"Inserted treatments: {treatment_counter}/{TARGET_TREATMENTS}")
                treatments = []

# Insert any remaining
if treatments:
    execute_values(cursor,
        """INSERT INTO treatments (patient_id, antibiotic_id, pathogen_id, dose_mg, duration_days,
           previous_antibiotics_count, wbc, neutrophils_pct, crp_mg_l, resistant, resistant_prob,
           hospital_stay_days, admission_date) VALUES %s""",
        treatments)
    conn.commit()

cursor.close()
conn.close()
print(f"✅ Database setup complete: {NEW_PATIENTS} patients and {TARGET_TREATMENTS} treatments generated!")
