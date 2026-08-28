"""
Custom Folder Selection Dialog — Sleek Modern Interface
Allows path browsing, quick shortcuts, recent folder selection, and live image count preview.
"""

import os
import customtkinter as ctk
from tkinter import filedialog
from typing import Optional, Callable, List

BG_DARK = "#12121a"
BG_CARD = "#1a1a28"
BG_HOVER = "#26263a"
ACCENT = "#7c3aed"
ACCENT_LIGHT = "#a78bfa"
TEXT = "#f3f4f6"
TEXT_DIM = "#9ca3af"

class FolderSelectionDialog(ctk.CTkToplevel):
    def __init__(self, master, current_path: Optional[str] = None, history_paths: Optional[List[str]] = None, on_select: Optional[Callable[[str], None]] = None):
        super().__init__(master)
        self.title("📁 Seleziona Cartella Foto")
        self.geometry("780x560")
        self.minsize(640, 480)
        self.configure(fg_color=BG_DARK)
        self.transient(master)
        self.grab_set()
        self.focus_force()

        self.on_select_callback = on_select
        self.selected_path = current_path if (current_path and os.path.exists(current_path)) else os.path.expanduser("~")
        self.history_paths = history_paths or []

        self._build_ui()
        self._navigate(self.selected_path)

    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="#181824", corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="📁  Seleziona Cartella Immaggini", font=ctk.CTkFont(size=18, weight="bold"), text_color="#ffffff").pack(side="left", padx=20)
        
        btn_native = ctk.CTkButton(hdr, text="🖥️ Esplora Sistema", width=140, fg_color="#2b2b3d", hover_color=ACCENT, font=ctk.CTkFont(size=12, weight="bold"), command=self._use_native_dialog)
        btn_native.pack(side="right", padx=20)

        # Path bar & Quick shortcuts
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(15, 10))

        btn_up = ctk.CTkButton(bar, text="⬆️ Su", width=60, fg_color="#262638", hover_color=ACCENT, font=ctk.CTkFont(size=12, weight="bold"), command=self._go_up)
        btn_up.pack(side="left", padx=(0, 10))

        self.entry_path = ctk.CTkEntry(bar, font=ctk.CTkFont(size=13), fg_color="#1c1c2b", border_color=ACCENT_LIGHT, text_color=TEXT)
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_path.bind("<Return>", lambda e: self._navigate(self.entry_path.get()))

        btn_go = ctk.CTkButton(bar, text="Vai", width=60, fg_color=ACCENT, hover_color=ACCENT_LIGHT, font=ctk.CTkFont(size=12, weight="bold"), command=lambda: self._navigate(self.entry_path.get()))
        btn_go.pack(side="left")

        # Shortcuts frame
        sc_frame = ctk.CTkFrame(self, fg_color="transparent")
        sc_frame.pack(fill="x", padx=20, pady=(0, 10))

        shortcuts = [
            ("🏠 Home", os.path.expanduser("~")),
            ("🖼️ Immagini", os.path.expanduser("~/Pictures")),
            ("📥 Download", os.path.expanduser("~/Downloads")),
            ("🖥️ Desktop", os.path.expanduser("~/Desktop"))
        ]

        for label, path in shortcuts:
            if os.path.exists(path):
                btn = ctk.CTkButton(sc_frame, text=label, width=100, height=28, fg_color="#222234", hover_color="#32324c", text_color=TEXT_DIM, font=ctk.CTkFont(size=11), command=lambda p=path: self._navigate(p))
                btn.pack(side="left", padx=(0, 8))

        # Main content area: Split between Folder Tree/List and Recent History
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Left: Folder List
        left_box = ctk.CTkFrame(main_split, fg_color=BG_CARD, corner_radius=10)
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(left_box, text="Sottocartelle disponibili", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_DIM).pack(anchor="w", padx=12, pady=(10, 5))

        self.subfolder_scroll = ctk.CTkScrollableFrame(left_box, fg_color="transparent")
        self.subfolder_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Right: Recent History & Info Preview
        right_box = ctk.CTkFrame(main_split, width=240, fg_color=BG_CARD, corner_radius=10)
        right_box.pack(side="right", fill="both", expand=False)
        right_box.pack_propagate(False)

        ctk.CTkLabel(right_box, text="📜 Cartelle Recenti", font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_DIM).pack(anchor="w", padx=12, pady=(10, 5))

        self.history_scroll = ctk.CTkScrollableFrame(right_box, fg_color="transparent")
        self.history_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        self._populate_history()

        # Bottom Action & Preview Footer
        ftr = ctk.CTkFrame(self, fg_color="#181824", corner_radius=0, height=65)
        ftr.pack(fill="x", side="bottom")
        ftr.pack_propagate(False)

        self.lbl_preview = ctk.CTkLabel(ftr, text="Caricamento info cartella...", font=ctk.CTkFont(size=13), text_color=ACCENT_LIGHT)
        self.lbl_preview.pack(side="left", padx=20)

        btn_confirm = ctk.CTkButton(ftr, text="✅ Seleziona Cartella", width=170, height=38, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=14, weight="bold"), command=self._confirm)
        btn_confirm.pack(side="right", padx=(10, 20))

        btn_cancel = ctk.CTkButton(ftr, text="Annulla", width=90, height=38, fg_color="#374151", hover_color="#4b5563", font=ctk.CTkFont(size=13), command=self.destroy)
        btn_cancel.pack(side="right", padx=5)

    def _navigate(self, target_path: str):
        if not os.path.exists(target_path) or not os.path.isdir(target_path):
            return
        
        self.selected_path = os.path.abspath(target_path)
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, self.selected_path)

        # Clear existing subfolder items
        for child in self.subfolder_scroll.winfo_children():
            child.destroy()

        # Count image files in target path
        exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        photo_count = 0
        subdirs = []

        try:
            entries = sorted(os.listdir(self.selected_path))
            for item in entries:
                full = os.path.join(self.selected_path, item)
                if os.path.isdir(full) and not item.startswith('.'):
                    subdirs.append(item)
                elif os.path.isfile(full):
                    if os.path.splitext(item)[1].lower() in exts:
                        photo_count += 1
        except PermissionError:
            self.lbl_preview.configure(text="⚠️ Accesso Negato", text_color="#ef4444")
            return

        # Update preview label
        self.lbl_preview.configure(
            text=f"📁 {os.path.basename(self.selected_path) or self.selected_path}  ·  📸 {photo_count} foto trovate",
            text_color="#10b981" if photo_count > 0 else TEXT_DIM
        )

        # Display subdirectories
        if not subdirs:
            lbl = ctk.CTkLabel(self.subfolder_scroll, text="Nessuna sottocartella", font=ctk.CTkFont(size=12), text_color=TEXT_DIM)
            lbl.pack(pady=20)
        else:
            for sdir in subdirs:
                sub_path = os.path.join(self.selected_path, sdir)
                card = ctk.CTkFrame(self.subfolder_scroll, fg_color="#202030", corner_radius=6, height=36)
                card.pack(fill="x", pady=2, padx=2)
                card.pack_propagate(False)

                lbl = ctk.CTkLabel(card, text=f"📁  {sdir}", font=ctk.CTkFont(size=13), text_color=TEXT, anchor="w")
                lbl.pack(side="left", padx=12, fill="x", expand=True)

                def _click(p=sub_path):
                    self._navigate(p)

                card.bind("<Double-Button-1>", lambda e, p=sub_path: self._navigate(p))
                lbl.bind("<Double-Button-1>", lambda e, p=sub_path: self._navigate(p))
                card.bind("<Button-1>", lambda e, p=sub_path: self._navigate(p))
                lbl.bind("<Button-1>", lambda e, p=sub_path: self._navigate(p))

    def _populate_history(self):
        for child in self.history_scroll.winfo_children():
            child.destroy()

        if not self.history_paths:
            lbl = ctk.CTkLabel(self.history_scroll, text="Nessuna cronologia", font=ctk.CTkFont(size=12), text_color=TEXT_DIM)
            lbl.pack(pady=20)
            return

        for p in self.history_paths:
            if not os.path.exists(p):
                continue
            fname = os.path.basename(p) or p
            card = ctk.CTkFrame(self.history_scroll, fg_color="#222234", corner_radius=6)
            card.pack(fill="x", pady=3, padx=2)

            lbl_name = ctk.CTkLabel(card, text=fname, font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT, anchor="w")
            lbl_name.pack(anchor="w", padx=8, pady=(4, 0))

            short_p = p if len(p) < 28 else "…" + p[-25:]
            lbl_p = ctk.CTkLabel(card, text=short_p, font=ctk.CTkFont(size=10), text_color=TEXT_DIM, anchor="w")
            lbl_p.pack(anchor="w", padx=8, pady=(0, 4))

            def _sel(target=p):
                self._navigate(target)

            card.bind("<Button-1>", lambda e, t=p: self._navigate(t))
            lbl_name.bind("<Button-1>", lambda e, t=p: self._navigate(t))
            lbl_p.bind("<Button-1>", lambda e, t=p: self._navigate(t))

    def _go_up(self):
        parent = os.path.dirname(self.selected_path)
        if parent and parent != self.selected_path:
            self._navigate(parent)

    def _use_native_dialog(self):
        chosen = filedialog.askdirectory(title="Seleziona cartella foto", initialdir=self.selected_path)
        if chosen:
            self.selected_path = chosen
            self._confirm()

    def _confirm(self):
        if self.on_select_callback and self.selected_path:
            self.on_select_callback(self.selected_path)
        self.destroy()
