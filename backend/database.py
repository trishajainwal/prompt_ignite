# database.py
import sqlite3

def init_db():
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            product TEXT,
            type TEXT,
            rating INTEGER,
            message TEXT,
            date TEXT,
            sentiment TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully")