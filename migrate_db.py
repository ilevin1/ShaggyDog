#!/usr/bin/env python3
"""
Simple migration script to add original_image_path column to existing database.
Run this once to update your database schema.
"""
import sqlite3
import os

# Flask creates databases in instance/ folder by default
db_path = 'instance/shaggydog.db'
if not os.path.exists(db_path):
    db_path = 'shaggydog.db'

if not os.path.exists(db_path):
    print(f"Database {db_path} does not exist. No migration needed.")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(generated_image)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'original_image_path' in columns:
        print("Column 'original_image_path' already exists. No migration needed.")
    else:
        print("Adding 'original_image_path' column...")
        cursor.execute("ALTER TABLE generated_image ADD COLUMN original_image_path VARCHAR(255)")
        conn.commit()
        print("Migration completed successfully!")
        
except Exception as e:
    print(f"Error during migration: {e}")
    conn.rollback()
finally:
    conn.close()

