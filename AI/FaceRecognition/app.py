#!/usr/bin/env python3
"""
Face Recognition Photo Analyzer — Asynchronous Flask Web Backend
Supports async background scan jobs, SQLite caching, and instant access
to past scan job results.
"""

import os
import sys
import time
import io
import uuid
import threading
import subprocess
import webbrowser
from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image, ImageOps

from face_analyzer import (
    scan_folder, analyze_folder_parallel, extract_face_thumbnail,
    cluster_faces, categorize_photos
)
from face_cache import CacheManager, generate_grid_thumbnail

app = Flask(__name__)
cache_mgr = CacheManager()

# Global Application State & Job Store
STATE = {
    "active_folder": None,
    "active_job_id": None,
    "recursive": False,   # include the subfolders of the selected folder
    "jobs": {},  # job_id -> dict
}
state_lock = threading.Lock()


def open_native_folder_dialog(initial_dir=None):
    """Safely open native OS folder picker dialog via isolated subprocess."""
    try:
        cmd = ["zenity", "--file-selection", "--directory", "--title=Seleziona Cartella Foto"]
        if initial_dir and os.path.exists(initial_dir):
            cmd.append(f"--filename={initial_dir}/")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        path = res.stdout.strip()
        if path and os.path.exists(path) and os.path.isdir(path):
            return path
    except Exception as e:
        print(f"[WARN] Zenity picker failed: {e}")

    try:
        py_code = (
            "import os, sys, tkinter as tk, tkinter.filedialog as fd; "
            "root=tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
            f"initial = r'{initial_dir}' if r'{initial_dir}' and os.path.exists(r'{initial_dir}') else os.path.expanduser('~'); "
            "p=fd.askdirectory(title='Seleziona Cartella Foto', initialdir=initial); "
            "print(p if p else '')"
        )
        res = subprocess.run([sys.executable, "-c", py_code], capture_output=True, text=True, timeout=180)
        path = res.stdout.strip()
        if path and os.path.exists(path) and os.path.isdir(path):
            return path
    except Exception as e:
        print(f"[WARN] Tkinter subprocess failed: {e}")

    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/select-folder", methods=["POST"])
def select_folder():
    """Select a folder manually or via native dialog."""
    data = request.json or {}
    manual_path = data.get("path")
    use_native = data.get("native", False)
    recursive = bool(data.get("recursive", STATE.get("recursive", False)))

    if manual_path:
        path = manual_path
    elif use_native:
        path = open_native_folder_dialog(STATE.get("active_folder"))
    else:
        path = open_native_folder_dialog(STATE.get("active_folder"))

    if not path or not os.path.exists(path) or not os.path.isdir(path):
        return jsonify({"success": False, "error": "Cartella non valida o annullata"}), 400

    images = scan_folder(path, recursive=recursive)
    with state_lock:
        STATE["active_folder"] = path
        STATE["recursive"] = recursive

    return jsonify({
        "success": True,
        "folder_path": path,
        "photo_count": len(images),
        "recursive": recursive
    })


@app.route("/api/browse-folder", methods=["POST"])
def browse_folder():
    """Endpoint for in-browser Folder Chooser Modal."""
    data = request.json or {}
    target_path = data.get("path") or STATE.get("active_folder") or os.path.expanduser("~")
    recursive = bool(data.get("recursive", STATE.get("recursive", False)))

    if not os.path.exists(target_path) or not os.path.isdir(target_path):
        target_path = os.path.expanduser("~")

    target_path = os.path.abspath(target_path)
    subdirs = []
    photo_count = 0
    exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

    try:
        for item in sorted(os.listdir(target_path)):
            full = os.path.join(target_path, item)
            if os.path.isdir(full) and not item.startswith('.'):
                subdirs.append(item)
            elif os.path.isfile(full):
                if os.path.splitext(item)[1].lower() in exts:
                    photo_count += 1
    except PermissionError:
        return jsonify({"success": False, "error": "Accesso Negato"}), 403

    if recursive:
        photo_count = len(scan_folder(target_path, recursive=True))

    return jsonify({
        "success": True,
        "current_path": target_path,
        "parent_path": os.path.dirname(target_path),
        "subfolders": subdirs,
        "photo_count": photo_count,
        "recursive": recursive
    })


@app.route("/api/scan", methods=["POST"])
def start_scan():
    """Launch asynchronous background scanning job."""
    data = request.json or {}
    folder_path = data.get("folder_path") or STATE.get("active_folder")
    recursive = bool(data.get("recursive", STATE.get("recursive", False)))

    if not folder_path or not os.path.exists(folder_path):
        return jsonify({"success": False, "error": "Nessuna cartella valida da analizzare"}), 400

    images = scan_folder(folder_path, recursive=recursive)
    if not images:
        return jsonify({
            "success": False,
            "error": "Nessuna immagine trovata nella cartella"
                     + ("" if recursive else " (prova con la ricerca ricorsiva)")
        }), 400

    job_id = f"job_{uuid.uuid4().hex[:8]}"

    job = {
        "id": job_id,
        "folder_path": folder_path,
        "folder_name": os.path.basename(folder_path) or folder_path,
        "recursive": recursive,
        "status": "scanning",
        "created_at": time.time(),
        "completed_at": None,
        "progress": {
            "completed": 0,
            "total": len(images),
            "current_file": "Avvio analisi...",
            "pct": 0
        },
        "image_paths": images,
        "face_data": {},
        "clusters": [],
        "face_thumbs": {}
    }

    with state_lock:
        STATE["jobs"][job_id] = job
        STATE["active_job_id"] = job_id
        STATE["active_folder"] = folder_path
        STATE["recursive"] = recursive

    threading.Thread(target=_async_scan_worker, args=(job_id,), daemon=True).start()

    return jsonify({
        "success": True,
        "job_id": job_id,
        "recursive": recursive,
        "message": (f"Scansione avviata in background per {os.path.basename(folder_path)}"
                    + (" (sottocartelle incluse)" if recursive else ""))
    })


def _async_scan_worker(job_id: str):
    """Background worker executing safe sequential scan & face clustering."""
    with state_lock:
        job = STATE["jobs"].get(job_id)

    if not job:
        return

    folder_path = job["folder_path"]
    image_paths = job["image_paths"]
    total = len(image_paths)

    def progress_cb(completed, total_cnt, current_name):
        with state_lock:
            if job_id in STATE["jobs"]:
                pct = Math_round((completed / total_cnt) * 100) if total_cnt > 0 else 0
                STATE["jobs"][job_id]["progress"] = {
                    "completed": completed,
                    "total": total_cnt,
                    "current_file": current_name,
                    "pct": pct
                }

    try:
        face_data = analyze_folder_parallel(image_paths, cache_mgr, progress_cb)
        clusters = cluster_faces(face_data)

        face_thumbs = {}
        for i, c in enumerate(clusters):
            src_path, src_loc = c['thumbnail_source']
            thumb = extract_face_thumbnail(src_path, src_loc, size=140)
            if thumb:
                buf = io.BytesIO()
                thumb.save(buf, format="JPEG", quality=85)
                face_thumbs[i] = buf.getvalue()

        total_faces = sum(len(encs) for encs, _ in face_data.values())
        cache_mgr.add_to_history(folder_path, photo_count=total, faces_count=total_faces, clusters_count=len(clusters))

        with state_lock:
            if job_id in STATE["jobs"]:
                j = STATE["jobs"][job_id]
                j["face_data"] = face_data
                j["clusters"] = clusters
                j["face_thumbs"] = face_thumbs
                j["status"] = "completed"
                j["completed_at"] = time.time()
                j["progress"]["pct"] = 100
                j["progress"]["current_file"] = "Completato con successo!"

    except Exception as e:
        print(f"[JOB ERROR] Failed job {job_id}: {e}")
        with state_lock:
            if job_id in STATE["jobs"]:
                STATE["jobs"][job_id]["status"] = "error"
                STATE["jobs"][job_id]["progress"]["current_file"] = f"Errore: {e}"


def Math_round(val):
    return int(round(val))


@app.route("/api/jobs")
def get_jobs():
    """List all current and past scan jobs."""
    with state_lock:
        job_list = []
        for jid, job in sorted(STATE["jobs"].items(), key=lambda x: x[1]["created_at"], reverse=True):
            job_list.append({
                "id": job["id"],
                "folder_path": job["folder_path"],
                "folder_name": job["folder_name"],
                "recursive": job.get("recursive", False),
                "status": job["status"],
                "created_at": job["created_at"],
                "date_str": time.strftime("%H:%M:%S", time.localtime(job["created_at"])),
                "progress": job["progress"],
                "total_photos": len(job["image_paths"]),
                "clusters_count": len(job["clusters"])
            })
    return jsonify({"success": True, "jobs": job_list})


@app.route("/api/results")
def get_results():
    job_id = request.args.get("job_id") or STATE.get("active_job_id")
    target_idx = request.args.get("target_idx", type=int)

    with state_lock:
        if not job_id or job_id not in STATE["jobs"]:
            return jsonify({"success": False, "error": "Nessuna scansione attiva"}), 400
        job = STATE["jobs"][job_id]
        STATE["active_job_id"] = job_id

    if job["status"] == "scanning":
        return jsonify({
            "success": False,
            "status": "scanning",
            "progress": job["progress"]
        }), 202

    image_paths = job["image_paths"]
    face_data = job["face_data"]
    clusters = job["clusters"]

    cluster_summaries = []
    for i, c in enumerate(clusters):
        cluster_summaries.append({
            "idx": i,
            "photo_count": c["photo_count"],
            "face_count": c.get("face_count", len(c["encodings"])),
            "is_top": (i == 0)
        })

    if target_idx is not None and 0 <= target_idx < len(clusters):
        target = clusters[target_idx]
    else:
        target_idx = None
        target = None

    with_t, without_t, no_face = categorize_photos(image_paths, face_data, target)

    return jsonify({
        "success": True,
        "job_id": job_id,
        "folder_path": job["folder_path"],
        "recursive": job.get("recursive", False),
        "total_photos": len(image_paths),
        "clusters": cluster_summaries,
        "selected_target": target_idx,
        "photos": {
            "with_target": with_t,
            "without_target": without_t,
            "no_faces": no_face
        }
    })


@app.route("/api/image")
def get_image():
    path = request.args.get("path")
    size = request.args.get("size", default="full")

    if not path or not os.path.exists(path):
        return "File non trovato", 404

    if size == "full":
        return send_file(path)

    try:
        max_size = int(size)
    except ValueError:
        max_size = 280

    cached = cache_mgr.get_cached_image(path)
    if cached and cached[2]:
        return send_file(io.BytesIO(cached[2]), mimetype="image/jpeg")

    thumb_bytes = generate_grid_thumbnail(path, max_size=max_size)
    if thumb_bytes:
        return send_file(io.BytesIO(thumb_bytes), mimetype="image/jpeg")

    return send_file(path)


@app.route("/api/face-thumb/<int:idx>")
def get_face_thumb(idx):
    job_id = request.args.get("job_id") or STATE.get("active_job_id")
    with state_lock:
        job = STATE["jobs"].get(job_id) if job_id else None
        thumb_bytes = job["face_thumbs"].get(idx) if job else None

    if thumb_bytes:
        return send_file(io.BytesIO(thumb_bytes), mimetype="image/jpeg")
    return "Non trovata", 404


@app.route("/api/history", methods=["GET", "DELETE"])
def history():
    if request.method == "DELETE":
        path = request.args.get("path")
        if path:
            cache_mgr.delete_history_item(path)
        else:
            cache_mgr.clear_all_history()
        return jsonify({"success": True})

    items = cache_mgr.get_history_list()
    for item in items:
        item["exists"] = os.path.exists(item["path"])
        item["date_str"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["scanned_at"]))

    return jsonify({"success": True, "history": items})


def run_app():
    port = 5000
    url = f"http://127.0.0.1:{port}"
    print(f"\n🚀 Server Flask avviato su {url}\n")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    run_app()
