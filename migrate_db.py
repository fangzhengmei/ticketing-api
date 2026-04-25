import sqlite3
import os

DB_PATH = "./tickets.db"

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        print(f"Adding column {column_name} to {table_name}...")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        print(f"Column {column_name} added successfully.")
    else:
        print(f"Column {column_name} already exists in {table_name}.")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database file {DB_PATH} does not exist. It will be created automatically when the app starts.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Checking database schema...")
        
        add_column_if_not_exists(cursor, "tickets", "solution", "TEXT")
        add_column_if_not_exists(cursor, "tickets", "solution_time", "DATETIME")
        add_column_if_not_exists(cursor, "tickets", "resolved_by", "TEXT")
        add_column_if_not_exists(cursor, "tickets", "resolution_category", "TEXT")
        
        conn.commit()
        print("Database migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
