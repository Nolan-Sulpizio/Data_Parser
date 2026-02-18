"""
Wesco MRO Parser — v5.0
=======================
Single-panel interface. Three steps. Impossible to get wrong.

By Wesco International — Global Accounts Team
Built by Nolan Sulpizio
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import pandas as pd
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.parser_core import (
    pipeline_mfg_pn, run_qa, parse_single_row,
)
from engine.column_mapper import (
    map_columns, suggest_columns,
    score_column_for_parsing, detect_supplier_column,
)
from engine.training import load_training_data
from engine import history_db

# ═══════════════════════════════════════════════════════════════
#  THEME & BRANDING
# ═══════════════════════════════════════════════════════════════

BRAND = {
    'bg_dark':       '#0D1117',
    'bg_card':       '#161B22',
    'bg_input':      '#21262D',
    'bg_hover':      '#30363D',
    'accent':        '#009639',
    'accent_hover':  '#4CAF50',
    'accent_dim':    '#006B2D',
    'text_primary':  '#F0F6FC',
    'text_secondary':'#8B949E',
    'text_muted':    '#6E7681',
    'border':        '#30363D',
    'success':       '#009639',
    'warning':       '#D29922',
    'error':         '#F85149',
    'info':          '#60A5FA',
    'font_family':   'Segoe UI',
    'font_mono':     'Consolas',
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# ═══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════

class WescoMROParser(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Wesco MRO Parser")
        self.geometry("920x740")
        self.minsize(760, 620)
        self.configure(fg_color=BRAND['bg_dark'])

        # State
        self.current_file: str = None
        self.df_input: pd.DataFrame = None
        self.df_output: pd.DataFrame = None
        self.job_result = None
        self.is_processing = False
        self.column_mapping: dict = None
        self.training_data: dict = None

        # Column selector state (set after file load)
        self.source_col_vars: dict = {}      # {col_name: tk.BooleanVar}
        self.supplier_col: str = None        # auto-detected supplier column
        self._scored_cols: dict = {}         # {col_name: score}

        # Load training data
        training_path = os.path.join(os.path.dirname(__file__), 'training_data.json')
        self.training_data = load_training_data(training_path)

        # Build UI
        self._build_header()
        self._build_scroll_area()

    # ───────────────────────────────────────────────────────
    #  HEADER (fixed, above scroll)
    # ───────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BRAND['bg_card'], corner_radius=0, height=60)
        hdr.pack(fill='x', side='top')
        hdr.pack_propagate(False)

        inner = ctk.CTkFrame(hdr, fg_color='transparent')
        inner.place(relx=0.5, rely=0.5, anchor='center', relwidth=1.0)

        logo_loaded = False
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'wesco_logo.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                aspect = img.height / img.width
                w, h = 120, int(120 * aspect)
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                logo_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                lbl = ctk.CTkLabel(inner, image=logo_ctk, text='', fg_color='transparent')
                lbl.image = logo_ctk
                lbl.pack(side='left', padx=(24, 8))
                logo_loaded = True
        except Exception:
            pass

        if not logo_loaded:
            ctk.CTkLabel(inner, text="W",
                         font=(BRAND['font_family'], 28, 'bold'),
                         text_color=BRAND['accent']).pack(side='left', padx=(24, 4))
            ctk.CTkLabel(inner, text="WESCO",
                         font=(BRAND['font_family'], 18, 'bold'),
                         text_color=BRAND['text_primary']).pack(side='left', padx=(0, 8))

        ctk.CTkLabel(inner, text="MRO Data Parser",
                     font=(BRAND['font_family'], 12),
                     text_color=BRAND['text_muted']).pack(side='left')

        ctk.CTkLabel(inner, text="v5.0",
                     font=(BRAND['font_family'], 11),
                     text_color=BRAND['text_muted']).pack(side='right', padx=24)

    # ───────────────────────────────────────────────────────
    #  SCROLL AREA  (single vertically-scrolling content panel)
    # ───────────────────────────────────────────────────────

    def _build_scroll_area(self):
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=BRAND['bg_dark'])
        self._scroll.pack(fill='both', expand=True)

        # Center content at max 800px
        self._content = ctk.CTkFrame(self._scroll, fg_color='transparent')
        self._content.pack(fill='both', expand=True, padx=48, pady=24)

        self._build_dropzone()
        self._build_file_info()
        self._build_warnings_area()
        self._build_column_panel()
        self._build_preview_panel()
        self._build_parse_button()
        self._build_results_panel()

    # ───────────────────────────────────────────────────────
    #  STEP 1: DROP ZONE
    # ───────────────────────────────────────────────────────

    def _build_dropzone(self):
        self._dropzone = ctk.CTkFrame(
            self._content,
            fg_color=BRAND['bg_card'],
            corner_radius=12,
            border_color=BRAND['border'],
            border_width=2,
            height=140,
        )
        self._dropzone.pack(fill='x', pady=(0, 8))
        self._dropzone.pack_propagate(False)

        inner = ctk.CTkFrame(self._dropzone, fg_color='transparent')
        inner.place(relx=0.5, rely=0.5, anchor='center')

        self._drop_icon = ctk.CTkLabel(inner, text="📂",
                                        font=(BRAND['font_family'], 32),
                                        text_color=BRAND['text_secondary'])
        self._drop_icon.pack()

        self._drop_label = ctk.CTkLabel(
            inner, text="Drop an Excel file here  or  click to browse",
            font=(BRAND['font_family'], 14),
            text_color=BRAND['text_secondary'],
        )
        self._drop_label.pack(pady=(6, 0))

        self._drop_hint = ctk.CTkLabel(
            inner, text=".xlsx  ·  .xls  ·  .csv",
            font=(BRAND['font_family'], 11),
            text_color=BRAND['text_muted'],
        )
        self._drop_hint.pack(pady=(2, 0))

        # Make entire zone clickable
        for widget in (self._dropzone, inner, self._drop_icon,
                       self._drop_label, self._drop_hint):
            widget.bind('<Button-1>', lambda e: self._browse_file())

        # Hover effect
        self._dropzone.bind('<Enter>', lambda e: self._dropzone.configure(
            border_color=BRAND['accent']))
        self._dropzone.bind('<Leave>', lambda e: self._dropzone.configure(
            border_color=BRAND['border']))

        # Drag-and-drop (optional — graceful fallback if not available)
        try:
            self._dropzone.drop_target_register('DND_Files')
            self._dropzone.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            pass

    # ───────────────────────────────────────────────────────
    #  FILE INFO BAR  (shown after load)
    # ───────────────────────────────────────────────────────

    def _build_file_info(self):
        self._file_info = ctk.CTkFrame(self._content, fg_color='transparent')
        # Packed by _show_file_info() after load

        self._file_name_label = ctk.CTkLabel(
            self._file_info, text="",
            font=(BRAND['font_family'], 13, 'bold'),
            text_color=BRAND['accent'],
        )
        self._file_name_label.pack(side='left')

        self._file_meta_label = ctk.CTkLabel(
            self._file_info, text="",
            font=(BRAND['font_family'], 11),
            text_color=BRAND['text_muted'],
        )
        self._file_meta_label.pack(side='left', padx=(10, 0))

    # ───────────────────────────────────────────────────────
    #  INLINE WARNINGS  (shown after load)
    # ───────────────────────────────────────────────────────

    def _build_warnings_area(self):
        self._warnings_area = ctk.CTkFrame(self._content, fg_color='transparent')
        # Packed by _show_warnings() after load

    # ───────────────────────────────────────────────────────
    #  STEP 2A: SOURCE COLUMN PANEL  (shown after load)
    # ───────────────────────────────────────────────────────

    def _build_column_panel(self):
        self._col_panel = ctk.CTkFrame(
            self._content, fg_color=BRAND['bg_card'], corner_radius=12,
        )
        # Packed by _show_column_panel()

        # Header
        hdr = ctk.CTkFrame(self._col_panel, fg_color='transparent')
        hdr.pack(fill='x', padx=16, pady=(14, 6))
        ctk.CTkLabel(hdr, text="SOURCE DATA",
                     font=(BRAND['font_family'], 12, 'bold'),
                     text_color=BRAND['text_primary']).pack(side='left')
        ctk.CTkLabel(hdr, text="— where MFG/PN info lives",
                     font=(BRAND['font_family'], 11),
                     text_color=BRAND['text_muted']).pack(side='left', padx=(8, 0))

        # Checkbox list (rebuilt on each file load)
        self._col_list_frame = ctk.CTkFrame(self._col_panel, fg_color='transparent')
        self._col_list_frame.pack(fill='x', padx=12, pady=(0, 4))

        ctk.CTkLabel(self._col_panel,
                     text="Only columns likely to contain product data are shown.  "
                          "Irrelevant columns (Plant, Date, Qty) are hidden.",
                     font=(BRAND['font_family'], 10),
                     text_color=BRAND['text_muted'],
                     wraplength=700, justify='left').pack(anchor='w', padx=16, pady=(0, 4))

        # Supplier hint
        sep = ctk.CTkFrame(self._col_panel, fg_color=BRAND['border'], height=1)
        sep.pack(fill='x', padx=16, pady=(4, 8))

        self._sup_frame = ctk.CTkFrame(self._col_panel, fg_color='transparent')
        self._sup_frame.pack(fill='x', padx=16, pady=(0, 14))

        ctk.CTkLabel(self._sup_frame, text="SUPPLIER HINT",
                     font=(BRAND['font_family'], 11, 'bold'),
                     text_color=BRAND['text_secondary']).pack(side='left')

        ctk.CTkLabel(self._sup_frame, text="— helps identify MFG",
                     font=(BRAND['font_family'], 10),
                     text_color=BRAND['text_muted']).pack(side='left', padx=(6, 16))

        self._sup_label = ctk.CTkLabel(self._sup_frame, text="",
                                        font=(BRAND['font_mono'], 11),
                                        text_color=BRAND['accent'])
        self._sup_label.pack(side='left')

    def _populate_column_panel(self):
        """Rebuild checkbox list based on scored columns."""
        for w in self._col_list_frame.winfo_children():
            w.destroy()
        self.source_col_vars = {}

        cols = list(self.df_input.columns)
        visible_cols = [
            (col, self._scored_cols.get(col, 0))
            for col in cols
            if self._scored_cols.get(col, 0) >= 10
        ]

        if not visible_cols:
            # Fallback: show all columns if scoring returned nothing
            visible_cols = [(col, 0) for col in cols]

        for col, score in visible_cols:
            idx = cols.index(col)
            letter = chr(ord('A') + idx) if idx < 26 else f"Col{idx + 1}"
            auto_check = score >= 40

            row = ctk.CTkFrame(self._col_list_frame, fg_color='transparent')
            row.pack(fill='x', pady=2)

            var = tk.BooleanVar(value=auto_check)
            self.source_col_vars[col] = var

            # Build display name — for Unnamed columns show sample value
            display_name = col
            if 'unnamed' in col.lower():
                sample_vals = self.df_input[col].dropna().head(2).astype(str).tolist()
                if sample_vals:
                    preview_val = sample_vals[0][:40]
                    display_name = f"{col}  (e.g. '{preview_val}')"

            cb = ctk.CTkCheckBox(
                row,
                text=f"{letter}:  {display_name}",
                variable=var,
                font=(BRAND['font_family'], 12),
                text_color=BRAND['accent'] if auto_check else BRAND['text_primary'],
                fg_color=BRAND['accent'],
                hover_color=BRAND['accent_hover'],
                command=self._on_column_changed,
            )
            cb.pack(side='left', padx=4)

            if auto_check:
                ctk.CTkLabel(row, text="← auto-selected",
                             font=(BRAND['font_mono'], 9),
                             text_color=BRAND['accent_dim']).pack(side='right', padx=8)

        # Supplier hint
        if self.supplier_col:
            self._sup_label.configure(
                text=f"Auto-detected: {self.supplier_col}  ✓"
            )
        else:
            self._sup_label.configure(text="None detected")

    # ───────────────────────────────────────────────────────
    #  STEP 2B: SMART PREVIEW PANEL  (shown after load)
    # ───────────────────────────────────────────────────────

    def _build_preview_panel(self):
        self._preview_panel = ctk.CTkFrame(
            self._content, fg_color=BRAND['bg_card'], corner_radius=12,
        )
        # Packed by _show_column_panel()

        hdr = ctk.CTkFrame(self._preview_panel, fg_color='transparent')
        hdr.pack(fill='x', padx=16, pady=(14, 8))
        ctk.CTkLabel(hdr, text="PREVIEW",
                     font=(BRAND['font_family'], 12, 'bold'),
                     text_color=BRAND['text_primary']).pack(side='left')
        ctk.CTkLabel(hdr, text="— sample of what the engine will extract",
                     font=(BRAND['font_family'], 11),
                     text_color=BRAND['text_muted']).pack(side='left', padx=(8, 0))

        self._preview_rows_frame = ctk.CTkFrame(self._preview_panel, fg_color='transparent')
        self._preview_rows_frame.pack(fill='x', padx=12, pady=(0, 14))

    def _refresh_preview(self):
        """Parse 3-5 sample rows and update the preview panel."""
        for w in self._preview_rows_frame.winfo_children():
            w.destroy()

        if self.df_input is None:
            return

        selected_cols = [c for c, v in self.source_col_vars.items() if v.get()]
        if not selected_cols:
            ctk.CTkLabel(self._preview_rows_frame,
                         text="Select at least one source column above to see a preview.",
                         font=(BRAND['font_family'], 11),
                         text_color=BRAND['text_muted']).pack(padx=8, pady=8)
            return

        sample_indices = self._pick_diverse_samples(5)

        for idx in sample_indices:
            row_data = self.df_input.iloc[idx]
            source_text = '  |  '.join(
                str(row_data[c]) for c in selected_cols
                if c in self.df_input.columns and pd.notna(row_data[c])
            )
            supplier_hint = (
                str(row_data[self.supplier_col])
                if self.supplier_col and self.supplier_col in self.df_input.columns
                   and pd.notna(row_data[self.supplier_col])
                else None
            )

            mfg, pn = parse_single_row(source_text, supplier_hint)

            confidence = 'high' if (mfg and pn) else ('partial' if (mfg or pn) else 'none')
            color_map = {
                'high':    BRAND['success'],
                'partial': BRAND['warning'],
                'none':    BRAND['text_muted'],
            }
            color = color_map[confidence]

            card = ctk.CTkFrame(self._preview_rows_frame,
                                fg_color=BRAND['bg_input'], corner_radius=8)
            card.pack(fill='x', padx=4, pady=3)

            inner = ctk.CTkFrame(card, fg_color='transparent')
            inner.pack(fill='x', padx=12, pady=8)

            # Source text (truncated)
            src_display = source_text[:90] + ('…' if len(source_text) > 90 else '')
            ctk.CTkLabel(inner, text=f"Row {idx + 1}:  {src_display}",
                         font=(BRAND['font_family'], 10),
                         text_color=BRAND['text_secondary'],
                         anchor='w', justify='left').pack(fill='x')

            result_line = ctk.CTkFrame(inner, fg_color='transparent')
            result_line.pack(fill='x', pady=(4, 0))

            ctk.CTkLabel(result_line,
                         text=f"MFG: {mfg or '—'}",
                         font=(BRAND['font_mono'], 11, 'bold'),
                         text_color=color).pack(side='left')
            ctk.CTkLabel(result_line,
                         text=f"   PN: {pn or '—'}",
                         font=(BRAND['font_mono'], 11),
                         text_color=color).pack(side='left')

    def _pick_diverse_samples(self, n: int) -> list:
        """Return up to n row indices spread across the dataframe."""
        total = len(self.df_input)
        if total <= n:
            return list(range(total))
        step = total // n
        return [min(i * step, total - 1) for i in range(n)]

    # ───────────────────────────────────────────────────────
    #  STEP 3: PARSE BUTTON  (shown after load)
    # ───────────────────────────────────────────────────────

    def _build_parse_button(self):
        self._parse_btn_frame = ctk.CTkFrame(self._content, fg_color='transparent')
        # Packed by _show_parse_button()

        self._parse_btn = ctk.CTkButton(
            self._parse_btn_frame,
            text="▶  PARSE FILE",
            height=52,
            font=(BRAND['font_family'], 16, 'bold'),
            fg_color=BRAND['accent'],
            hover_color=BRAND['accent_hover'],
            text_color='#FFFFFF',
            corner_radius=10,
            command=self._on_parse_clicked,
        )
        self._parse_btn.pack(fill='x')

        self._progress_bar = ctk.CTkProgressBar(
            self._parse_btn_frame,
            fg_color=BRAND['bg_card'],
            progress_color=BRAND['accent'],
            height=4, corner_radius=2,
        )
        self._progress_bar.pack(fill='x', pady=(6, 0))
        self._progress_bar.set(0)

        self._parse_status = ctk.CTkLabel(
            self._parse_btn_frame, text="",
            font=(BRAND['font_family'], 11),
            text_color=BRAND['text_muted'],
        )
        self._parse_status.pack(pady=(4, 0))

    # ───────────────────────────────────────────────────────
    #  RESULTS PANEL  (shown after parse)
    # ───────────────────────────────────────────────────────

    def _build_results_panel(self):
        self._results_panel = ctk.CTkFrame(
            self._content, fg_color=BRAND['bg_card'], corner_radius=12,
        )
        # Packed by _show_results()

        # Metrics row
        self._metrics_frame = ctk.CTkFrame(self._results_panel, fg_color='transparent')
        self._metrics_frame.pack(fill='x', padx=16, pady=(16, 8))

        # File paths
        self._paths_frame = ctk.CTkFrame(self._results_panel, fg_color=BRAND['bg_input'],
                                          corner_radius=8)
        self._paths_frame.pack(fill='x', padx=16, pady=(0, 12))

        # Action buttons
        btn_row = ctk.CTkFrame(self._results_panel, fg_color='transparent')
        btn_row.pack(fill='x', padx=16, pady=(0, 16))

        self._open_loc_btn = ctk.CTkButton(
            btn_row, text="Open File Location",
            height=38, width=180,
            font=(BRAND['font_family'], 13),
            fg_color=BRAND['bg_input'],
            hover_color=BRAND['bg_hover'],
            text_color=BRAND['text_primary'],
            corner_radius=8,
            border_color=BRAND['border'], border_width=1,
            command=self._open_file_location,
        )
        self._open_loc_btn.pack(side='left')

        self._another_btn = ctk.CTkButton(
            btn_row, text="Parse Another File",
            height=38, width=180,
            font=(BRAND['font_family'], 13),
            fg_color=BRAND['accent_dim'],
            hover_color=BRAND['accent'],
            text_color=BRAND['text_primary'],
            corner_radius=8,
            command=self._reset,
        )
        self._another_btn.pack(side='left', padx=(12, 0))

        self._exported_path: str = None

    # ═══════════════════════════════════════════════════════
    #  FILE HANDLING
    # ═══════════════════════════════════════════════════════

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Excel or CSV File",
            filetypes=[("Excel / CSV", "*.xlsx *.xls *.csv"), ("All files", "*.*")],
        )
        if path:
            self._load_file(path)

    def _on_drop(self, event):
        path = event.data.strip('{}')
        if path.lower().endswith(('.xlsx', '.xls', '.csv')):
            self._load_file(path)

    def _load_file(self, path: str):
        try:
            self._drop_label.configure(text="Loading…", text_color=BRAND['text_muted'])
            self.update_idletasks()

            if path.lower().endswith('.csv'):
                self.df_input = pd.read_csv(path)
            else:
                self.df_input = pd.read_excel(path, engine='openpyxl')

            self.df_input.columns = [str(c).strip() for c in self.df_input.columns]
            self.current_file = path

            # Score columns and detect supplier
            self._scored_cols = {
                col: score_column_for_parsing(col, self.df_input[col].tolist())
                for col in self.df_input.columns
            }
            self.supplier_col = detect_supplier_column(list(self.df_input.columns))
            self.column_mapping = map_columns(self.df_input, self.training_data)

            self._on_file_loaded(path)

        except Exception as e:
            self._drop_label.configure(
                text=f"Error loading file: {e}",
                text_color=BRAND['error'],
            )

    def _on_file_loaded(self, path: str):
        filename = os.path.basename(path)
        n_rows = len(self.df_input)
        n_cols = len(self.df_input.columns)

        # Shrink dropzone and update label
        self._dropzone.configure(height=60, border_color=BRAND['accent'], border_width=1)
        self._drop_icon.configure(text="✓", font=(BRAND['font_family'], 16),
                                   text_color=BRAND['accent'])
        self._drop_label.configure(
            text=f"{filename}",
            font=(BRAND['font_family'], 13, 'bold'),
            text_color=BRAND['accent'],
        )
        self._drop_hint.configure(
            text=f"{n_rows:,} rows  ·  {n_cols} columns  ·  click to change file",
        )

        # File info bar
        self._file_name_label.configure(text=f"✓  {filename}")
        self._file_meta_label.configure(text=f"{n_rows:,} rows  ·  {n_cols} columns")
        self._file_info.pack(fill='x', pady=(0, 4))

        # Inline warnings
        self._build_inline_warnings()

        # Column panel + preview
        self._populate_column_panel()
        self._col_panel.pack(fill='x', pady=(8, 0))
        self._preview_panel.pack(fill='x', pady=(8, 0))
        self._parse_btn_frame.pack(fill='x', pady=(12, 0))

        # Refresh preview in background to keep UI snappy
        self.after(50, self._refresh_preview)

    def _build_inline_warnings(self):
        """Show inline warnings about file quality issues (replaces buried Data Prep Tips)."""
        for w in self._warnings_area.winfo_children():
            w.destroy()

        warnings = []

        unnamed_count = sum(1 for c in self.df_input.columns if 'unnamed' in c.lower())
        if unnamed_count > 0:
            warnings.append(
                f"⚠  {unnamed_count} column(s) have no headers. "
                "The engine will use row content to identify data."
            )

        empty_rows = self.df_input.isnull().all(axis=1).sum()
        if empty_rows > 0:
            warnings.append(f"⚠  {empty_rows} completely empty rows — these will produce blank output.")

        high_score_cols = [c for c, s in self._scored_cols.items() if s >= 40]
        if not high_score_cols:
            warnings.append(
                "⚠  No obvious description column detected. "
                "Review the column list below and check the right column manually."
            )

        for msg in warnings:
            ctk.CTkLabel(self._warnings_area, text=msg,
                         font=(BRAND['font_family'], 10),
                         text_color=BRAND['warning'],
                         anchor='w', justify='left').pack(anchor='w', pady=2)

        if warnings:
            self._warnings_area.pack(fill='x', pady=(0, 4))

    # ═══════════════════════════════════════════════════════
    #  COLUMN CHANGE → REFRESH PREVIEW
    # ═══════════════════════════════════════════════════════

    def _on_column_changed(self):
        self.after(80, self._refresh_preview)

    # ═══════════════════════════════════════════════════════
    #  PARSING
    # ═══════════════════════════════════════════════════════

    def _on_parse_clicked(self):
        if self.df_input is None or self.is_processing:
            return

        selected_cols = [c for c, v in self.source_col_vars.items() if v.get()]
        if not selected_cols:
            self._parse_status.configure(
                text="Select at least one source column above.",
                text_color=BRAND['error'],
            )
            return

        self.is_processing = True
        self._parse_btn.configure(state='disabled', text="⏳  Parsing…")
        self._progress_bar.set(0)
        self._parse_status.configure(text="Running extraction pipeline…",
                                      text_color=BRAND['text_muted'])
        self.title(f"Wesco MRO Parser — {os.path.basename(self.current_file)}")

        threading.Thread(target=self._execute_pipeline,
                         args=(selected_cols,), daemon=True).start()

    def _execute_pipeline(self, source_cols: list):
        try:
            self.after(0, lambda: self._progress_bar.set(0.25))

            result = pipeline_mfg_pn(
                self.df_input,
                source_cols=source_cols,
                supplier_col=self.supplier_col,
                column_mapping=self.column_mapping,
                add_sim=False,
            )

            self.after(0, lambda: self._progress_bar.set(0.75))

            issues = run_qa(result.df, mfg_col='MFG')
            result.issues = issues

            self.after(0, lambda: self._progress_bar.set(0.90))

            # Save to history
            history_db.save_job(
                filename=os.path.basename(self.current_file or 'unknown'),
                instruction='', pipeline='mfg_pn',
                source_columns=source_cols,
                target_mfg='MFG', target_pn='PN',
                add_sim=False, sim_pattern='',
                total_rows=result.total_rows,
                mfg_filled=result.mfg_filled,
                pn_filled=result.pn_filled,
                sim_filled=result.sim_filled,
                issues_count=len(issues),
                output_path='',
            )

            self.df_output = result.df
            self.job_result = result

            self.after(0, lambda: self._on_parse_complete(result, issues))

        except Exception as e:
            self.after(0, lambda: self._on_parse_error(str(e)))

    def _on_parse_complete(self, result, issues):
        self._progress_bar.set(1.0)
        self.is_processing = False
        self._parse_btn.configure(state='normal', text="▶  PARSE FILE")

        # Auto-export
        exported_main, exported_qa = self._auto_export(result, issues)
        self._exported_path = exported_main

        self._parse_status.configure(
            text=f"✓ Complete — file saved to {os.path.dirname(exported_main) if exported_main else 'unknown'}",
            text_color=BRAND['success'],
        )

        self._show_results(result, issues, exported_main, exported_qa)

    def _on_parse_error(self, error_msg: str):
        self._progress_bar.set(0)
        self.is_processing = False
        self._parse_btn.configure(state='normal', text="▶  PARSE FILE")
        self._parse_status.configure(
            text=f"✗  Error: {error_msg}",
            text_color=BRAND['error'],
        )

    # ═══════════════════════════════════════════════════════
    #  AUTO-EXPORT
    # ═══════════════════════════════════════════════════════

    def _auto_export(self, result, issues) -> tuple:
        """Save parsed output to the same directory as the source file.

        Returns (main_path, qa_path) — qa_path may be None.
        """
        if not self.current_file or result is None:
            return None, None

        src_dir = os.path.dirname(self.current_file)
        base = os.path.splitext(os.path.basename(self.current_file))[0]

        main_path = os.path.join(src_dir, f"{base}_parsed.csv")
        qa_path = None

        try:
            result.df.to_csv(main_path, index=False, encoding='utf-8-sig')
        except Exception as e:
            print(f"Auto-export error: {e}")
            return None, None

        if issues:
            try:
                qa_path = os.path.join(src_dir, f"{base}_QA.csv")
                import pandas as pd
                pd.DataFrame(issues).to_csv(qa_path, index=False, encoding='utf-8-sig')
            except Exception:
                qa_path = None

        return main_path, qa_path

    # ═══════════════════════════════════════════════════════
    #  RESULTS PANEL
    # ═══════════════════════════════════════════════════════

    def _show_results(self, result, issues, main_path, qa_path):
        # Clear old metrics/paths
        for w in self._metrics_frame.winfo_children():
            w.destroy()
        for w in self._paths_frame.winfo_children():
            w.destroy()

        # ── Completion badge ──
        ctk.CTkLabel(self._metrics_frame, text="✅  COMPLETE",
                     font=(BRAND['font_family'], 16, 'bold'),
                     text_color=BRAND['success']).pack(anchor='w')

        # ── Stats ──
        stats = [
            f"{result.total_rows:,} rows processed",
            f"MFG filled: {result.mfg_filled:,} ({result.mfg_filled / max(result.total_rows, 1):.0%})",
            f"PN filled:  {result.pn_filled:,} ({result.pn_filled / max(result.total_rows, 1):.0%})",
        ]
        if issues:
            stats.append(f"Issues flagged: {len(issues):,}")

        for stat in stats:
            ctk.CTkLabel(self._metrics_frame, text=stat,
                         font=(BRAND['font_family'], 12),
                         text_color=BRAND['text_primary']).pack(anchor='w', pady=1)

        # ── File paths ──
        paths_inner = ctk.CTkFrame(self._paths_frame, fg_color='transparent')
        paths_inner.pack(fill='x', padx=12, pady=10)

        if main_path:
            ctk.CTkLabel(paths_inner,
                         text=f"📄  {os.path.basename(main_path)}",
                         font=(BRAND['font_mono'], 11),
                         text_color=BRAND['accent']).pack(anchor='w')
            ctk.CTkLabel(paths_inner,
                         text=f"   {main_path}",
                         font=(BRAND['font_mono'], 9),
                         text_color=BRAND['text_muted']).pack(anchor='w')

        if qa_path:
            ctk.CTkLabel(paths_inner,
                         text=f"📊  {os.path.basename(qa_path)}",
                         font=(BRAND['font_mono'], 11),
                         text_color=BRAND['warning']).pack(anchor='w', pady=(6, 0))
            ctk.CTkLabel(paths_inner,
                         text=f"   {qa_path}",
                         font=(BRAND['font_mono'], 9),
                         text_color=BRAND['text_muted']).pack(anchor='w')

        if main_path is None:
            ctk.CTkLabel(paths_inner,
                         text="⚠  Auto-save failed. Use your file manager to save manually.",
                         font=(BRAND['font_family'], 11),
                         text_color=BRAND['warning']).pack(anchor='w')

        self._results_panel.pack(fill='x', pady=(12, 0))

    # ═══════════════════════════════════════════════════════
    #  POST-RESULTS ACTIONS
    # ═══════════════════════════════════════════════════════

    def _open_file_location(self):
        path = self._exported_path
        if not path:
            return
        folder = os.path.dirname(path)
        if sys.platform == 'darwin':
            os.system(f'open "{folder}"')
        elif sys.platform == 'win32':
            os.startfile(folder)
        else:
            os.system(f'xdg-open "{folder}"')

    def _reset(self):
        """Reset to Step 1 so the user can parse another file."""
        self.current_file = None
        self.df_input = None
        self.df_output = None
        self.job_result = None
        self.is_processing = False
        self.source_col_vars = {}
        self.supplier_col = None
        self._scored_cols = {}
        self._exported_path = None

        # Reset dropzone
        self._dropzone.configure(height=140, border_color=BRAND['border'], border_width=2)
        self._drop_icon.configure(text="📂", font=(BRAND['font_family'], 32),
                                   text_color=BRAND['text_secondary'])
        self._drop_label.configure(
            text="Drop an Excel file here  or  click to browse",
            font=(BRAND['font_family'], 14),
            text_color=BRAND['text_secondary'],
        )
        self._drop_hint.configure(text=".xlsx  ·  .xls  ·  .csv")

        # Hide panels
        self._file_info.pack_forget()
        self._warnings_area.pack_forget()
        self._col_panel.pack_forget()
        self._preview_panel.pack_forget()
        self._parse_btn_frame.pack_forget()
        self._results_panel.pack_forget()

        # Reset parse button
        self._parse_btn.configure(state='normal', text="▶  PARSE FILE")
        self._progress_bar.set(0)
        self._parse_status.configure(text="")

        self.title("Wesco MRO Parser")


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    app = WescoMROParser()
    app.mainloop()


if __name__ == '__main__':
    main()
