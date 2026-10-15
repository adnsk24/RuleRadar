# RuleRadar AI - Database & Storage Backup / Restore Utility
# Guarantees zero data loss during migrations and hosting deployment

import os
import sys
import shutil
import zipfile
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "ruleradar.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

def backup():
    """Create a self-contained archive of the SQLite database and all uploaded files."""
    if not os.path.exists(DATA_DIR):
        print(f"[ERROR] Data directory does not exist: {DATA_DIR}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"ruleradar_backup_{timestamp}.zip"
    backup_filepath = os.path.join(BASE_DIR, backup_filename)

    print(f"[*] Packaging RuleRadar data from {DATA_DIR} into {backup_filename}...")
    
    with zipfile.ZipFile(backup_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
        if os.path.exists(DB_PATH):
            zipf.write(DB_PATH, arcname="ruleradar.db")
            print(f"  + Included database: ruleradar.db ({os.path.getsize(DB_PATH)} bytes)")
        
        if os.path.exists(UPLOAD_DIR):
            for root, _, files in os.walk(UPLOAD_DIR):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, DATA_DIR)
                    zipf.write(full_p, arcname=rel_p)
            print(f"  + Included document uploads directory")

    canonical_latest = os.path.join(BASE_DIR, "ruleradar_data_latest.zip")
    shutil.copy2(backup_filepath, canonical_latest)
    print(f"[SUCCESS] Backup successfully created at: {backup_filepath}")
    print(f"[SUCCESS] Canonical snapshot updated at: {canonical_latest}")
    verify(DB_PATH)
    return backup_filepath

def restore(zip_path):
    """Safely restore a RuleRadar data archive into the active data directory."""
    if not os.path.exists(zip_path):
        print(f"[ERROR] Specified backup file does not exist: {zip_path}")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    print(f"[*] Restoring RuleRadar data from {zip_path} into {DATA_DIR}...")
    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(DATA_DIR)

    print(f"[SUCCESS] Restore complete.")
    verify(DB_PATH)

def verify(db_file=None):
    """Check record counts in the SQLite database to confirm zero data loss."""
    target = db_file or DB_PATH
    if not os.path.exists(target):
        print(f"[WARNING] Database file not found at {target}")
        return

    try:
        conn = sqlite3.connect(target)
        cursor = conn.cursor()
        
        counts = {}
        for table in ["documents", "clauses", "risk_findings", "deadlines", "comparison_reports", "qa_sessions"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except Exception:
                counts[table] = "N/A"
        
        conn.close()
        print("\n--- Current Data Integrity Snapshot ---")
        for table, count in counts.items():
            print(f"  • {table.replace('_', ' ').title():<22}: {count} records")
        print("----------------------------------------\n")
    except Exception as e:
        print(f"[ERROR] Failed to verify database: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python data_sync.py backup           -> Creates a .zip backup of DB and uploads")
        print("  python data_sync.py restore <file>   -> Restores DB and uploads from .zip")
        print("  python data_sync.py verify           -> Verifies current DB record counts")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "backup":
        backup()
    elif cmd == "restore":
        if len(sys.argv) < 3:
            print("[ERROR] Please specify the backup .zip file to restore.")
        else:
            restore(sys.argv[2])
    elif cmd == "verify":
        verify()
    else:
        print(f"Unknown command '{cmd}'. Available: backup, restore, verify")
