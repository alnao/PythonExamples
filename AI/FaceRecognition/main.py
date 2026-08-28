#!/usr/bin/env python3
"""
Face Recognition Photo Analyzer — Fast, Cached & Bootstrap Theme GUI
Analyzes photos, finds frequent faces, categorizes photos, caches encodings,
and persists scan history.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import time
import io
from PIL import Image, ImageOps
from typing import List, Dict, Optional

from face_analyzer import (
    scan_folder, analyze_folder_parallel, extract_face_thumbnail,
    cluster_faces, categorize_photos,
)
from face_cache import CacheManager

# ── Styling & Bootstrap Color Palette ────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Bootstrap 5 Dark Theme Tokens
BG_DARK = "#121417"          # Dark body background
BG_HEADER = "#1b1e22"        # Navbar / Header dark
BG_CARD = "#212529"          # Card background
BG_CARD_INNER = "#2b3035"    # Sub-card / container bg
BG_HOVER = "#343a40"         # Hover state
BS_BORDER = "#495057"        # Bootstrap dark border

BS_PRIMARY = "#0d6efd"       # Primary Blue
BS_PRIMARY_HOVER = "#0b5ed7"
BS_SECONDARY = "#6c757d"     # Secondary Gray
BS_SECONDARY_HOVER = "#5c636a"
BS_SUCCESS = "#198754"       # Success Green
BS_SUCCESS_HOVER = "#157347"
BS_DANGER = "#dc3545"        # Danger Red
BS_DANGER_HOVER = "#bb2d3b"
BS_WARNING = "#ffc107"       # Warning Yellow
BS_INFO = "#0dcaf0"          # Info Cyan

TEXT = "#f8f9fa"             # Text primary
TEXT_MUTED = "#adb5bd"       # Text muted
TEXT_DIM = "#dee2e6"

FACE_SIZE = 110

SIZE_MAP = {
    "Piccolo": (190, 4),
    "Medio": (280, 3),
    "Grande": (380, 2),
}


# ── Asynchronous & Scalable Photo Grid ───────────────────────────────────
class PhotoGrid(ctk.CTkScrollableFrame):
    """Scrollable grid of photo thumbnails with async background loading."""

    def __init__(self, master, app=None, thumb_size=280, columns=3, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.app = app
        self.thumb_size = thumb_size
        self.columns = columns
        self._refs = {}
        self.paths = []
        self._load_token = 0

    def set_config(self, thumb_size: int, columns: int):
        self.thumb_size = thumb_size
        self.columns = columns

    def clear(self):
        self._load_token += 1
        for w in self.winfo_children():
            w.destroy()
        self._refs.clear()

    def display(self, paths: list):
        self.clear()
        self.paths = paths
        self._load_token += 1
        token = self._load_token

        if not paths:
            lbl = ctk.CTkLabel(self, text="Nessuna foto in questa categoria",
                               font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_MUTED)
            lbl.grid(row=0, column=0, columnspan=self.columns, pady=60)
            return

        for c in range(self.columns):
            self.grid_columnconfigure(c, weight=1)

        # 1. Immediate UI skeleton creation (placeholder)
        self.card_widgets = []
        for i, p in enumerate(paths):
            r, c = divmod(i, self.columns)
            card = ctk.CTkFrame(self, corner_radius=8, fg_color=BG_CARD, border_width=1, border_color=BS_BORDER)
            card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

            placeholder_lbl = ctk.CTkLabel(card, text="🖼️", font=ctk.CTkFont(size=32), text_color=BS_SECONDARY)
            placeholder_lbl.pack(padx=6, pady=(10, 0), expand=True)

            name = os.path.basename(p)
            max_char = int(self.thumb_size / 9)
            if len(name) > max_char:
                name = name[:max_char-3] + "…"
            name_lbl = ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED)
            name_lbl.pack(padx=6, pady=(6, 8))

            def _bind_dbl(widget, idx=i):
                widget.bind("<Double-Button-1>", lambda e: self.app._open_preview_modal(self.paths, idx))
            _bind_dbl(card)
            _bind_dbl(placeholder_lbl)
            _bind_dbl(name_lbl)

            self.card_widgets.append((card, placeholder_lbl))

        # 2. Async background image thumbnail worker thread
        threading.Thread(target=self._load_thumbnails_async, args=(token, paths), daemon=True).start()

    def _load_thumbnails_async(self, token: int, paths: list):
        """Load thumbnails in background thread pool."""
        cache_mgr = self.app.cache_mgr if self.app else None

        for i, p in enumerate(paths):
            if self._load_token != token:
                return

            sq_img = None
            if cache_mgr:
                cached = cache_mgr.get_cached_image(p)
                if cached and cached[2]:  # thumb_blob
                    try:
                        sq_img = Image.open(io.BytesIO(cached[2])).convert("RGB")
                    except Exception:
                        pass

            if sq_img is None:
                try:
                    with Image.open(p) as orig:
                        img = ImageOps.exif_transpose(orig).convert("RGB")
                        img.thumbnail((self.thumb_size, self.thumb_size), Image.LANCZOS)
                        sq_img = Image.new("RGB", (self.thumb_size, self.thumb_size), (33, 37, 41))
                        sq_img.paste(img, ((self.thumb_size - img.width) // 2,
                                           (self.thumb_size - img.height) // 2))
                except Exception:
                    sq_img = None

            if sq_img and self._load_token == token:
                ci = ctk.CTkImage(light_image=sq_img, dark_image=sq_img,
                                  size=(self.thumb_size, self.thumb_size))
                self.after(0, self._apply_thumbnail, token, i, ci)

    def _apply_thumbnail(self, token: int, idx: int, ci: ctk.CTkImage):
        if self._load_token != token or idx >= len(self.card_widgets):
            return
        card, placeholder_lbl = self.card_widgets[idx]
        self._refs[idx] = ci
        placeholder_lbl.configure(image=ci, text="")
        placeholder_lbl.pack(padx=6, pady=(6, 0))


# ── Main Application Window ──────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("👤 Face Recognition Photo Analyzer")
        self.geometry("1380x900")
        self.minsize(1040, 700)
        self.configure(fg_color=BG_DARK)

        # Cache & database engine
        self.cache_mgr = CacheManager()

        # Application state
        self.folder_path = None
        self.image_paths = []
        self.face_data = {}
        self.clusters = []
        self.face_thumbs = []
        self.selected_cluster_idx = 0
        self.thumb_size_name = "Medio"
        self._face_refs = []

        self._build_header()
        self._build_active_folder_bar()
        self._build_body()
        self._show_welcome()

    # ── Header Bar ───────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=65)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Title
        ctk.CTkLabel(hdr, text="👤  Face Recognition Analyzer",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=TEXT).pack(side="left", padx=20)

        # Controls
        ctrl = ctk.CTkFrame(hdr, fg_color="transparent")
        ctrl.pack(side="right", padx=20)

        # Size menu selector
        ctk.CTkLabel(ctrl, text="Dimensione Foto:", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))
        self.menu_size = ctk.CTkOptionMenu(
            ctrl, values=["Piccolo", "Medio", "Grande"], width=110, fg_color=BG_CARD_INNER,
            button_color=BS_PRIMARY, button_hover_color=BS_PRIMARY_HOVER,
            dropdown_fg_color=BG_CARD,
            command=self._on_change_thumb_size
        )
        self.menu_size.set("Medio")
        self.menu_size.pack(side="left", padx=(0, 15))

        # Recursive scan toggle
        self.recursive_var = ctk.BooleanVar(value=False)
        self.chk_recursive = ctk.CTkCheckBox(
            ctrl, text="🔁 Sottocartelle", variable=self.recursive_var,
            font=ctk.CTkFont(size=12), text_color=TEXT_MUTED,
            fg_color=BS_PRIMARY, hover_color=BS_PRIMARY_HOVER,
            checkbox_width=18, checkbox_height=18,
        )
        self.chk_recursive.pack(side="left", padx=(0, 15))

        # History button
        btn_hist = ctk.CTkButton(
            ctrl, text="📜 Cronologia", width=130, fg_color=BS_SECONDARY, hover_color=BS_SECONDARY_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"), command=self._open_history_modal
        )
        btn_hist.pack(side="left", padx=(0, 10))

        # Select folder button (system standard dialog)
        self.btn_folder = ctk.CTkButton(
            ctrl, text="📁 Seleziona Cartella", width=180,
            fg_color=BS_PRIMARY, hover_color=BS_PRIMARY_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_folder_dialog,
        )
        self.btn_folder.pack(side="left", padx=(0, 10))

        # Analyze button
        self.btn_analyze = ctk.CTkButton(
            ctrl, text="▶  Analizza", width=115,
            fg_color=BS_SUCCESS, hover_color=BS_SUCCESS_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_analysis, state="disabled",
        )
        self.btn_analyze.pack(side="left")

    # ── Active Folder Status Banner ──────────────────────────────────
    def _build_active_folder_bar(self):
        self.active_bar = ctk.CTkFrame(self, fg_color="#181b1f", corner_radius=0, height=44)
        self.active_bar.pack(fill="x")
        self.active_bar.pack_propagate(False)

        lbl_tag = ctk.CTkLabel(self.active_bar, text=" CARTELLA ATTIVA ", font=ctk.CTkFont(size=11, weight="bold"),
                               fg_color=BS_PRIMARY, text_color=TEXT, corner_radius=4)
        lbl_tag.pack(side="left", padx=(20, 12))

        self.lbl_active_path = ctk.CTkLabel(
            self.active_bar, text="Nessuna cartella selezionata",
            font=ctk.CTkFont(size=13), text_color=TEXT_MUTED
        )
        self.lbl_active_path.pack(side="left")

        # Copy path button
        self.btn_copy_path = ctk.CTkButton(
            self.active_bar, text="📋 Copia Percorso", width=120, height=28,
            fg_color="transparent", hover_color=BG_HOVER, text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11), command=self._copy_active_path
        )
        self.btn_copy_path.pack(side="right", padx=20)

    # ── Main Layout Body ─────────────────────────────────────────────
    def _build_body(self):
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

        # Progress bar frame (hidden by default)
        self.progress_frame = ctk.CTkFrame(self.body, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BS_BORDER)
        self.progress_lbl = ctk.CTkLabel(self.progress_frame, text="", font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT)
        self.progress_sublbl = ctk.CTkLabel(self.progress_frame, text="", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED)
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=560, height=14, progress_color=BS_PRIMARY)

        # Sidebar for faces
        self.sidebar = ctk.CTkScrollableFrame(self.body, width=320, fg_color=BG_CARD, corner_radius=0)

        # Right Content Area
        self.content = ctk.CTkFrame(self.body, fg_color="transparent")

        # Stats summary bar
        self.stats_frame = ctk.CTkFrame(self.content, fg_color=BG_CARD, corner_radius=8, height=48, border_width=1, border_color=BS_BORDER)
        self.stats_lbl = ctk.CTkLabel(self.stats_frame, text="", font=ctk.CTkFont(size=13), text_color=TEXT)

        # Tabs container
        self.tabview = ctk.CTkTabview(self.content, fg_color=BG_DARK,
                                      segmented_button_fg_color=BG_CARD,
                                      segmented_button_selected_color=BS_PRIMARY,
                                      segmented_button_unselected_color=BG_CARD_INNER)

    def _show_welcome(self):
        self.welcome = ctk.CTkFrame(self.body, fg_color="transparent")
        self.welcome.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(self.welcome, fg_color="transparent")
        inner.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(inner, text="👤", font=ctk.CTkFont(size=84)).pack()
        ctk.CTkLabel(inner, text="Face Recognition Photo Analyzer",
                     font=ctk.CTkFont(size=28, weight="bold"), text_color=TEXT).pack(pady=(10, 5))
        ctk.CTkLabel(inner, text=(
            "Analizza qualsiasi cartella con riconoscimento facciale ad alte prestazioni e cache SQLite.\n"
            "Trova automaticamente le persone più frequenti e organizza le foto."
        ), font=ctk.CTkFont(size=14), text_color=TEXT_MUTED, justify="center").pack(pady=(0, 25))

        btn_box = ctk.CTkFrame(inner, fg_color="transparent")
        btn_box.pack()

        ctk.CTkButton(btn_box, text="📁  Seleziona Cartella", width=220, height=46,
                      fg_color=BS_PRIMARY, hover_color=BS_PRIMARY_HOVER,
                      font=ctk.CTkFont(size=15, weight="bold"),
                      command=self._open_folder_dialog).pack(side="left", padx=8)

        ctk.CTkButton(btn_box, text="📜  Cronologia", width=160, height=46,
                      fg_color=BS_SECONDARY, hover_color=BS_SECONDARY_HOVER,
                      font=ctk.CTkFont(size=15, weight="bold"),
                      command=self._open_history_modal).pack(side="left", padx=8)

    def _hide_welcome(self):
        if hasattr(self, "welcome") and self.welcome.winfo_exists():
            self.welcome.destroy()

    # ── System Standard Folder Selection ─────────────────────────────
    def _open_folder_dialog(self):
        initial = self.folder_path or os.path.expanduser("~")
        chosen = filedialog.askdirectory(title="Seleziona Cartella Foto", initialdir=initial)
        if chosen:
            self._on_folder_selected(chosen)

    def _on_folder_selected(self, path: str):
        if not path or not os.path.exists(path):
            return
        self.folder_path = path
        self.lbl_active_path.configure(text=path, text_color=TEXT)
        self.btn_analyze.configure(state="normal")
        self._start_analysis()

    def _copy_active_path(self):
        if self.folder_path:
            self.clipboard_clear()
            self.clipboard_append(self.folder_path)
            messagebox.showinfo("Copiato", f"Percorso copiato negli appunti:\n{self.folder_path}")

    def _on_change_thumb_size(self, choice: str):
        self.thumb_size_name = choice
        if hasattr(self, 'grid_with') and self.grid_with and self.grid_with.winfo_exists():
            thumb_sz, cols = SIZE_MAP[choice]
            for grid in (self.grid_with, self.grid_without, self.grid_noface):
                if grid:
                    grid.set_config(thumb_sz, cols)
                    grid.display(grid.paths)

    def _start_analysis(self):
        if not self.folder_path:
            return
        recursive = bool(self.recursive_var.get())
        self.image_paths = scan_folder(self.folder_path, recursive=recursive)
        if not self.image_paths:
            hint = "" if recursive else "\n\nSuggerimento: attiva 🔁 Sottocartelle per cercare anche nelle sottocartelle."
            messagebox.showwarning(
                "Nessun File",
                f"Nessuna immagine (.jpg, .png, .webp) trovata in questa cartella.{hint}"
            )
            return

        self._hide_welcome()
        self._show_progress()
        self.btn_analyze.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        self.chk_recursive.configure(state="disabled")

        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _show_progress(self):
        self.sidebar.pack_forget()
        self.content.pack_forget()

        self.progress_frame.place(relx=0.5, rely=0.45, anchor="center", width=640, height=230)
        self.progress_lbl.pack(pady=(25, 4))
        self.progress_sublbl.pack(pady=(0, 15))
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        self.progress_lbl.configure(text="Scansione in corso...")
        self.progress_sublbl.configure(text="Controllo cache SQLite e rilevamento volti...")

    def _hide_progress(self):
        self.progress_frame.place_forget()

    def _run_analysis(self):
        """Background thread: Parallel analysis + SQLite cache."""
        start_time = time.time()
        total = len(self.image_paths)

        def progress_cb(completed, total_cnt, current_name):
            pct = completed / total_cnt
            self.after(0, self._update_progress, pct,
                       f"Rilevamento volti: {completed}/{total_cnt}", current_name)

        self.face_data = analyze_folder_parallel(
            self.image_paths, self.cache_mgr, progress_cb
        )

        self.after(0, self._update_progress, 0.95, "Clustering volti...", "Raggruppamento per somiglianza...")
        self.clusters = cluster_faces(self.face_data)

        self.face_thumbs = []
        for c in self.clusters:
            src_path, src_loc = c['thumbnail_source']
            thumb = extract_face_thumbnail(src_path, src_loc, FACE_SIZE)
            self.face_thumbs.append(thumb)

        total_faces = sum(len(encs) for encs, _ in self.face_data.values())
        self.cache_mgr.add_to_history(
            self.folder_path, photo_count=total, faces_count=total_faces, clusters_count=len(self.clusters)
        )

        duration = time.time() - start_time
        print(f"[PERF] Scanned {total} photos in {duration:.2f}s")
        self.after(0, self._analysis_done)

    def _update_progress(self, pct, title, subtitle):
        self.progress_bar.set(pct)
        self.progress_lbl.configure(text=title)
        self.progress_sublbl.configure(text=subtitle)

    def _analysis_done(self):
        self._hide_progress()
        self.btn_analyze.configure(state="normal")
        self.btn_folder.configure(state="normal")
        self.chk_recursive.configure(state="normal")

        if not self.clusters:
            messagebox.showinfo("Risultato Scansione", "Nessun volto rilevato nelle immagini analizzate.")
            self._categorize_and_show(target_idx=None)
            return

        self.selected_cluster_idx = 0
        self._build_sidebar()
        self._categorize_and_show(target_idx=0)

    # ── Faces Sidebar ────────────────────────────────────────────────
    def _build_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()
        self._face_refs.clear()

        ctk.CTkLabel(self.sidebar, text="👥  Volti Identificati",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT).pack(pady=(15, 12), padx=10)

        for i, (cluster, thumb) in enumerate(zip(self.clusters, self.face_thumbs)):
            selected = (i == self.selected_cluster_idx)
            card = ctk.CTkFrame(
                self.sidebar, corner_radius=8,
                fg_color=BS_PRIMARY if selected else BG_CARD_INNER,
                border_width=1,
                border_color=BS_BORDER,
            )
            card.pack(fill="x", padx=10, pady=6)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=10)

            if thumb:
                ci = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(FACE_SIZE, FACE_SIZE))
                self._face_refs.append(ci)
                ctk.CTkLabel(row, image=ci, text="").pack(side="left", padx=(0, 12))

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True)

            ctk.CTkLabel(info, text=f"Persona {i+1}", font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=TEXT, anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=f"📸  {cluster['photo_count']} foto", font=ctk.CTkFont(size=12),
                         text_color=TEXT_MUTED if not selected else "#e0e7ff", anchor="w").pack(anchor="w")

            if i == 0:
                ctk.CTkLabel(info, text="⭐ Più Frequente", font=ctk.CTkFont(size=11, weight="bold"),
                             text_color=BS_WARNING, anchor="w").pack(anchor="w", pady=(2, 0))

            def _bind_click(widget, idx=i):
                widget.bind("<Button-1>", lambda e: self._select_face(idx))
                for child in widget.winfo_children():
                    _bind_click(child, idx)
            _bind_click(card, i)

    def _select_face(self, idx):
        if idx == self.selected_cluster_idx:
            return
        self.selected_cluster_idx = idx
        self._build_sidebar()
        self._categorize_and_show(target_idx=idx)

    # ── Display Categorized Grid ─────────────────────────────────────
    def _categorize_and_show(self, target_idx: Optional[int]):
        target = None
        if target_idx is not None and 0 <= target_idx < len(self.clusters):
            target = self.clusters[target_idx]
        else:
            target_idx = None

        with_t, without_t, no_face = categorize_photos(
            self.image_paths, self.face_data, target
        )

        self.sidebar.pack(side="left", fill="y")
        self.content.pack(side="left", fill="both", expand=True)

        # Stats summary
        self.stats_frame.pack(fill="x", padx=14, pady=(10, 0))
        self.stats_lbl.pack(padx=14, pady=10)
        total = len(self.image_paths)
        person = f"Persona {(target_idx or 0) + 1}" if target_idx is not None else "—"

        self.stats_lbl.configure(
            text=(f"📊  {total} foto  ·  Filtro: {person}  ·  "
                  f"✅ Con persona ({len(with_t)})  ·  "
                  f"❌ Senza persona ({len(without_t)})  ·  "
                  f"🚫 Nessun volto ({len(no_face)})")
        )

        # Re-build tabs
        self.tabview.pack(fill="both", expand=True, padx=14, pady=10)
        for name in list(self.tabview._tab_dict.keys()):
            self.tabview.delete(name)

        tab_with = self.tabview.add(f"✅ Con Persona ({len(with_t)})")
        tab_without = self.tabview.add(f"❌ Senza Persona ({len(without_t)})")
        tab_noface = self.tabview.add(f"🚫 Nessun Volto ({len(no_face)})")

        thumb_sz, cols = SIZE_MAP[self.thumb_size_name]

        self.grid_with = PhotoGrid(tab_with, app=self, thumb_size=thumb_sz, columns=cols)
        self.grid_with.pack(fill="both", expand=True)
        self.grid_with.display(with_t)

        self.grid_without = PhotoGrid(tab_without, app=self, thumb_size=thumb_sz, columns=cols)
        self.grid_without.pack(fill="both", expand=True)
        self.grid_without.display(without_t)

        self.grid_noface = PhotoGrid(tab_noface, app=self, thumb_size=thumb_sz, columns=cols)
        self.grid_noface.pack(fill="both", expand=True)
        self.grid_noface.display(no_face)

        # Default tab selection
        self.tabview.set(f"❌ Senza Persona ({len(without_t)})")

    # ── History Modal Window (Larger Popup) ──────────────────────────
    def _open_history_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("📜 Cronologia Scansioni")
        modal.geometry("980x660")
        modal.minsize(780, 520)
        modal.configure(fg_color=BG_DARK)
        modal.transient(self)
        modal.grab_set()
        modal.focus_force()

        hdr = ctk.CTkFrame(modal, fg_color=BG_HEADER, corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="📜  Cronologia Scansioni Passate", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(side="left", padx=20)

        btn_clear = ctk.CTkButton(hdr, text="🗑️ Pulisci Tutto", width=120, height=34, fg_color=BS_DANGER, hover_color=BS_DANGER_HOVER,
                                  font=ctk.CTkFont(size=12, weight="bold"), command=lambda: self._clear_all_history(modal))
        btn_clear.pack(side="right", padx=20)

        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=20)

        history_items = self.cache_mgr.get_history_list()

        if not history_items:
            lbl = ctk.CTkLabel(scroll, text="Nessuna scansione salvata in cronologia", font=ctk.CTkFont(size=15), text_color=TEXT_MUTED)
            lbl.pack(pady=60)
            return

        for item in history_items:
            path = item["path"]
            exists = os.path.exists(path)
            card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BS_BORDER)
            card.pack(fill="x", pady=8)

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=16, pady=12)

            fname = os.path.basename(path) or path
            ctk.CTkLabel(info_frame, text=fname, font=ctk.CTkFont(size=15, weight="bold"),
                         text_color=TEXT if exists else TEXT_MUTED, anchor="w").pack(anchor="w")

            date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["scanned_at"]))
            details = f"📍 {path}\n📸 {item['photo_count']} Foto  ·  👥 {item['clusters_count']} Personaggi  ·  Data: {date_str}"
            ctk.CTkLabel(info_frame, text=details, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED, anchor="w", justify="left").pack(anchor="w", pady=(3, 0))

            btn_box = ctk.CTkFrame(card, fg_color="transparent")
            btn_box.pack(side="right", padx=14)

            if exists:
                btn_load = ctk.CTkButton(btn_box, text="🔄 Ricarica", width=105, height=34, fg_color=BS_PRIMARY, hover_color=BS_PRIMARY_HOVER,
                                         font=ctk.CTkFont(size=13, weight="bold"), command=lambda p=path: self._load_from_history(modal, p))
                btn_load.pack(side="left", padx=4)

            def _del_item(p=path):
                self.cache_mgr.delete_history_item(p)
                modal.destroy()
                self._open_history_modal()

            btn_del = ctk.CTkButton(btn_box, text="❌", width=38, height=34, fg_color=BS_SECONDARY, hover_color=BS_DANGER, command=_del_item)
            btn_del.pack(side="left", padx=4)

    def _clear_all_history(self, modal):
        if messagebox.askyesno("Conferma", "Vuoi cancellare tutta la cronologia delle scansioni?"):
            self.cache_mgr.clear_all_history()
            modal.destroy()
            self._open_history_modal()

    def _load_from_history(self, modal, path: str):
        modal.destroy()
        self._on_folder_selected(path)

    # ── Fullscreen Preview Modal (Larger Popup) ───────────────────────
    def _open_preview_modal(self, paths: list, current_idx: int):
        if not paths:
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Anteprima Immagine")
        modal.geometry("1240x880")
        modal.minsize(920, 640)
        modal.configure(fg_color="#0a0c0e")
        modal.transient(self)
        modal.grab_set()
        modal.focus_force()

        state = {"idx": current_idx, "img_ref": None}

        # Header
        hdr = ctk.CTkFrame(modal, fg_color=BG_HEADER, height=55, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        lbl_counter = ctk.CTkLabel(hdr, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_MUTED)
        lbl_counter.pack(side="left", padx=20)

        lbl_filename = ctk.CTkLabel(hdr, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT)
        lbl_filename.pack(side="left", padx=10)

        btn_close = ctk.CTkButton(hdr, text="✕ Chiudi", width=90, height=36, fg_color=BS_DANGER, hover_color=BS_DANGER_HOVER,
                                  font=ctk.CTkFont(size=13, weight="bold"), command=modal.destroy)
        btn_close.pack(side="right", padx=20)

        # Image view container with previous/next arrows
        main_area = ctk.CTkFrame(modal, fg_color="transparent")
        main_area.pack(fill="both", expand=True, padx=15, pady=15)

        btn_prev = ctk.CTkButton(main_area, text="◀", width=60, height=60, fg_color=BG_CARD_INNER, hover_color=BS_PRIMARY,
                                 font=ctk.CTkFont(size=24, weight="bold"))
        btn_prev.pack(side="left", padx=(5, 12))

        img_container = ctk.CTkFrame(main_area, fg_color="#121417", corner_radius=10, border_width=1, border_color=BS_BORDER)
        img_container.pack(side="left", fill="both", expand=True)

        img_label = ctk.CTkLabel(img_container, text="", fg_color="transparent")
        img_label.pack(fill="both", expand=True, padx=12, pady=12)

        btn_next = ctk.CTkButton(main_area, text="▶", width=60, height=60, fg_color=BG_CARD_INNER, hover_color=BS_PRIMARY,
                                 font=ctk.CTkFont(size=24, weight="bold"))
        btn_next.pack(side="right", padx=(12, 5))

        def render_image():
            idx = state["idx"]
            path = paths[idx]
            # With a recursive scan show the path relative to the analyzed folder
            fname = os.path.basename(path)
            if self.folder_path and path.startswith(self.folder_path.rstrip(os.sep) + os.sep):
                fname = os.path.relpath(path, self.folder_path)

            lbl_counter.configure(text=f"[{idx + 1} / {len(paths)}]")
            lbl_filename.configure(text=fname if len(fname) < 55 else fname[:52] + "…")

            btn_prev.configure(state="normal" if idx > 0 else "disabled")
            btn_next.configure(state="normal" if idx < len(paths) - 1 else "disabled")

            modal.update_idletasks()
            w = max(img_container.winfo_width() - 28, 550)
            h = max(img_container.winfo_height() - 28, 420)

            try:
                with Image.open(path) as orig:
                    img = ImageOps.exif_transpose(orig).convert("RGB")
                    img.thumbnail((w, h), Image.LANCZOS)
                    ci = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                    state["img_ref"] = ci
                    img_label.configure(image=ci, text="")
            except Exception:
                img_label.configure(image="", text="⚠️ Errore caricamento immagine", font=ctk.CTkFont(size=16), text_color=BS_WARNING)

        def go_prev():
            if state["idx"] > 0:
                state["idx"] -= 1
                render_image()

        def go_next():
            if state["idx"] < len(paths) - 1:
                state["idx"] += 1
                render_image()

        btn_prev.configure(command=go_prev)
        btn_next.configure(command=go_next)

        modal.bind("<Left>", lambda e: go_prev())
        modal.bind("<Right>", lambda e: go_next())
        modal.bind("<Escape>", lambda e: modal.destroy())

        modal.after(10, render_image)


# ── Entry Point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
