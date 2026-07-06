"""
Manually re-scan the photos/ folder and link any employee/<name>/*.jpg
found there as that employee's profile photo (employees.photo_path).

Run this any time you add/replace photos under photos/<employee_name>/.

    python sync_photos.py
"""
import config
import db

if __name__ == "__main__":
    db.init_db()
    n = db.sync_employee_photos_from_dir()
    print(f"Linked {n} employee profile photo(s) from {config.PHOTOS_DIR}")
