import sqlite3
import os
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_db():
    db_path = os.path.join(PROJECT_DIR, "registrations.db")
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            college TEXT NOT NULL,
            branch TEXT NOT NULL,
            year TEXT NOT NULL,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()

def generate_ack_id():
    # Generate a unique acknowledgement ID (YUKTI-YYYY-XXXXX)
    timestamp = datetime.now().strftime("%Y")
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"YUKTI-{timestamp}-{random_chars}"
