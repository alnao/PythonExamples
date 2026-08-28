"""
SQLite Cache & History Engine for Face Recognition.
Caches image encodings, locations, thumbnails, and scan history.
"""

import os
import sqlite3
import pickle
import time
import concurrent.futures
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageOps
import io
import numpy as np

DB_NAME = "face_rec_cache.db"

# Bump whenever detection changes the meaning of the stored encodings/locations
# (EXIF orientation, downscaling, detector parameters): older rows are ignored
# and the images are analyzed again instead of returning stale data.
ALGO_VERSION = 2

class CacheManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, DB_NAME)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Image encodings & locations cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_cache (
                    path TEXT PRIMARY KEY,
                    mtime REAL,
                    size INTEGER,
                    encodings BLOB,
                    locations BLOB,
                    thumb_blob BLOB,
                    algo_version INTEGER DEFAULT 0
                )
            """)
            # Migration for databases created before algo_version existed.
            columns = {row[1] for row in cursor.execute("PRAGMA table_info(image_cache)")}
            if "algo_version" not in columns:
                cursor.execute("ALTER TABLE image_cache ADD COLUMN algo_version INTEGER DEFAULT 0")
            # Folder history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    path TEXT PRIMARY KEY,
                    scanned_at REAL,
                    photo_count INTEGER,
                    faces_count INTEGER,
                    clusters_count INTEGER
                )
            """)
            conn.commit()

    def get_cached_image(self, path: str) -> Optional[Tuple[List[np.ndarray], List[tuple], Optional[bytes]]]:
        try:
            stat = os.stat(path)
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT mtime, size, encodings, locations, thumb_blob, algo_version "
                    "FROM image_cache WHERE path = ?",
                    (path,)
                )
                row = cursor.fetchone()
                if row:
                    cached_mtime, cached_size, enc_blob, loc_blob, thumb_blob, algo_version = row
                    if (abs(cached_mtime - stat.st_mtime) < 0.01
                            and cached_size == stat.st_size
                            and (algo_version or 0) == ALGO_VERSION):
                        encodings = pickle.loads(enc_blob) if enc_blob else []
                        locations = pickle.loads(loc_blob) if loc_blob else []
                        return encodings, locations, thumb_blob
        except Exception:
            pass
        return None

    def save_cached_image(self, path: str, encodings: List[np.ndarray], locations: List[tuple], thumb_blob: Optional[bytes] = None):
        try:
            stat = os.stat(path)
            enc_blob = pickle.dumps(encodings)
            loc_blob = pickle.dumps(locations)
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO image_cache
                        (path, mtime, size, encodings, locations, thumb_blob, algo_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (path, stat.st_mtime, stat.st_size, enc_blob, loc_blob, thumb_blob, ALGO_VERSION))
                conn.commit()
        except Exception as e:
            print(f"[CACHE WARN] Failed to save cache for {path}: {e}")

    def add_to_history(self, path: str, photo_count: int, faces_count: int, clusters_count: int):
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO search_history (path, scanned_at, photo_count, faces_count, clusters_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (path, time.time(), photo_count, faces_count, clusters_count))
                conn.commit()
        except Exception as e:
            print(f"[HISTORY WARN] {e}")

    def get_history(self) -> List[Dict]:
        return self.get_history_list()

    def get_history_list(self) -> List[Dict]:
        history = []
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT path, scanned_at, photo_count, faces_count, clusters_count
                    FROM search_history ORDER BY scanned_at DESC
                """)
                for row in cursor.fetchall():
                    history.append({
                        "path": row[0],
                        "scanned_at": row[1],
                        "photo_count": row[2],
                        "faces_count": row[3],
                        "clusters_count": row[4]
                    })
        except Exception as e:
            print(f"[HISTORY WARN] {e}")
        return history

    def delete_history_item(self, path: str):
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM search_history WHERE path = ?", (path,))
                conn.commit()
        except Exception as e:
            print(f"[HISTORY DEL WARN] {e}")

    def clear_all_history(self):
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM search_history")
                conn.commit()
        except Exception as e:
            print(f"[HISTORY CLEAR WARN] {e}")


def generate_grid_thumbnail(image_path: str, max_size: int = 360) -> Optional[bytes]:
    """Generate compressed JPEG thumbnail blob for fast grid rendering."""
    try:
        with Image.open(image_path) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((max_size, max_size), Image.LANCZOS)
            buffer = io.BytesIO()
            img.convert("RGB").save(buffer, format="JPEG", quality=80)
            return buffer.getvalue()
    except Exception:
        return None
