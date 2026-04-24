import sqlite3
from pathlib import Path


def migrate_database():
    db_path = Path("./tickets.db")
    
    if not db_path.exists():
        print("Database not found. It will be created automatically on first run.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(tickets)")
    columns = [col[1] for col in cursor.fetchall()]
    
    migrations_needed = []
    if "created_at" not in columns:
        migrations_needed.append("ALTER TABLE tickets ADD COLUMN created_at TIMESTAMP")
    if "sla_deadline" not in columns:
        migrations_needed.append("ALTER TABLE tickets ADD COLUMN sla_deadline TIMESTAMP")
    if "sla_breached" not in columns:
        migrations_needed.append("ALTER TABLE tickets ADD COLUMN sla_breached INTEGER DEFAULT 0")
    if "resolved_at" not in columns:
        migrations_needed.append("ALTER TABLE tickets ADD COLUMN resolved_at TIMESTAMP")
    
    if not migrations_needed:
        print("Database is already up to date.")
        conn.close()
        return
    
    print(f"Applying {len(migrations_needed)} migration(s)...")
    for migration in migrations_needed:
        try:
            cursor.execute(migration)
            print(f"  ✓ Executed: {migration}")
        except sqlite3.OperationalError as e:
            print(f"  ✗ Failed: {migration}")
            print(f"    Error: {e}")
    
    conn.commit()
    conn.close()
    print("Migration completed.")


if __name__ == "__main__":
    migrate_database()
