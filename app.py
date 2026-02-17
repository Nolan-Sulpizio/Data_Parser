"""
Wesco MRO Parser — Agentic MRO Data Parsing Tool
=================================================
A standalone desktop application for parsing MRO Excel data.
100% offline, no API keys required.

By Wesco International — Global Accounts Team
Built by Nolan Sulpizio
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pandas as pd
import os
import sys
import json
import threading
from datetime import datetime

# Add engine to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.parser_core import (
    pipeline_mfg_pn, pipeline_part_number, pipeline_sim_builder, run_qa
)
from engine.instruction_parser import parse_instruction, auto_detect_pipeline
from engine.column_mapper import map_columns, format_mapping_summary, suggest_columns
from engine.training import load_training_data, ingest_training_files
from engine import history_db

# ═══════════════════════════════════════════════════════════════
#  THEME & BRANDING
# ═══════════════════════════════════════════════════════════════

BRAND = {
    'bg_dark': '#0D1117',
    'bg_card': '#161B22',
    'bg_input': '#21262D',
    'bg_hover': '#30363D',
    'accent': '#009639',        # Wesco primary green
    'accent_hover': '#4CAF50',
    'accent_dim': '#006B2D',
    'text_primary': '#F0F6FC',
    'text_secondary': '#8B949E',
    'text_muted': '#6E7681',
    'border': '#30363D',
    'success': '#009639',
    'warning': '#D29922',
    'error': '#F85149',
    'info': '#60A5FA',
    'font_family': 'Segoe UI',
    'font_mono': 'Consolas',
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
        self.geometry("1280x820")
        self.minsize(1000, 700)
        self.configure(fg_color=BRAND['bg_dark'])

        # State
        self.current_file: str = None
        self.df_input: pd.DataFrame = None
        self.df_output: pd.DataFrame = None
        self.job_result = None
        self.is_processing = False
        self.column_mapping: dict = None
        self.training_data: dict = None

        # Column-first selector state
        self.col_selector_vars: dict = {}       # {col_name: tk.BooleanVar}
        self.output_position_var: tk.StringVar = None
        self.supplier_col_var: tk.StringVar = None
        self._col_suggestions: dict = {}
        self._advanced_visible: bool = False

        # Load training data at startup
        training_path = os.path.join(os.path.dirname(__file__), 'training_data.json')
        self.training_data = load_training_data(training_path)

        # Layout: Sidebar + Main content
        self._build_sidebar()
        self._build_main_area()

    # ───────────────────────────────────────────────────────
    #  SIDEBAR
    # ───────────────────────────────────────────────────────

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=260, fg_color=BRAND['bg_card'],
                                     corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Logo area - pack FIRST for visibility
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        logo_frame.pack(fill='x', padx=20, pady=(24, 16))

        # Try to load the Wesco logo image
        logo_loaded = False
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'wesco_logo.png')
            if os.path.exists(logo_path):
                # Load and resize the logo
                logo_img = Image.open(logo_path)
                # Make it larger for better visibility
                aspect_ratio = logo_img.height / logo_img.width
                new_width = 200
                new_height = int(new_width * aspect_ratio)
                logo_img = logo_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Convert to CTkImage
                logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img,
                                       size=(new_width, new_height))
                logo_label = ctk.CTkLabel(logo_frame, image=logo_ctk, text="", fg_color='transparent')
                logo_label.image = logo_ctk  # Keep a reference
                logo_label.pack(pady=(0, 8))
                logo_loaded = True
        except Exception as e:
            print(f"Logo load error: {e}")
            logo_loaded = False

        # Always show text fallback if image didn't load
        if not logo_loaded:
            text_frame = ctk.CTkFrame(logo_frame, fg_color='transparent')
            text_frame.pack()

            logo_icon = ctk.CTkLabel(text_frame, text="W",
                                      font=(BRAND['font_family'], 36, 'bold'),
                                      text_color=BRAND['accent'])
            logo_icon.pack(side='left', padx=(0, 4))

            logo_text = ctk.CTkLabel(text_frame, text="WESCO",
                                      font=(BRAND['font_family'], 20, 'bold'),
                                      text_color=BRAND['text_primary'])
            logo_text.pack(side='left')

        subtitle = ctk.CTkLabel(self.sidebar, text="MRO Data Parser",
                                 font=(BRAND['font_family'], 12),
                                 text_color=BRAND['text_muted'])
        subtitle.pack(padx=20, pady=(0, 20))

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BRAND['border']).pack(fill='x', padx=16)

        # Navigation buttons
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        nav_frame.pack(fill='x', padx=12, pady=16)

        self.nav_buttons = {}
        nav_items = [
            ('parser', '⬡  Parser', self._show_parser),
            ('history', '◷  History', self._show_history),
            ('configs', '⚙  Saved Configs', self._show_configs),
        ]

        for key, label, cmd in nav_items:
            btn = ctk.CTkButton(
                nav_frame, text=label, anchor='w',
                font=(BRAND['font_family'], 13),
                fg_color='transparent',
                hover_color=BRAND['bg_hover'],
                text_color=BRAND['text_secondary'],
                height=40, corner_radius=8,
                command=cmd,
            )
            btn.pack(fill='x', pady=2)
            self.nav_buttons[key] = btn

        # Quick templates section
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BRAND['border']).pack(fill='x', padx=16, pady=(8, 0))

        templates_label = ctk.CTkLabel(self.sidebar, text="QUICK TEMPLATES",
                                        font=(BRAND['font_family'], 10, 'bold'),
                                        text_color=BRAND['text_muted'])
        templates_label.pack(anchor='w', padx=20, pady=(16, 8))

        # Template buttons live in a dedicated frame so they can be rebuilt dynamically
        self.templates_frame = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self.templates_frame.pack(fill='x')

        self._default_templates = [
            ("MFG + PN Extract", "Extract MFG and PN from Material Description and PO Text into MFG and PN columns"),
            ("Part Number Clean", "Clean and validate Part Number 1 from description fields"),
            ("Build SIM Values", "Generate SIM from MFG and ITEM # for rows with missing SIM"),
        ]
        self._render_template_buttons(self._default_templates)

        # How to Use section (expandable)
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BRAND['border']).pack(fill='x', padx=16, pady=(12, 0))

        self.help_expanded = False
        self.help_toggle_btn = ctk.CTkButton(
            self.sidebar, text="📖  How to Use  ▼", anchor='w',
            font=(BRAND['font_family'], 11, 'bold'),
            fg_color='transparent',
            hover_color=BRAND['bg_hover'],
            text_color=BRAND['text_secondary'],
            height=36, corner_radius=6,
            command=self._toggle_help_panel,
        )
        self.help_toggle_btn.pack(fill='x', padx=16, pady=(12, 4))

        # Help content — packed immediately after toggle btn (hidden via pack_forget)
        self.help_panel = ctk.CTkFrame(self.sidebar, fg_color=BRAND['bg_input'], corner_radius=8)
        self.help_sections = {
            "1️⃣  Import Your File": [
                "Click the import zone or drag an Excel file in.",
                "Supports .xlsx, .xls, and .csv formats.",
            ],
            "2️⃣  Select Source Columns": [
                "Check the columns that contain the text to parse.",
                "Look for columns with descriptions or part info.",
                "⭐ columns are auto-suggested — verify them.",
                "Char counts on the right help identify text vs IDs.",
            ],
            "3️⃣  Choose Output Placement": [
                "'At end' appends MFG + PN as new last columns.",
                "'At front' inserts them as columns A–B.",
            ],
            "4️⃣  Run & Export": [
                "Hit Run Parser — results appear in the preview.",
                "Toggle Input/Output to compare before and after.",
                "Export saves as CSV (opens directly in Excel).",
            ],
        }
        # Don't pack help_panel yet — toggle will show it

        # Spacer to push version footer to bottom
        self._sidebar_spacer = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self._sidebar_spacer.pack(fill='both', expand=True)

        # Version footer
        version_label = ctk.CTkLabel(self.sidebar, text="v4.0.0  •  Wesco International  •  Global Accounts",
                                      font=(BRAND['font_family'], 9),
                                      text_color=BRAND['text_muted'])
        version_label.pack(side='bottom', pady=12)

    def _select_nav(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=BRAND['bg_hover'], text_color=BRAND['accent'])
            else:
                btn.configure(fg_color='transparent', text_color=BRAND['text_secondary'])

    def _toggle_help_panel(self):
        """Toggle the expandable help panel in sidebar."""
        self.help_expanded = not self.help_expanded

        if self.help_expanded:
            self.help_toggle_btn.configure(text="📖  How to Use  ▲")

            # Clear existing content
            for widget in self.help_panel.winfo_children():
                widget.destroy()

            # Create a scrollable frame for the help content
            help_scroll = ctk.CTkScrollableFrame(
                self.help_panel,
                fg_color='transparent',
                height=300
            )
            help_scroll.pack(fill='both', expand=True, padx=8, pady=8)

            # Add help sections
            for section_title, tips in self.help_sections.items():
                section_label = ctk.CTkLabel(
                    help_scroll, text=section_title,
                    font=(BRAND['font_family'], 11, 'bold'),
                    text_color=BRAND['accent'],
                    anchor='w',
                    justify='left'
                )
                section_label.pack(anchor='w', padx=8, pady=(8, 4), fill='x')

                for tip in tips:
                    tip_label = ctk.CTkLabel(
                        help_scroll, text=tip,
                        font=(BRAND['font_family'], 10),
                        text_color=BRAND['text_secondary'],
                        anchor='w',
                        justify='left',
                        wraplength=200
                    )
                    tip_label.pack(anchor='w', padx=8, pady=2, fill='x')

            # Pack immediately after the toggle button (not at end of sidebar)
            self.help_panel.pack(after=self.help_toggle_btn, fill='both', padx=16, pady=(4, 8))
        else:
            self.help_toggle_btn.configure(text="📖  How to Use  ▼")
            self.help_panel.pack_forget()

    # ───────────────────────────────────────────────────────
    #  MAIN CONTENT AREA
    # ───────────────────────────────────────────────────────

    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=BRAND['bg_dark'], corner_radius=0)
        self.main_frame.pack(side='right', fill='both', expand=True)

        # Container for swappable views
        self.view_container = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        self.view_container.pack(fill='both', expand=True, padx=24, pady=20)

        # Build all views
        self.views = {}
        self._build_parser_view()
        self._build_history_view()
        self._build_configs_view()

        # Show parser by default
        self._show_parser()

    def _clear_view(self):
        for view in self.views.values():
            view.pack_forget()

    # ───────────────────────────────────────────────────────
    #  PARSER VIEW (main view)
    # ───────────────────────────────────────────────────────

    def _build_parser_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color='transparent')
        self.views['parser'] = view

        # ── Header ──
        header = ctk.CTkFrame(view, fg_color='transparent')
        header.pack(fill='x', pady=(0, 16))

        ctk.CTkLabel(header, text="Parse & Extract",
                      font=(BRAND['font_family'], 24, 'bold'),
                      text_color=BRAND['text_primary']).pack(side='left')

        # ── Import zone ──
        self.import_frame = ctk.CTkFrame(view, fg_color=BRAND['bg_card'],
                                          corner_radius=12, height=120,
                                          border_color=BRAND['border'], border_width=2)
        self.import_frame.pack(fill='x', pady=(0, 12))
        self.import_frame.pack_propagate(False)

        import_inner = ctk.CTkFrame(self.import_frame, fg_color='transparent')
        import_inner.place(relx=0.5, rely=0.5, anchor='center')

        self.import_icon = ctk.CTkLabel(import_inner, text="📂",
                                         font=(BRAND['font_family'], 28))
        self.import_icon.pack()

        self.import_label = ctk.CTkLabel(import_inner,
                                          text="Drop an Excel file here or click to browse",
                                          font=(BRAND['font_family'], 13),
                                          text_color=BRAND['text_secondary'])
        self.import_label.pack(pady=(4, 0))

        self.file_info_label = ctk.CTkLabel(import_inner, text="",
                                             font=(BRAND['font_family'], 11),
                                             text_color=BRAND['accent'])
        self.file_info_label.pack(pady=(2, 0))

        # Make the whole import frame clickable
        self.import_frame.bind('<Button-1>', lambda e: self._browse_file())
        import_inner.bind('<Button-1>', lambda e: self._browse_file())
        self.import_icon.bind('<Button-1>', lambda e: self._browse_file())
        self.import_label.bind('<Button-1>', lambda e: self._browse_file())

        # Enable drag-and-drop (works on Windows with tkinterdnd2 if available)
        try:
            self.import_frame.drop_target_register('DND_Files')
            self.import_frame.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            pass  # DnD not available, click-to-browse still works

        # ── Data prep tips (shows after file load) ──
        self.data_tips_frame = ctk.CTkFrame(view, fg_color=BRAND['bg_card'],
                                             corner_radius=12, height=90)
        # Initially hidden - will be shown after file load

        # ── Column Selector (shown after file load, packed via _refresh_column_selector) ──
        self.col_selector_frame = ctk.CTkFrame(view, fg_color=BRAND['bg_card'], corner_radius=12)
        # Not packed yet — populated and packed by _refresh_column_selector() after file load

        # ── Action buttons — PACKED BEFORE optional sections so they're always visible ──
        action_frame = ctk.CTkFrame(view, fg_color='transparent')
        action_frame.pack(fill='x', pady=(0, 8))

        self.run_btn = ctk.CTkButton(
            action_frame, text="▶  Run Parser", height=42, width=180,
            font=(BRAND['font_family'], 14, 'bold'),
            fg_color=BRAND['accent'], hover_color=BRAND['accent_hover'],
            text_color=BRAND['bg_dark'], corner_radius=10,
            command=self._run_parser,
        )
        self.run_btn.pack(side='left')

        self.export_btn = ctk.CTkButton(
            action_frame, text="💾  Export", height=42, width=140,
            font=(BRAND['font_family'], 13),
            fg_color=BRAND['bg_card'], hover_color=BRAND['bg_hover'],
            text_color=BRAND['text_primary'], corner_radius=10,
            border_color=BRAND['border'], border_width=1,
            command=self._export_result, state='disabled',
        )
        self.export_btn.pack(side='left', padx=(12, 0))

        self.save_config_btn = ctk.CTkButton(
            action_frame, text="⚙ Save Config", height=42, width=140,
            font=(BRAND['font_family'], 13),
            fg_color=BRAND['bg_card'], hover_color=BRAND['bg_hover'],
            text_color=BRAND['text_primary'], corner_radius=10,
            border_color=BRAND['border'], border_width=1,
            command=self._save_current_config, state='disabled',
        )
        self.save_config_btn.pack(side='left', padx=(12, 0))

        # ── Progress ──
        self.progress_bar = ctk.CTkProgressBar(view, fg_color=BRAND['bg_card'],
                                                progress_color=BRAND['accent'],
                                                height=4, corner_radius=2)
        self.progress_bar.pack(fill='x', pady=(0, 4))
        self.progress_bar.set(0)

        # ── Status bar ──
        self.status_frame = ctk.CTkFrame(view, fg_color=BRAND['bg_card'],
                                          corner_radius=8, height=36)
        self.status_frame.pack(fill='x', pady=(0, 8))
        self.status_frame.pack_propagate(False)

        self.status_label = ctk.CTkLabel(self.status_frame, text="Ready — import a file to begin",
                                          font=(BRAND['font_family'], 11),
                                          text_color=BRAND['text_secondary'])
        self.status_label.pack(side='left', padx=12)

        self.stats_label = ctk.CTkLabel(self.status_frame, text="",
                                         font=(BRAND['font_mono'], 11),
                                         text_color=BRAND['accent'])
        self.stats_label.pack(side='right', padx=12)

        # ── Advanced toggle + Instruction input ──
        self.advanced_toggle_btn = ctk.CTkButton(
            view, text="▸  Custom Instruction (Advanced)",
            height=28, anchor='w',
            font=(BRAND['font_family'], 11),
            fg_color='transparent', hover_color=BRAND['bg_hover'],
            text_color=BRAND['text_muted'],
            border_color=BRAND['border'], border_width=1,
            corner_radius=8,
            command=self._toggle_advanced_instruction,
        )
        self.advanced_toggle_btn.pack(fill='x', pady=(0, 4))

        self.instr_frame = ctk.CTkFrame(view, fg_color=BRAND['bg_card'], corner_radius=12)
        # Packed immediately so it's visible before a file is loaded
        self.instr_frame.pack(fill='x', pady=(0, 12))

        instr_header = ctk.CTkFrame(self.instr_frame, fg_color='transparent')
        instr_header.pack(fill='x', padx=16, pady=(12, 4))

        ctk.CTkLabel(instr_header, text="What do you need?",
                      font=(BRAND['font_family'], 14, 'bold'),
                      text_color=BRAND['text_primary']).pack(side='left')

        # Help tooltip button
        help_btn = ctk.CTkButton(
            instr_header, text="?", width=24, height=24,
            font=(BRAND['font_family'], 11, 'bold'),
            fg_color=BRAND['bg_input'],
            hover_color=BRAND['bg_hover'],
            text_color=BRAND['text_muted'],
            corner_radius=12,
            command=self._show_instruction_help,
        )
        help_btn.pack(side='right')

        self.instruction_input = ctk.CTkTextbox(
            self.instr_frame, height=60,
            font=(BRAND['font_family'], 12),
            fg_color=BRAND['bg_input'],
            text_color=BRAND['text_primary'],
            border_color=BRAND['border'],
            border_width=1, corner_radius=8,
        )
        self.instruction_input.pack(fill='x', padx=16, pady=(0, 4))

        # Set initial placeholder with rotating examples
        self.placeholder_examples = [
            "Extract MFG and PN from Material Description into columns A and B",
            "Pull part number from Description column and put in PartNum column",
            "Get manufacturer from Product Info and place in MFG column",
            "Parse MFG, PN, and Description from Material text into separate columns",
        ]
        self.current_placeholder_idx = 0
        self.instruction_input.insert('1.0', f"e.g., {self.placeholder_examples[0]}")
        self.instruction_input.bind('<FocusIn>', self._clear_placeholder)
        self.instruction_input.bind('<KeyRelease>', lambda e: self._update_interpretation())

        # Interpretation feedback (now more prominent with badge style)
        interp_container = ctk.CTkFrame(self.instr_frame, fg_color='transparent')
        interp_container.pack(fill='x', padx=16, pady=(4, 0))

        self.interp_badge = ctk.CTkFrame(interp_container, fg_color=BRAND['bg_input'],
                                          corner_radius=6)
        self.interp_label = ctk.CTkLabel(self.interp_badge, text="",
                                          font=(BRAND['font_family'], 10),
                                          text_color=BRAND['text_secondary'])

        # Suggestion chips
        self.suggestion_frame = ctk.CTkFrame(self.instr_frame, fg_color='transparent')
        self.suggestion_frame.pack(fill='x', padx=16, pady=(4, 8))

        suggestions = [
            ("Need help?", self._show_instruction_help),
            ("See examples", self._rotate_placeholder),
        ]

        for text, cmd in suggestions:
            chip = ctk.CTkButton(
                self.suggestion_frame, text=text,
                width=90, height=24,
                font=(BRAND['font_family'], 9),
                fg_color='transparent',
                hover_color=BRAND['bg_hover'],
                text_color=BRAND['text_muted'],
                border_color=BRAND['border'],
                border_width=1,
                corner_radius=12,
                command=cmd,
            )
            chip.pack(side='left', padx=(0, 6))

        # ── Preview table ──
        self.preview_frame = ctk.CTkFrame(view, fg_color=BRAND['bg_card'], corner_radius=12)
        self.preview_frame.pack(fill='both', expand=True)

        preview_header = ctk.CTkFrame(self.preview_frame, fg_color='transparent')
        preview_header.pack(fill='x', padx=16, pady=(12, 8))

        ctk.CTkLabel(preview_header, text="Preview",
                      font=(BRAND['font_family'], 14, 'bold'),
                      text_color=BRAND['text_primary']).pack(side='left')

        self.preview_toggle = ctk.CTkSegmentedButton(
            preview_header, values=["Input", "Output"],
            font=(BRAND['font_family'], 11),
            command=self._toggle_preview,
        )
        self.preview_toggle.pack(side='right')
        self.preview_toggle.set("Input")

        # Table using Treeview (more capable for tabular data)
        table_container = ctk.CTkFrame(self.preview_frame, fg_color=BRAND['bg_input'],
                                        corner_radius=8)
        table_container.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        # Scrollbars
        x_scroll = tk.Scrollbar(table_container, orient='horizontal')
        y_scroll = tk.Scrollbar(table_container, orient='vertical')

        self.table = tk.ttk.Treeview(
            table_container,
            show='headings',
            xscrollcommand=x_scroll.set,
            yscrollcommand=y_scroll.set,
        )

        x_scroll.config(command=self.table.xview)
        y_scroll.config(command=self.table.yview)
        x_scroll.pack(side='bottom', fill='x')
        y_scroll.pack(side='right', fill='y')
        self.table.pack(fill='both', expand=True)

        # Style the treeview
        style = tk.ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview',
                         background=BRAND['bg_input'],
                         foreground=BRAND['text_primary'],
                         fieldbackground=BRAND['bg_input'],
                         borderwidth=0,
                         font=(BRAND['font_family'], 10))
        style.configure('Treeview.Heading',
                         background=BRAND['bg_card'],
                         foreground=BRAND['text_secondary'],
                         font=(BRAND['font_family'], 10, 'bold'),
                         borderwidth=0)
        style.map('Treeview', background=[('selected', BRAND['accent_dim'])],
                   foreground=[('selected', BRAND['accent'])])

    # ───────────────────────────────────────────────────────
    #  HISTORY VIEW
    # ───────────────────────────────────────────────────────

    def _build_history_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color='transparent')
        self.views['history'] = view

        ctk.CTkLabel(view, text="Processing History",
                      font=(BRAND['font_family'], 24, 'bold'),
                      text_color=BRAND['text_primary']).pack(anchor='w', pady=(0, 16))

        self.history_scroll = ctk.CTkScrollableFrame(view, fg_color='transparent')
        self.history_scroll.pack(fill='both', expand=True)

    def _populate_history(self):
        # Clear existing
        for w in self.history_scroll.winfo_children():
            w.destroy()

        jobs = history_db.get_recent_jobs(20)

        if not jobs:
            ctk.CTkLabel(self.history_scroll, text="No processing history yet.",
                          font=(BRAND['font_family'], 13),
                          text_color=BRAND['text_muted']).pack(pady=40)
            return

        for job in jobs:
            card = ctk.CTkFrame(self.history_scroll, fg_color=BRAND['bg_card'],
                                 corner_radius=10, height=70)
            card.pack(fill='x', pady=4)
            card.pack_propagate(False)

            inner = ctk.CTkFrame(card, fg_color='transparent')
            inner.pack(fill='x', padx=16, pady=10)

            # Left: file info
            left = ctk.CTkFrame(inner, fg_color='transparent')
            left.pack(side='left', fill='y')

            ctk.CTkLabel(left, text=job.get('filename', 'Unknown'),
                          font=(BRAND['font_family'], 12, 'bold'),
                          text_color=BRAND['text_primary']).pack(anchor='w')

            ts = job.get('timestamp', '')[:16].replace('T', '  ')
            pipeline = job.get('pipeline', '')
            ctk.CTkLabel(left, text=f"{ts}  •  {pipeline}",
                          font=(BRAND['font_family'], 10),
                          text_color=BRAND['text_muted']).pack(anchor='w')

            # Right: stats
            right = ctk.CTkFrame(inner, fg_color='transparent')
            right.pack(side='right')

            stats_text = f"MFG: {job.get('mfg_filled', 0)}  PN: {job.get('pn_filled', 0)}  Rows: {job.get('total_rows', 0)}"
            ctk.CTkLabel(right, text=stats_text,
                          font=(BRAND['font_mono'], 10),
                          text_color=BRAND['accent']).pack()

    # ───────────────────────────────────────────────────────
    #  CONFIGS VIEW
    # ───────────────────────────────────────────────────────

    def _build_configs_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color='transparent')
        self.views['configs'] = view

        ctk.CTkLabel(view, text="Saved Configurations",
                      font=(BRAND['font_family'], 24, 'bold'),
                      text_color=BRAND['text_primary']).pack(anchor='w', pady=(0, 16))

        self.configs_scroll = ctk.CTkScrollableFrame(view, fg_color='transparent')
        self.configs_scroll.pack(fill='both', expand=True)

    def _populate_configs(self):
        for w in self.configs_scroll.winfo_children():
            w.destroy()

        configs = history_db.get_saved_configs()

        if not configs:
            ctk.CTkLabel(self.configs_scroll,
                          text="No saved configurations. Run a job and click 'Save Config' to save.",
                          font=(BRAND['font_family'], 13),
                          text_color=BRAND['text_muted']).pack(pady=40)
            return

        for cfg in configs:
            card = ctk.CTkFrame(self.configs_scroll, fg_color=BRAND['bg_card'],
                                 corner_radius=10)
            card.pack(fill='x', pady=4)

            inner = ctk.CTkFrame(card, fg_color='transparent')
            inner.pack(fill='x', padx=16, pady=10)

            left = ctk.CTkFrame(inner, fg_color='transparent')
            left.pack(side='left', fill='y')

            ctk.CTkLabel(left, text=cfg.get('name', 'Untitled'),
                          font=(BRAND['font_family'], 12, 'bold'),
                          text_color=BRAND['text_primary']).pack(anchor='w')
            ctk.CTkLabel(left, text=cfg.get('instruction', ''),
                          font=(BRAND['font_family'], 10),
                          text_color=BRAND['text_muted'],
                          wraplength=500).pack(anchor='w')

            use_btn = ctk.CTkButton(
                inner, text="Use", width=60, height=28,
                font=(BRAND['font_family'], 11),
                fg_color=BRAND['accent_dim'],
                hover_color=BRAND['accent'],
                text_color=BRAND['accent'],
                corner_radius=6,
                command=lambda c=cfg: self._load_config(c),
            )
            use_btn.pack(side='right')

    # ───────────────────────────────────────────────────────
    #  NAVIGATION
    # ───────────────────────────────────────────────────────

    def _show_parser(self):
        self._clear_view()
        self._select_nav('parser')
        self.views['parser'].pack(fill='both', expand=True)

    def _show_history(self):
        self._clear_view()
        self._select_nav('history')
        self.views['history'].pack(fill='both', expand=True)
        self._populate_history()

    def _show_configs(self):
        self._clear_view()
        self._select_nav('configs')
        self.views['configs'].pack(fill='both', expand=True)
        self._populate_configs()

    def _train_from_files(self):
        """Open folder picker and run training data ingestion."""
        folder = filedialog.askdirectory(
            title="Select folder with completed training files"
        )
        if not folder:
            return

        # Run training in a thread to avoid blocking UI
        self.status_label.configure(text="Training in progress...")
        self.update_idletasks()

        def run_training():
            try:
                training_path = os.path.join(os.path.dirname(__file__), 'training_data.json')
                result = ingest_training_files(folder, training_path)

                # Reload training data
                self.training_data = load_training_data(training_path)

                # Update UI on main thread
                summary = (
                    f"Training complete!\n\n"
                    f"Files processed: {result['files_processed']}\n"
                    f"Rows analyzed: {result['total_rows_analyzed']}\n"
                    f"Known manufacturers: {len(result['known_manufacturers'])}\n"
                    f"MFG normalizations: {len(result['mfg_normalization'])}"
                )
                self.after(0, lambda: messagebox.showinfo("Training Complete", summary))
                self.after(0, lambda: self.status_label.configure(text="Training complete — ready for improved parsing"))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Training Error", str(e)))
                self.after(0, lambda: self.status_label.configure(text=f"Training error: {str(e)}"))

        threading.Thread(target=run_training, daemon=True).start()

    # ───────────────────────────────────────────────────────
    #  FILE HANDLING
    # ───────────────────────────────────────────────────────

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls *.csv"), ("All files", "*.*")]
        )
        if path:
            self._load_file(path)

    def _on_drop(self, event):
        path = event.data.strip('{}')
        if path.lower().endswith(('.xlsx', '.xls', '.csv')):
            self._load_file(path)

    def _show_data_tips(self):
        """Display data validation tips after file load."""
        if self.df_input is None:
            return

        # Clear existing tips
        for widget in self.data_tips_frame.winfo_children():
            widget.destroy()

        # Analyze the data
        empty_cols = [col for col in self.df_input.columns
                      if self.df_input[col].isna().all() or
                      (self.df_input[col].astype(str).str.strip() == '').all()]

        has_empty_cols = len(empty_cols) > 0

        # Build tips content
        tips_inner = ctk.CTkFrame(self.data_tips_frame, fg_color='transparent')
        tips_inner.pack(fill='both', padx=16, pady=12)

        # Header
        if has_empty_cols:
            icon = "✓"
            header_text = "Your file is ready!"
            header_color = BRAND['success']
        else:
            icon = "ℹ️"
            header_text = "Data Preparation Tips"
            header_color = BRAND['info']

        header = ctk.CTkLabel(
            tips_inner, text=f"{icon}  {header_text}",
            font=(BRAND['font_family'], 12, 'bold'),
            text_color=header_color
        )
        header.pack(anchor='w')

        # Tips list
        tips_list = ctk.CTkFrame(tips_inner, fg_color='transparent')
        tips_list.pack(fill='x', pady=(4, 0))

        tips = []
        if has_empty_cols:
            tips.append(f"✓  Found {len(empty_cols)} empty column(s) ready to fill")
            tips.append(f"💡  Columns: {', '.join(empty_cols[:3])}{'...' if len(empty_cols) > 3 else ''}")
        else:
            tips.append("⚠️  No empty columns detected")
            tips.append("💡  Add empty columns next to your source data for results")
            tips.append("💡  Empty columns should be to the RIGHT of source data")

        tips.append("☑️  Check the columns below to select your source data")

        for tip in tips:
            tip_label = ctk.CTkLabel(
                tips_list, text=tip,
                font=(BRAND['font_family'], 10),
                text_color=BRAND['text_secondary'],
                anchor='w'
            )
            tip_label.pack(anchor='w', pady=1)

        # Show the tips frame
        self.data_tips_frame.pack(fill='x', pady=(0, 12))
        self.data_tips_frame.pack_propagate(False)

    def _load_file(self, path: str):
        try:
            self.status_label.configure(text="Loading file...")
            self.update_idletasks()

            if path.lower().endswith('.csv'):
                self.df_input = pd.read_csv(path)
            else:
                self.df_input = pd.read_excel(path, engine='openpyxl')

            self.df_input.columns = [str(c).strip() for c in self.df_input.columns]
            self.current_file = path
            filename = os.path.basename(path)

            # Map columns using smart detection
            self.column_mapping = map_columns(self.df_input, self.training_data)

            # Build/refresh the column selector UI
            self._refresh_column_selector()

            self.import_label.configure(text=f"✓  {filename}")
            # Shrink import frame after load to reclaim vertical space
            self.import_frame.configure(height=80)
            self.file_info_label.configure(
                text=f"{len(self.df_input)} rows  •  {len(self.df_input.columns)} columns  •  "
                     f"Cols: {', '.join(self.df_input.columns[:6])}{'...' if len(self.df_input.columns) > 6 else ''}"
            )
            self.import_frame.configure(border_color=BRAND['accent'], border_width=1)

            self._populate_table(self.df_input)
            self.status_label.configure(text=f"Loaded: {filename}")
            self.preview_toggle.set("Input")

            # Regenerate quick templates to reference the actual detected columns
            self._update_templates()

            # Show data preparation tips
            self._show_data_tips()

            # Auto-interpret any existing instruction
            self._update_interpretation()

        except Exception as e:
            self.status_label.configure(text=f"Error loading file: {str(e)}")
            messagebox.showerror("Import Error", str(e))

    # ───────────────────────────────────────────────────────
    #  TABLE DISPLAY
    # ───────────────────────────────────────────────────────

    def _populate_table(self, df: pd.DataFrame, max_rows: int = 200):
        """Fill the preview table with DataFrame content."""
        # Clear existing
        self.table.delete(*self.table.get_children())
        self.table['columns'] = list(df.columns)

        for col in df.columns:
            self.table.heading(col, text=col)
            # Auto-size columns
            max_width = max(len(str(col)) * 9, 80)
            sample = df[col].dropna().astype(str).head(20)
            if len(sample) > 0:
                max_width = max(max_width, min(sample.str.len().max() * 8, 300))
            self.table.column(col, width=int(max_width), minwidth=60)

        # Insert rows (limit for performance)
        display_df = df.head(max_rows)
        for _, row in display_df.iterrows():
            values = [str(v) if pd.notna(v) else '' for v in row]
            self.table.insert('', 'end', values=values)

        if len(df) > max_rows:
            self.status_label.configure(
                text=f"Showing first {max_rows} of {len(df)} rows"
            )

    def _toggle_preview(self, value):
        if value == "Input" and self.df_input is not None:
            self._populate_table(self.df_input)
        elif value == "Output" and self.df_output is not None:
            self._populate_table(self.df_output)

    # ───────────────────────────────────────────────────────
    #  INSTRUCTION HANDLING
    # ───────────────────────────────────────────────────────

    def _clear_placeholder(self, event=None):
        content = self.instruction_input.get('1.0', 'end').strip()
        if content.startswith('e.g.,'):
            self.instruction_input.delete('1.0', 'end')

    def _get_instruction(self) -> str:
        text = self.instruction_input.get('1.0', 'end').strip()
        if text.startswith('e.g.,'):
            return ''
        return text

    def _update_interpretation(self):
        instruction = self._get_instruction()
        if instruction and self.df_input is not None:
            cols = list(self.df_input.columns)
            parsed = parse_instruction(instruction, cols, column_mapping=self.column_mapping)
            # Show interpretation in a prominent badge
            self.interp_label.configure(text=f"⚡ Interpreted as: {parsed.explanation}")
            self.interp_label.pack(padx=8, pady=4)
            self.interp_badge.pack(side='left', pady=(0, 4))
        else:
            self.interp_badge.pack_forget()

    def _rotate_placeholder(self):
        """Cycle through example placeholders and show in a popup."""
        self.current_placeholder_idx = (self.current_placeholder_idx + 1) % len(self.placeholder_examples)
        example = self.placeholder_examples[self.current_placeholder_idx]

        # Always replace the instruction field with the new example
        self.instruction_input.delete('1.0', 'end')
        self.instruction_input.insert('1.0', example)
        self.instruction_input.focus()

        # Update interpretation immediately
        self._update_interpretation()

    def _show_instruction_help(self):
        """Show a help dialog about writing good instructions."""
        help_text = """How to Write Good Instructions:

✅ BE SPECIFIC
"Extract MFG from column A into column B"
NOT: "Get the manufacturer"

✅ MENTION COLUMNS
Use column names or letters (A, B, C, etc.)
"Pull part number from 'Description' into column D"

✅ INDICATE SOURCE AND DESTINATION
"Parse Material Description: MFG → column C, PN → column D"

✅ USE NATURAL LANGUAGE
The parser understands phrases like:
• "Extract MFG and PN from..."
• "Get manufacturer from..."
• "Build SIM values..."
• "Clean part numbers in..."

💡 TIP: Check the "Interpreted as" feedback below the input box!
"""
        messagebox.showinfo("Instruction Writing Guide", help_text)

    # ───────────────────────────────────────────────────────
    #  COLUMN-FIRST SELECTOR
    # ───────────────────────────────────────────────────────

    def _toggle_advanced_instruction(self):
        """Show or hide the instruction text box (Advanced/Custom mode)."""
        if self._advanced_visible:
            self.instr_frame.pack_forget()
            self._advanced_visible = False
            self.advanced_toggle_btn.configure(text="▸  Custom Instruction (Advanced)")
        else:
            # Pack instr_frame after the advanced toggle button
            self.instr_frame.pack(fill='x', pady=(0, 12),
                                   after=self.advanced_toggle_btn)
            self._advanced_visible = True
            self.advanced_toggle_btn.configure(text="▾  Custom Instruction (Advanced)")

    def _get_column_preview(self, col_name: str, n: int = 5) -> str:
        """Return first N non-null values from a column as a readable string."""
        if self.df_input is None or col_name not in self.df_input.columns:
            return "No data"
        sample = self.df_input[col_name].dropna().head(n).astype(str).tolist()
        if not sample:
            return "(empty column)"
        return "\n".join(f"  {v[:80]}" for v in sample)

    def _refresh_column_selector(self):
        """
        Rebuild the column selector widget after a file is loaded.

        Shows column checkboxes with auto-suggestions, output placement radio
        buttons, and an optional supplier column dropdown.  Packed with
        after=self.import_frame so it sits between the import zone and the
        Advanced instruction toggle.
        """
        if self.df_input is None:
            return

        # Clear previous content
        for widget in self.col_selector_frame.winfo_children():
            widget.destroy()
        self.col_selector_vars = {}

        # Build suggestions from the already-computed column_mapping
        self._col_suggestions = suggest_columns(self.df_input, self.column_mapping)
        suggested_cols = {s['column'] for s in self._col_suggestions.get('source_suggestions', [])}
        suggestion_meta = {s['column']: s for s in self._col_suggestions.get('source_suggestions', [])}

        cols = list(self.df_input.columns)

        # ── Header ──
        hdr = ctk.CTkFrame(self.col_selector_frame, fg_color='transparent')
        hdr.pack(fill='x', padx=16, pady=(12, 4))
        ctk.CTkLabel(hdr, text="SOURCE COLUMNS",
                     font=(BRAND['font_family'], 12, 'bold'),
                     text_color=BRAND['text_primary']).pack(side='left')
        ctk.CTkLabel(hdr, text="Select columns to extract from",
                     font=(BRAND['font_family'], 10),
                     text_color=BRAND['text_muted']).pack(side='left', padx=(8, 0))

        # ── Scrollable column list ──
        # Dynamic height: cap at 130px so action buttons stay visible
        n_cols = len(list(self.df_input.columns))
        scroll_h = min(max(n_cols * 26, 80), 130)
        scroll = ctk.CTkScrollableFrame(self.col_selector_frame,
                                         fg_color='transparent', height=scroll_h)
        scroll.pack(fill='x', padx=8, pady=4)

        # Column preview label (updated on click)
        self._col_preview_label = ctk.CTkLabel(
            self.col_selector_frame, text="",
            font=(BRAND['font_mono'], 9),
            text_color=BRAND['text_muted'],
            justify='left', anchor='w',
        )

        for i, col in enumerate(cols):
            letter = chr(ord('A') + i) if i < 26 else f"Col{i + 1}"
            is_suggested = col in suggested_cols
            meta = suggestion_meta.get(col, {})

            row = ctk.CTkFrame(scroll, fg_color='transparent')
            row.pack(fill='x', pady=1)

            var = tk.BooleanVar(value=is_suggested)
            self.col_selector_vars[col] = var

            cb = ctk.CTkCheckBox(
                row,
                text=f"{letter}:  {col}",
                variable=var,
                font=(BRAND['font_family'], 11),
                text_color=BRAND['accent'] if is_suggested else BRAND['text_primary'],
                fg_color=BRAND['accent'],
                hover_color=BRAND['accent_hover'],
                command=self._on_col_selector_change,
            )
            cb.pack(side='left', padx=4)

            # Right side: reason/hint
            hint = meta.get('reason', '') if is_suggested else ''
            if is_suggested:
                ctk.CTkLabel(row, text=f"⭐ {hint}",
                             font=(BRAND['font_mono'], 9),
                             text_color=BRAND['warning']).pack(side='right', padx=8)
            else:
                # Show avg char length for all columns so user can identify text cols
                try:
                    s = self.df_input[col].dropna().head(10).astype(str)
                    avg_len = int(s.str.len().mean()) if len(s) > 0 else 0
                    ctk.CTkLabel(row, text=f"~{avg_len} chars",
                                 font=(BRAND['font_mono'], 9),
                                 text_color=BRAND['text_muted']).pack(side='right', padx=8)
                except Exception:
                    pass

            # Click row to preview column values
            def _show_preview(c=col):
                preview = self._get_column_preview(c)
                self._col_preview_label.configure(
                    text=f"  Preview — {c}:\n{preview}"
                )
                self._col_preview_label.pack(fill='x', padx=16, pady=(0, 4))

            row.bind('<Button-1>', lambda e, c=col: _show_preview(c))

        # Collapse preview initially
        # (it's shown on row click, not packed by default)

        # ── Output placement ──
        placement_sep = ctk.CTkFrame(self.col_selector_frame,
                                      fg_color=BRAND['border'], height=1)
        placement_sep.pack(fill='x', padx=16, pady=(4, 8))

        placement_hdr = ctk.CTkFrame(self.col_selector_frame, fg_color='transparent')
        placement_hdr.pack(fill='x', padx=16)
        ctk.CTkLabel(placement_hdr, text="OUTPUT PLACEMENT",
                     font=(BRAND['font_family'], 11, 'bold'),
                     text_color=BRAND['text_primary']).pack(side='left')

        self.output_position_var = tk.StringVar(value='end')
        radio_frame = ctk.CTkFrame(self.col_selector_frame, fg_color='transparent')
        radio_frame.pack(fill='x', padx=24, pady=(4, 0))

        ctk.CTkRadioButton(radio_frame,
                           text="Insert MFG + PN at end (append new columns)",
                           variable=self.output_position_var, value='end',
                           font=(BRAND['font_family'], 11),
                           fg_color=BRAND['accent'],
                           hover_color=BRAND['accent_hover'],
                           ).pack(anchor='w', pady=2)
        ctk.CTkRadioButton(radio_frame,
                           text="Insert MFG + PN at front (columns A–B)",
                           variable=self.output_position_var, value='front',
                           font=(BRAND['font_family'], 11),
                           fg_color=BRAND['accent'],
                           hover_color=BRAND['accent_hover'],
                           ).pack(anchor='w', pady=2)

        # ── Supplier column dropdown ──
        sup_suggestion = self._col_suggestions.get('supplier_suggestion')
        sup_frame = ctk.CTkFrame(self.col_selector_frame, fg_color='transparent')
        sup_frame.pack(fill='x', padx=16, pady=(8, 12))

        ctk.CTkLabel(sup_frame,
                     text="SUPPLIER COLUMN  (optional — used as MFG fallback)",
                     font=(BRAND['font_family'], 10),
                     text_color=BRAND['text_muted']).pack(anchor='w')

        sup_options = ['None'] + cols
        default_sup = sup_suggestion['column'] if sup_suggestion else 'None'
        self.supplier_col_var = tk.StringVar(value=default_sup)

        ctk.CTkOptionMenu(
            sup_frame,
            values=sup_options,
            variable=self.supplier_col_var,
            font=(BRAND['font_family'], 11),
            fg_color=BRAND['bg_input'],
            button_color=BRAND['accent_dim'],
            button_hover_color=BRAND['accent'],
            dropdown_fg_color=BRAND['bg_card'],
            text_color=BRAND['text_primary'],
            width=260,
        ).pack(anchor='w', pady=(4, 0))

        # Pack the frame into the view right after the import frame
        self.col_selector_frame.pack(fill='x', pady=(0, 12),
                                      after=self.import_frame)

        # After file load: collapse the instruction section (it becomes Advanced)
        if self._advanced_visible:
            pass  # leave as-is if user had it open
        else:
            self.instr_frame.pack_forget()
            self.advanced_toggle_btn.configure(text="▸  Custom Instruction (Advanced)")

    def _on_col_selector_change(self):
        """Called when any column checkbox changes — could enable/disable run button."""
        selected = [col for col, var in self.col_selector_vars.items() if var.get()]
        # Run button state: enabled if file loaded (regardless of selection)
        # (zero selections → engine will fall back to instruction parsing)
        pass

    def _render_template_buttons(self, templates: list):
        """Clear and rebuild the template buttons in self.templates_frame."""
        for widget in self.templates_frame.winfo_children():
            widget.destroy()
        for name, instruction in templates:
            btn = ctk.CTkButton(
                self.templates_frame, text=f"  {name}", anchor='w',
                font=(BRAND['font_family'], 11),
                fg_color=BRAND['accent_dim'],
                hover_color=BRAND['bg_hover'],
                text_color=BRAND['accent'],
                height=32, corner_radius=6,
                command=lambda inst=instruction: self._apply_template(inst),
            )
            btn.pack(fill='x', padx=16, pady=2)

    def _update_templates(self):
        """Regenerate quick templates based on detected columns after a file is loaded."""
        if not self.column_mapping:
            return
        desc_cols = self.column_mapping.get('source_description', [])
        source_text = ' and '.join(desc_cols) if desc_cols else 'description columns'
        templates = [
            ("MFG + PN Extract", f"Extract MFG and PN from {source_text}"),
            ("Part Number Clean", "Clean and validate part numbers from description fields"),
            ("Build SIM Values", "Generate SIM from MFG and ITEM # for rows with missing SIM"),
        ]
        self._render_template_buttons(templates)

    def _apply_template(self, instruction: str):
        self._show_parser()
        self.instruction_input.delete('1.0', 'end')
        self.instruction_input.insert('1.0', instruction)
        self._update_interpretation()

    def _load_config(self, cfg: dict):
        self._show_parser()
        instruction = cfg.get('instruction', '')
        self.instruction_input.delete('1.0', 'end')
        self.instruction_input.insert('1.0', instruction)
        self._update_interpretation()

    # ───────────────────────────────────────────────────────
    #  PARSER EXECUTION
    # ───────────────────────────────────────────────────────

    def _run_parser(self):
        if self.df_input is None:
            messagebox.showwarning("No File", "Please import an Excel file first.")
            return
        if self.is_processing:
            return

        self.is_processing = True
        self.run_btn.configure(state='disabled', text="⏳  Processing...")
        self.progress_bar.set(0)
        self.status_label.configure(text="Processing...")

        # Run in background thread
        thread = threading.Thread(target=self._execute_pipeline, daemon=True)
        thread.start()

    def _execute_pipeline(self):
        try:
            instruction = self._get_instruction()
            cols = list(self.df_input.columns)

            # ── Column-first mode: explicit UI selection takes priority ──
            explicit_sources = [col for col, var in self.col_selector_vars.items()
                                 if var.get()]

            # Always parse instruction (for pipeline type detection + output column names).
            # If no instruction is given, parsed fields will be empty/defaults.
            parsed = parse_instruction(instruction, cols, column_mapping=self.column_mapping)

            # Auto-detect pipeline type if not specified by instruction
            pipeline = parsed.pipeline
            if pipeline == 'auto':
                pipeline = auto_detect_pipeline(self.df_input)

            self.after(0, lambda: self.progress_bar.set(0.2))

            # ── Supplier column: dropdown beats mapping fallback ──
            supplier_col = None
            if self.supplier_col_var:
                sc = self.supplier_col_var.get()
                supplier_col = sc if sc and sc != 'None' else None
            if supplier_col is None and self.column_mapping:
                supplier_col = self.column_mapping.get('supplier')

            # ── Route to appropriate pipeline ──
            if pipeline == 'mfg_pn':
                if explicit_sources:
                    # COLUMN-FIRST: use exactly what the user selected — no guessing
                    source_cols = explicit_sources
                else:
                    # LEGACY: derive from instruction parsing with nuclear fallback
                    source_cols = parsed.source_columns or [
                        c for c in cols if any(k in c.upper() for k in
                        ['MATERIAL', 'DESCRIPTION', 'PO TEXT'])
                    ]
                    if source_cols and self.column_mapping:
                        mapper_sources = (
                            self.column_mapping.get('source_description', []) +
                            self.column_mapping.get('source_po_text', []) +
                            self.column_mapping.get('source_notes', [])
                        )
                        if mapper_sources:
                            for col in list(source_cols):
                                if col in self.df_input.columns:
                                    sample = self.df_input[col].dropna().head(20).astype(str)
                                    text_pct = (
                                        sum(1 for v in sample if any(c.isalpha() for c in str(v)))
                                        / max(len(sample), 1)
                                    )
                                    if text_pct < 0.3:
                                        source_cols = mapper_sources
                                        break

                result = pipeline_mfg_pn(
                    self.df_input, source_cols,
                    mfg_col=parsed.target_mfg_col,
                    pn_col=parsed.target_pn_col,
                    add_sim=parsed.add_sim,
                    column_mapping=self.column_mapping,
                    supplier_col=supplier_col,
                )

            elif pipeline == 'part_number':
                pn_col = next((c for c in cols if 'PART NUMBER' in c.upper()), 'Part Number 1')
                mfg_col = next((c for c in cols if 'MANUFACTURER' in c.upper()), 'Manufacturer 1')
                result = pipeline_part_number(self.df_input, pn_col=pn_col, mfg_col=mfg_col)

            elif pipeline == 'sim':
                mfg_col = next((c for c in cols if c.upper() in ('MFG', 'MANUFACTURER')), 'MFG')
                item_col = next((c for c in cols if 'ITEM' in c.upper()), 'ITEM #')
                sim_pattern = parsed.sim_pattern if parsed.sim_pattern in ('A', 'B', 'C') else 'C'
                result = pipeline_sim_builder(
                    self.df_input, mfg_col=mfg_col,
                    item_col=item_col, pattern=sim_pattern,
                )
            else:
                # Default fallback: mfg_pn with best available sources
                if explicit_sources:
                    source_cols = explicit_sources
                else:
                    source_cols = [c for c in cols if any(k in c.upper() for k in
                                   ['MATERIAL', 'DESCRIPTION', 'PO TEXT', 'NOTES'])]
                    if not source_cols:
                        source_cols = cols[:3]
                result = pipeline_mfg_pn(self.df_input, source_cols,
                                         column_mapping=self.column_mapping,
                                         supplier_col=supplier_col)

            self.after(0, lambda: self.progress_bar.set(0.7))

            # ── Output placement: reorder MFG/PN to front if requested ──
            if (self.output_position_var and self.output_position_var.get() == 'front'):
                mfg = parsed.target_mfg_col
                pn = parsed.target_pn_col
                df = result.df
                front_cols = [c for c in (mfg, pn) if c in df.columns]
                other_cols = [c for c in df.columns if c not in front_cols]
                if front_cols:
                    result.df = df[front_cols + other_cols]

            # ── Run QA ──
            mfg_col_name = parsed.target_mfg_col
            issues = run_qa(result.df, mfg_col=mfg_col_name)

            self.after(0, lambda: self.progress_bar.set(0.9))

            # Store results
            self.df_output = result.df
            self.job_result = result
            self.job_result.issues = issues

            # Save to history
            history_db.save_job(
                filename=os.path.basename(self.current_file or 'unknown'),
                instruction=instruction, pipeline=pipeline,
                source_columns=explicit_sources or parsed.source_columns,
                target_mfg=parsed.target_mfg_col,
                target_pn=parsed.target_pn_col,
                add_sim=parsed.add_sim,
                sim_pattern=parsed.sim_pattern,
                total_rows=result.total_rows,
                mfg_filled=result.mfg_filled,
                pn_filled=result.pn_filled,
                sim_filled=result.sim_filled,
                issues_count=len(issues),
                output_path='',
            )

            # Update UI on main thread
            self.after(0, lambda: self._on_pipeline_complete(result, issues, pipeline))

        except Exception as e:
            self.after(0, lambda: self._on_pipeline_error(str(e)))

    def _on_pipeline_complete(self, result, issues, pipeline):
        self.progress_bar.set(1.0)
        self.is_processing = False
        self.run_btn.configure(state='normal', text="▶  Run Parser")
        self.export_btn.configure(state='normal')
        self.save_config_btn.configure(state='normal')

        # Show output in preview
        self.preview_toggle.set("Output")
        self._populate_table(self.df_output)

        # Stats
        stats_parts = [f"Rows: {result.total_rows}"]
        if result.mfg_filled:
            stats_parts.append(f"MFG filled: {result.mfg_filled}")
        if result.pn_filled:
            stats_parts.append(f"PN filled: {result.pn_filled}")
        if result.sim_filled:
            stats_parts.append(f"SIM filled: {result.sim_filled}")
        if issues:
            stats_parts.append(f"⚠ {len(issues)} issues")

        self.stats_label.configure(text="  •  ".join(stats_parts))
        self.status_label.configure(
            text=f"✓ Complete — {pipeline} pipeline  •  Ready to export"
        )

    def _on_pipeline_error(self, error_msg):
        self.progress_bar.set(0)
        self.is_processing = False
        self.run_btn.configure(state='normal', text="▶  Run Parser")
        self.status_label.configure(text=f"✗ Error: {error_msg}")
        messagebox.showerror("Processing Error", error_msg)

    # ───────────────────────────────────────────────────────
    #  EXPORT
    # ───────────────────────────────────────────────────────

    def _export_result(self):
        if self.df_output is None:
            return

        # Default to CSV to avoid Excel corruption issues
        default_name = os.path.basename(self.current_file or 'output').replace(
            '.xlsx', ' - parsed.csv'
        ).replace('.xls', ' - parsed.csv')

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV (Recommended)", "*.csv"), ("Excel", "*.xlsx")],
        )
        if not path:
            return

        try:
            # Force CSV export for reliability - Excel export has issues in packaged builds
            if not path.lower().endswith('.csv'):
                # User selected Excel, but we'll force CSV and warn them
                csv_path = os.path.splitext(path)[0] + '.csv'
                path = csv_path

            # Export main file as CSV (always works, Excel can open it)
            self.df_output.to_csv(path, index=False, encoding='utf-8-sig')
            export_format = 'CSV'

            # Verify the file was created
            if not os.path.exists(path):
                raise Exception(f"File was not created at: {path}")

            file_size = os.path.getsize(path)
            if file_size == 0:
                raise Exception(f"File was created but is empty: {path}")

            # Also export QA report if there are issues
            qa_path = None
            if self.job_result and self.job_result.issues:
                try:
                    qa_path = path.replace('.csv', ' - QA Issues.csv')
                    pd.DataFrame(self.job_result.issues).to_csv(qa_path, index=False, encoding='utf-8-sig')

                    self.status_label.configure(
                        text=f"✓ Exported ({export_format}): {os.path.basename(path)} + QA report"
                    )
                except Exception as qa_error:
                    # QA export failed - just show main file success
                    print(f"QA report export failed: {qa_error}")
                    self.status_label.configure(
                        text=f"✓ Exported ({export_format}): {os.path.basename(path)}"
                    )
            else:
                self.status_label.configure(
                    text=f"✓ Exported ({export_format}): {os.path.basename(path)}"
                )

            # Build success message
            success_msg = f"✓ Data exported successfully as CSV\n\n"
            success_msg += f"Main file:\n{path}\n"
            success_msg += f"Size: {file_size:,} bytes\n\n"

            if qa_path and os.path.exists(qa_path):
                success_msg += f"QA Report:\n{qa_path}\n\n"

            success_msg += "Note: CSV files open directly in Excel.\n"
            success_msg += "All your data is preserved and ready to use!"

            messagebox.showinfo("Export Successful", success_msg)

        except Exception as e:
            error_msg = f"Export failed: {str(e)}\n\n"
            error_msg += f"Attempted path: {path}\n\n"
            error_msg += "Please try:\n"
            error_msg += "1. Save to your Desktop or Documents folder\n"
            error_msg += "2. Make sure you have write permissions\n"
            error_msg += "3. Close any Excel files that might be using the same name"
            messagebox.showerror("Export Error", error_msg)
            print(f"Full export error: {e}")
            import traceback
            traceback.print_exc()

    # ───────────────────────────────────────────────────────
    #  SAVE CONFIG
    # ───────────────────────────────────────────────────────

    def _save_current_config(self):
        instruction = self._get_instruction()
        if not instruction:
            messagebox.showwarning("No Instruction", "Enter an instruction before saving a config.")
            return

        dialog = ctk.CTkInputDialog(text="Configuration name:", title="Save Config")
        name = dialog.get_input()
        if not name:
            return

        cols = list(self.df_input.columns) if self.df_input is not None else []
        parsed = parse_instruction(instruction, cols)

        history_db.save_config(
            name=name, description=instruction,
            instruction=instruction, pipeline=parsed.pipeline,
            source_columns=parsed.source_columns,
            target_mfg=parsed.target_mfg_col,
            target_pn=parsed.target_pn_col,
            add_sim=parsed.add_sim,
            sim_pattern=parsed.sim_pattern,
        )
        self.status_label.configure(text=f"✓ Config saved: {name}")


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    app = WescoMROParser()
    app.mainloop()


if __name__ == '__main__':
    main()
