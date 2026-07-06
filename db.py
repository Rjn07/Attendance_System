"""
=============================================================================
  db.py  —  saara Postgres (Supabase) access ek jagah.
  entry_cameras.py aur server.py dono isi module ko import karte hain,
  taaki query logic sirf ek jagah maintain karni pade.

  NOTE: Ye MySQL wale db.py ka Postgres version hai. Sabhi function names
  aur return shapes SAME rakhe gaye hain, isliye entry_cameras.py aur
  server.py me KOI CHANGE nahi karna padega.
=============================================================================
"""

import threading
from datetime import datetime, date

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor

import config

# =============================================================================
#  CONNECTION POOL
# =============================================================================
_pool = None
_pool_lock = threading.Lock()


def get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = pg_pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=8,
                    dsn=config.DATABASE_URL,
                )
    return _pool


class _ConnCtx:
    """Small wrapper so existing code (`conn = get_conn() ... conn.close()`)
       keeps working unchanged, while actually returning the connection to
       the pool instead of really closing the socket."""

    def __init__(self, raw_conn):
        self._raw = raw_conn

    def cursor(self, *args, **kwargs):
        kwargs.setdefault("cursor_factory", RealDictCursor)
        return self._raw.cursor(*args, **kwargs)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        get_pool().putconn(self._raw)


def get_conn():
    raw = get_pool().getconn()
    return _ConnCtx(raw)


def init_db():
    """Tables ab schema.sql se banti hain (Supabase SQL editor me ek baar
       run karo). Yahan sirf connectivity check karte hain taaki startup pe
       galat DATABASE_URL ka pata turant chal jaaye."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
    finally:
        conn.close()


def get_or_create_employee(name, department=None, designation=None):
    """Roster me employee dhoondo, na ho to bana do. Returns employee_id."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM employees WHERE name = %s", (name,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute(
            """INSERT INTO employees (name, department, designation)
               VALUES (%s, %s, %s) RETURNING id""",
            (name, department, designation),
        )
        emp_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
        return emp_id
    finally:
        conn.close()


def sync_roster(names):
    """embeddings.pkl ke saare naam employees table me ensure karo (bulk, startup pe)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        for name in names:
            cur.execute(
                "INSERT INTO employees (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (name,),
            )
        conn.commit()
        cur.close()
    finally:
        conn.close()


def get_last_status_today(name):
    """Aaj is naam ka sabse recent status ('Present'/'Exit') ya None."""
    today = date.today()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT status FROM attendance
               WHERE name = %s AND att_date = %s
               ORDER BY att_time DESC, id DESC LIMIT 1""",
            (name, today),
        )
        row = cur.fetchone()
        cur.close()
        return row["status"] if row else None
    finally:
        conn.close()


def mark_attendance(name, camera_id, confidence=None, photo_path=None,
                     department=None):
    """
    Duplicate-prevention wali attendance mark:
      - Agar aaj already "Present" hai -> "already_present", kuch nahi likhta.
      - Warna naya row insert (Present ya, agar pehle Exit tha, to Re-Entry
        bhi "Present" hi likha jaata hai — jaisa original CSV version me tha).
    Returns "marked" | "already_present".
    """
    last_status = get_last_status_today(name)
    if last_status == "Present":
        return "already_present"

    emp_id = get_or_create_employee(name, department=department)

    now = datetime.now()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO attendance
               (employee_id, name, att_date, att_time, status, camera_id,
                confidence, photo_path)
               VALUES (%s, %s, %s, %s, 'Present', %s, %s, %s)""",
            (emp_id, name, now.date(), now.time().strftime("%H:%M:%S"),
             camera_id, confidence, photo_path),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()

    return "marked"


def mark_exit(name, camera_id, confidence=None, photo_path=None):
    """Optional explicit exit-marking (e.g. from a separate exit camera)."""
    last_status = get_last_status_today(name)
    if last_status != "Present":
        return "not_inside"

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM employees WHERE name = %s", (name,))
        row = cur.fetchone()
        emp_id = row["id"] if row else get_or_create_employee(name)

        now = datetime.now()
        cur.execute(
            """INSERT INTO attendance
               (employee_id, name, att_date, att_time, status, camera_id,
                confidence, photo_path)
               VALUES (%s, %s, %s, %s, 'Exit', %s, %s, %s)""",
            (emp_id, name, now.date(), now.time().strftime("%H:%M:%S"),
             camera_id, confidence, photo_path),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return "marked"


def count_today_rows(name):
    today = date.today()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS c FROM attendance WHERE name = %s AND att_date = %s",
            (name, today),
        )
        n = cur.fetchone()["c"]
        cur.close()
        return n
    finally:
        conn.close()


# =============================================================================
#  READ HELPERS  —  used by the Flask API
# =============================================================================
def _dictify(cur):
    # RealDictCursor already returns dict-like rows; just cast to plain dicts.
    return [dict(row) for row in cur.fetchall()]


def read_day_rows(target_date):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT name, att_time AS time, status, camera_id AS camera,
                      photo_path AS photo
               FROM attendance WHERE att_date = %s
               ORDER BY att_time DESC""",
            (target_date,),
        )
        rows = _dictify(cur)
        cur.close()
        for r in rows:
            r["time"] = str(r["time"])
        return rows
    finally:
        conn.close()


def read_month_rows(month):
    """month = 'YYYY-MM'."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT name, att_date AS date, att_time AS time, status,
                      camera_id AS camera, photo_path AS photo
               FROM attendance WHERE TO_CHAR(att_date, 'YYYY-MM') = %s
               ORDER BY att_time ASC""",
            (month,),
        )
        rows = _dictify(cur)
        cur.close()
        for r in rows:
            r["date"] = str(r["date"])
            r["time"] = str(r["time"])
        return rows
    finally:
        conn.close()


def all_dates():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT att_date FROM attendance ORDER BY att_date DESC")
        dates = [str(r["att_date"]) for r in cur.fetchall()]
        cur.close()
        return dates
    finally:
        conn.close()


def available_months():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT TO_CHAR(att_date, 'YYYY-MM') AS m FROM attendance "
            "ORDER BY 1 DESC"
        )
        months = [r["m"] for r in cur.fetchall()]
        cur.close()
        return months
    finally:
        conn.close()


def get_roster():
    """Returns (names_list, source='employees')."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM employees WHERE active = TRUE ORDER BY name")
        names = [r["name"] for r in cur.fetchall()]
        cur.close()
        return names, "employees"
    finally:
        conn.close()


def get_employee_photo(name):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT photo_path FROM employees WHERE name = %s", (name,))
        row = cur.fetchone()
        cur.close()
        return row["photo_path"] if row and row["photo_path"] else None
    finally:
        conn.close()


def sync_employee_photos_from_dir():
    """
    photos/<employee_name>/*.jpg (seedha folder ke andar, date-subfolder ke
    ANDAR nahi) — inhe employee ki PROFILE photo maan kar employees.photo_path
    me set kar do. Capture-wale photos (photos/<name>/<date>/*.jpg) is se
    touch nahi hote, kyunki wo ek level neeche hote hain.
    Safe to call baar baar (idempotent, sirf jinke paas abhi photo_path
    khaali hai unhi ko update karta hai).
    """
    import os as _os

    IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
    if not _os.path.isdir(config.PHOTOS_DIR):
        return 0

    updated = 0
    conn = get_conn()
    try:
        cur = conn.cursor()
        for entry in sorted(_os.listdir(config.PHOTOS_DIR)):
            emp_dir = _os.path.join(config.PHOTOS_DIR, entry)
            if not _os.path.isdir(emp_dir):
                continue

            # sirf top-level files (date subfolders skip)
            photo_file = None
            for fname in sorted(_os.listdir(emp_dir)):
                fpath = _os.path.join(emp_dir, fname)
                if _os.path.isfile(fpath) and fname.lower().endswith(IMG_EXT):
                    photo_file = fname
                    break
            if not photo_file:
                continue

            rel_path = f"{entry}/{photo_file}"

            # match employee by name (folder name == employee name, jaisa
            # embeddings.pkl / roster me hai). Agar employee exist nahi karta,
            # to bhi bana do taaki naya photo add karte hi turant dikh jaaye.
            cur.execute("SELECT id, photo_path FROM employees WHERE name = %s", (entry,))
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    "INSERT INTO employees (name, photo_path) VALUES (%s, %s)",
                    (entry, rel_path),
                )
                updated += 1
            elif not row["photo_path"]:
                cur.execute(
                    "UPDATE employees SET photo_path = %s WHERE id = %s",
                    (rel_path, row["id"]),
                )
                updated += 1
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return updated


def list_employees():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, name, department, designation, photo_path, active
               FROM employees ORDER BY name"""
        )
        rows = _dictify(cur)
        cur.close()
        return rows
    finally:
        conn.close()
