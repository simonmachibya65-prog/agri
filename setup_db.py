"""
setup_db.py — One-time database setup script.

Run this before starting the web app if MySQL is available:
    python setup_db.py
"""

from db import init_db

if __name__ == "__main__":
    try:
        init_db()
        print("✅  Database 'crop_ai' and table 'records' created successfully.")
    except Exception as e:
        print(f"❌  Failed to initialise database: {e}")
        print("    Make sure MySQL is running and credentials in db.py are correct.")
