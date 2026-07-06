# Deploying the Attendance System to the Cloud

## Architecture

```
[Local Ubuntu machine]                    [Cloud]
 entry_cameras.py  ───writes───▶  Supabase Postgres  ◀───reads─── server.py (on Render)
 (RTSP cameras, GPU,                     (shared DB)                  │
  must stay local)                                                     ▼
                                                          Anyone, anywhere opens
                                                          https://your-app.onrender.com
```

- **`entry_cameras.py`** needs your GPU and LAN access to the RTSP cameras, so it **stays on your local machine**. It only changes in one way: it now writes to Supabase instead of local MySQL.
- **`server.py` + `dashboard.html`** move to **Render**, so your team can open the dashboard from any browser, on any network.
- **Photos**: captured face-crop images are saved locally by `entry_cameras.py`. They will NOT automatically appear on the cloud server unless you sync them (see "Photos" section below) — this is the one piece that needs a follow-up decision from you.

---

## Step 1 — Create the Supabase project & database

1. Go to https://supabase.com → **New project**.
2. Once created, open **SQL Editor** → paste the contents of `schema.sql` → **Run**.
3. Go to **Project Settings → Database → Connection string**.
4. Click the **"Transaction pooler"** tab (NOT "Direct connection" — the direct one is IPv6-only and will fail to connect from most local networks/Render).
5. Copy the string, it looks like:
   ```
   postgresql://postgres.xxxxxxxxxxxx:[email protected]:6543/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with your actual database password (set when you created the project).

Keep this string handy — you'll set it as `DATABASE_URL` in **two** places: your local machine and Render.

---

## Step 2 — Test locally first

On your local machine:

```bash
export DATABASE_URL='postgresql://postgres.xxxx:[email protected]:6543/postgres'
pip install -r requirements.txt
python server.py
```

Open `http://localhost:5400` — dashboard should load (empty, since no attendance yet).

If you have old CSV data to migrate:
```bash
export DATABASE_URL='...'
python import_csv.py /path/to/New_attendance.csv
```

---

## Step 3 — Deploy `server.py` to Render

1. Push this project folder to a **GitHub repo** (Render deploys from git).
2. Go to https://render.com → **New → Web Service** → connect your repo.
3. Settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: leave blank (Render will detect the `Procfile`) or set `gunicorn server:app --bind 0.0.0.0:$PORT`
4. Add environment variable:
   - `DATABASE_URL` = the same Supabase pooler string from Step 1
5. Click **Create Web Service**. Render will build and give you a URL like `https://attendance-dashboard.onrender.com`.

That URL is now shareable with anyone on your team — no VPN, no local network needed.

---

## Step 4 — Point your local camera script at the same database

On your local machine (the one plugged into the cameras), just set the same env var permanently, e.g. add to `~/.bashrc` or a systemd service file:

```bash
export DATABASE_URL='postgresql://postgres.xxxx:[email protected]:6543/postgres'
```

Then run as before:
```bash
python entry_cameras.py
```

It now writes attendance straight into Supabase — the same data the Render-hosted dashboard reads.

---

## Photos — the one thing that needs a decision

Right now, `entry_cameras.py` saves cropped face photos to a **local folder** (`PHOTOS_DIR`). The Render server has its own separate, ephemeral filesystem — it can't see your local photos, and Render's disk is wiped on every redeploy anyway.

Pick one:

**Option A — Simplest (recommended to start):** Don't worry about photos in the cloud dashboard yet. Attendance records, names, times, and stats will all work fine on Render; only the little face-crop thumbnails won't show up remotely. You can still view them locally.

**Option B — Full solution:** Upload each captured photo to cloud storage (Supabase Storage, S3, or Cloudflare R2) right when it's captured in `entry_cameras.py`, and store the **public URL** in `photo_path` instead of a local relative path. `dashboard.html` already just renders whatever `photo_path` gives it, so this is a small change in one function (`_save_capture` in `entry_cameras.py`). I can build this for you if you want — just say the word and tell me which storage you'd prefer (Supabase Storage is easiest since you already have that account).

---

## Files in this package

| File | Runs where | Notes |
|---|---|---|
| `config.py` | both | reads `DATABASE_URL` env var |
| `db.py` | both | rewritten for Postgres (was MySQL) |
| `schema.sql` | Supabase SQL editor | run once |
| `server.py` | Render (cloud) | Flask API + dashboard |
| `entry_cameras.py` | local machine only | needs GPU + camera LAN access |
| `import_csv.py` | either | one-time historical data import |
| `sync_photos.py` | local machine | re-links profile photos |
| `requirements.txt` | Render | lightweight (Flask, psycopg2, gunicorn) |
| `requirements-local.txt` | local machine | OpenCV, InsightFace, etc. |
| `Procfile` | Render | tells Render how to start the app |

**Not included in this package** — you'll need to add your `dashboard.html` and your `embeddings.pkl` file back in (they weren't part of this upload), plus your real camera RTSP URLs/credentials in `entry_cameras.py`.
