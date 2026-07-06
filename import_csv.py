"""
Purani CSV (Name, Date, Time, Status, Camera) ko MySQL "attendance" table
me import karta hai. Employees jo already roster me nahi hain, unhe bhi
automatically create kar deta hai.

CHALANE KA TARIKA:
    python import_csv.py /path/to/New_attendance.csv

Duplicate-safe: agar same (name, date, time, camera) row already DB me
hai, to usse skip kar deta hai — script baar baar chalane se dobara
records duplicate nahi honge.
"""

import sys
import csv
from datetime import datetime

import config
import db


def row_exists(cur, name, att_date, att_time, camera):
    cur.execute(
        """SELECT 1 FROM attendance
           WHERE name=%s AND att_date=%s AND att_time=%s
             AND (camera_id=%s OR (camera_id IS NULL AND %s IS NULL))
           LIMIT 1""",
        (name, att_date, att_time, camera, camera),
    )
    return cur.fetchone() is not None


def import_csv(path):
    db.init_db()

    total = 0
    inserted = 0
    skipped_dup = 0
    skipped_bad = 0

    conn = db.get_conn()
    cur = conn.cursor()

    with open(path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            name   = (row.get("Name") or "").strip()
            date_s = (row.get("Date") or "").strip()
            time_s = (row.get("Time") or "").strip()
            status = (row.get("Status") or "Present").strip() or "Present"
            camera = (row.get("Camera") or "").strip() or None

            if not name or not date_s or not time_s:
                skipped_bad += 1
                continue

            try:
                att_date = datetime.strptime(date_s, "%Y-%m-%d").date()
                att_time = datetime.strptime(time_s, "%H:%M:%S").time()
            except ValueError:
                skipped_bad += 1
                continue

            if status not in ("Present", "Exit"):
                status = "Present"

            if row_exists(cur, name, att_date, att_time, camera):
                skipped_dup += 1
                continue

            emp_id = db.get_or_create_employee(name)
            cur.execute(
                """INSERT INTO attendance
                   (employee_id, name, att_date, att_time, status, camera_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (emp_id, name, att_date, att_time, status, camera),
            )
            inserted += 1

            if inserted % 200 == 0:
                conn.commit()   # batch commit for large files

    conn.commit()
    cur.close()
    conn.close()

    print("=" * 50)
    print(f"  CSV rows read     : {total}")
    print(f"  Inserted          : {inserted}")
    print(f"  Skipped (dup)     : {skipped_dup}")
    print(f"  Skipped (bad row) : {skipped_bad}")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_csv.py /home/cyamsys/Desktop/attendance/attendance_deploy/New_attendance.csv")
        sys.exit(1)
    import_csv(sys.argv[1])
