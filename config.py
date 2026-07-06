"""
=============================================================================
  SHARED CONFIG  —  entry_cameras.py aur server.py dono isi file ko use
  karte hain, taaki DB settings ek hi jagah edit karni padein.

  DB ab Postgres (Supabase) hai, MySQL nahi. Ek hi DATABASE_URL string se
  connect hota hai — local camera script aur cloud server (Render) dono
  isi env var ko set karke SAME Supabase database use karte hain.
=============================================================================
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
#  POSTGRES DATABASE (Supabase)
# =============================================================================
#  Supabase dashboard -> Project Settings -> Database -> Connection string
#  -> "Transaction pooler" tab (port 6543, address session-pooler...) copy
#  karo. Direct connection (port 5432) IPv6-only hota hai aur kai ISPs /
#  local networks se fail hota hai — isliye pooler string hi use karo.
#
#  Example:
#  postgresql://postgres.xxxxxxxx:[email protected]:6543/postgres
#
#  Isko environment variable DATABASE_URL me set karo — local machine pe
#  aur Render pe dono jagah SAME value.
# =============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it to your Supabase Transaction Pooler connection string, e.g.\n"
        "  export DATABASE_URL='postgresql://postgres.xxxx:[email protected]:6543/postgres'"
    )

# =============================================================================
#  FACE EMBEDDINGS  (unchanged from your original setup, LOCAL ONLY —
#  entry_cameras.py needs this, server.py does not)
# =============================================================================
EMBEDDINGS_FILE = os.environ.get(
    "EMBEDDINGS_FILE",
    "/home/cyamsys/Downloads/HR_face/embeddings/embeddings.pkl",
)

# =============================================================================
#  PHOTO STORAGE
#  Har successful "mark" pe cropped face image yahan save hoti hai, aur
#  database me sirf relative path store hota hai (PHOTOS_DIR ke andar ka path).
#
#  IMPORTANT (cloud deployment): local camera machine aur Render server
#  alag-alag disks hain, isliye photos "shared" nahi hote by default.
#  Options:
#    1) sync_photos_to_cloud.py se photos ko S3/Supabase Storage pe upload
#       karo aur DB me full URL store karo (recommended for production).
#    2) Ya, chhote setup ke liye, Render pe bhi ek scheduled sync job/rclone
#       laga do jo local PHOTOS_DIR ko cloud disk pe mirror kare.
#  Filhal dono scripts isi env var se apna apna local PHOTOS_DIR use karte
#  hain — camera machine pe capture hote hain, server apne khud ke
#  PHOTOS_DIR se serve karega (jab tak upload step add na ho).
# =============================================================================
PHOTOS_DIR = os.environ.get("PHOTOS_DIR", os.path.join(BASE_DIR, "photos"))
os.makedirs(PHOTOS_DIR, exist_ok=True)

# =============================================================================
#  ATTENDANCE BEHAVIOUR
# =============================================================================
MARK_COOLDOWN_SECONDS = int(os.environ.get("MARK_COOLDOWN_SECONDS", 10))
STATUS_CACHE_TTL       = int(os.environ.get("STATUS_CACHE_TTL", 5))

# Monthly report "working days" mode:
#   "office_open" -> jis din kisi camera pe koi detect hua, wahi din count
#   "calendar"    -> mahine ke saare din minus WEEKEND_DAYS
WORKING_DAYS_MODE = os.environ.get("WORKING_DAYS_MODE", "office_open")
WEEKEND_DAYS      = [5, 6]   # 0=Mon ... 6=Sun

# =============================================================================
#  FLASK SERVER
# =============================================================================
HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
# Render provides its own PORT env var — respect it if present.
PORT = int(os.environ.get("PORT", os.environ.get("FLASK_PORT", 5400)))
