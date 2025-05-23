"""
SuSi Analysis Tool
------------------
This tool loads and analyzes Sun Simulator (SuSi) data files.
It supports both single‐file and multiple‐file modes. For each file
the performance metrics (J_sc, V_oc, Efficiency, Fill Factor) are plotted,
as well as the I–V curves. The user can customize the plot appearance,
set filter ranges (including a voltage filter for I–V curves), group files
(if they are from the same device), and choose whether to separate forward
and reverse data on the x‑axis.

Author: Florian Kalaß
Date: 15.04.2025
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import os
import numpy as np

class SuSiAnalysisTool:
    def __init__(self, root):
        self.root = root
        self.root.title("SuSi Analysis Tool")
        self.root.state("zoomed")  # Fullscreen

        # --- Default Plot Options & Filter Options ---
        self.plot_options = {
            "axis_label_fontsize": 14,
            "tick_label_fontsize": 10,
            "marker_size": 8,
            "forward_marker": "o",
            "reverse_marker": "s",
            "forward_color": {"Jsc": "blue", "Voc": "red", "Efficiency": "green", "Fill Factor": "magenta"},
            "reverse_color": {"Jsc": "lightblue", "Voc": "tomato", "Efficiency": "limegreen", "Fill Factor": "violet"},
            "separate_forward_reverse": False,  # also toggled by the checkbox
            "x_spacing": 0.2,    # horizontal spacing (wspace)
            "y_spacing": 0.05    # vertical spacing (hspace)
        }
        # X-axis labels for performance subplots (customizable)
        self.plot_options["x_axis_labels"] = {"Jsc": "", "Voc": "", "Efficiency": "", "Fill Factor": "", "IV": "Voltage [V]"}
        # Subplot titles and Y-axis labels; if empty, no title is set.
        self.plot_options["subplot_titles"] = {"Jsc": "", "Voc": "", "Efficiency": "", "Fill Factor": "", "IV": ""}
        # Use LaTeX-style labels for J_sc and V_oc:
        self.plot_options["y_axis_labels"] = {"Jsc": r"$J_{sc}$ [mA/cm²]", "Voc": r"$V_{oc}$ [V]",
                                               "Efficiency": "Efficiency [%]", "Fill Factor": "Fill Factor [%]", "IV": "J [mA/cm²]"}
        self.plot_options["iv_line_style"] = {"Fwd": "-", "Rev": ":"}
        self.plot_options["iv_marker"] = {"Fwd": "o", "Rev": "s"}

        self.filter_options = {
            "Jsc": (-np.inf, np.inf),
            "Voc": (-np.inf, np.inf),
            "Efficiency": (0, 100),
            "Fill Factor": (0, 100),
            "Voltage": (-np.inf, np.inf)
        }

        # --- Additional toggle via checkbox for separate forward/reverse ---
        self.sep_fwd_rev_var = tk.BooleanVar(value=False)

        # For grouping files in multiple-file mode:
        self.group_mapping = {}  # Maps group name to list of file indices

        ##########################################
        # Build the GUI
        ##########################################
        self.setup_gui()

        ##########################################
        # Data Holders
        ##########################################
        self.data = None  # Single file mode: dict with keys "filename", "performance", "iv", "params"
        self.multi_data = []  # Multiple files: list of such dicts

    def setup_gui(self):
        # --- Top Controls Frame ---
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(fill="x", padx=10, pady=5)
        self.load_button = tk.Button(self.top_frame, text="Load Data File", command=self.load_file)
        self.load_button.pack(side=tk.LEFT, padx=5)
        self.load_multi_button = tk.Button(self.top_frame, text="Load Multiple Files", command=self.load_multiple_files)
        self.load_multi_button.pack(side=tk.LEFT, padx=5)
        self.group_button = tk.Button(self.top_frame, text="Group Files", command=self.open_group_window)
        self.group_button.pack(side=tk.LEFT, padx=5)
        self.file_path_var = tk.StringVar()
        self.file_path_entry = tk.Entry(self.top_frame, textvariable=self.file_path_var, state="readonly", width=80)
        self.file_path_entry.pack(side=tk.LEFT, padx=5)

        # --- Plot Title & Custom Labels ---
        self.title_frame = tk.Frame(self.root)
        self.title_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(self.title_frame, text="Plot Title:").pack(side=tk.LEFT, padx=5)
        self.plot_title_var = tk.StringVar()
        self.plot_title_entry = tk.Entry(self.title_frame, textvariable=self.plot_title_var, width=50)
        self.plot_title_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(self.title_frame, text="File Labels (comma-separated):").pack(side=tk.LEFT, padx=5)
        self.custom_labels_var = tk.StringVar()
        self.custom_labels_entry = tk.Entry(self.title_frame, textvariable=self.custom_labels_var, width=50)
        self.custom_labels_entry.pack(side=tk.LEFT, padx=5)

        # --- Buttons Frame ---
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(fill="x", padx=10, pady=5)
        self.generate_button = tk.Button(self.button_frame, text="Generate Plots", command=self.generate_plots)
        self.generate_button.pack(side=tk.LEFT, padx=5)
        self.save_button = tk.Button(self.button_frame, text="Save Plots", command=self.save_plots)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.customize_button = tk.Button(self.button_frame, text="Customize Plot", command=self.open_customization_window)
        self.customize_button.pack(side=tk.LEFT, padx=5)
        self.filter_button = tk.Button(self.button_frame, text="Filter Settings", command=self.open_filter_window)
        self.filter_button.pack(side=tk.LEFT, padx=5)
        # --- Moved Separate Fwd/Rev checkbox next to Filter Settings ---
        self.sep_checkbox = tk.Checkbutton(self.button_frame, text="Separate Fwd/Rev", variable=self.sep_fwd_rev_var)
        self.sep_checkbox.pack(side=tk.LEFT, padx=10)

        # --- Measurement Parameters Frame (Scrollable) ---
        self.params_frame_container = tk.Frame(self.root)
        self.params_frame_container.pack(fill="x", padx=10, pady=5)
        self.params_canvas = tk.Canvas(self.params_frame_container, height=120)
        self.params_scrollbar = tk.Scrollbar(self.params_frame_container, orient="vertical", command=self.params_canvas.yview)
        self.params_canvas.configure(yscrollcommand=self.params_scrollbar.set)
        self.params_canvas.pack(side=tk.LEFT, fill="x", expand=True)
        self.params_scrollbar.pack(side=tk.RIGHT, fill="y")
        self.params_inner_frame = tk.Frame(self.params_canvas)
        self.params_canvas.create_window((0, 0), window=self.params_inner_frame, anchor="nw")
        self.params_inner_frame.bind("<Configure>", lambda e: self.params_canvas.configure(scrollregion=self.params_canvas.bbox("all")))
        self.params_text = tk.Text(self.params_inner_frame, height=7, wrap=tk.WORD, state="disabled", relief="flat")
        self.params_text.pack(fill="x")

        # --- Plot Frame (Scrollable) ---
        self.plot_frame_container = tk.Frame(self.root)
        self.plot_canvas = tk.Canvas(self.plot_frame_container)
        self.plot_scrollbar = tk.Scrollbar(self.plot_frame_container, orient="vertical", command=self.plot_canvas.yview)
        self.plot_canvas.configure(yscrollcommand=self.plot_scrollbar.set)
        self.plot_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        self.plot_scrollbar.pack(side=tk.RIGHT, fill="y")
        self.plot_inner_frame = tk.Frame(self.plot_canvas)
        self.plot_canvas.create_window((0, 0), window=self.plot_inner_frame, anchor="nw")
        self.plot_inner_frame.bind("<Configure>", lambda e: self.plot_canvas.configure(scrollregion=self.plot_canvas.bbox("all")))

        # --- Matplotlib Figure Setup (using gridspec) ---
        self.fig = plt.figure(figsize=(18, 7.2))
        gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 1.5], height_ratios=[1, 1])
        self.ax_jsc = self.fig.add_subplot(gs[0, 0])
        self.ax_voc = self.fig.add_subplot(gs[0, 1])
        self.ax_eff = self.fig.add_subplot(gs[1, 0])
        self.ax_ff = self.fig.add_subplot(gs[1, 1])
        self.ax_iv = self.fig.add_subplot(gs[:, 2])
        self.fig.subplots_adjust(left=0.07, right=0.98, top=0.92, bottom=0.12,
                                 wspace=self.plot_options["x_spacing"],
                                 hspace=self.plot_options["y_spacing"])
        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_inner_frame)
        self.canvas.get_tk_widget().pack(padx=10, pady=10, fill="both", expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_inner_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.TOP, fill="x")

        # --- Mouse Wheel Bindings ---
        self.plot_canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.params_canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def on_mousewheel(self, event):
        delta = event.delta if hasattr(event, 'delta') else (120 if event.num == 4 else -120)
        if event.widget in (self.plot_canvas, self.plot_inner_frame):
            self.plot_canvas.yview_scroll(-1 * int(delta / 120), "units")
        elif event.widget in (self.params_canvas, self.params_inner_frame):
            self.params_canvas.yview_scroll(-1 * int(delta / 120), "units")

    def open_customization_window(self):
        win = tk.Toplevel(self.root)
        win.title("Customize Plot")
        win.geometry("850x700")
        main_frame = tk.Frame(win, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(main_frame)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        entries = {}
        section_frame = tk.LabelFrame(scroll_frame, text="General Plot Options", padx=10, pady=10)
        section_frame.grid(row=0, column=0, columnspan=8, sticky="ew", padx=5, pady=10)
        general_opts = [
            ("Axis Label Fontsize:", "axis_label_fontsize", self.plot_options["axis_label_fontsize"]),
            ("Tick Label Fontsize:", "tick_label_fontsize", self.plot_options["tick_label_fontsize"]),
            ("Marker Size:", "marker_size", self.plot_options["marker_size"]),
            ("Separate Fwd/Rev (True/False):", "separate_forward_reverse", self.plot_options["separate_forward_reverse"]),
            ("Horizontal Spacing (wspace):", "x_spacing", self.plot_options["x_spacing"]),
            ("Vertical Spacing (hspace):", "y_spacing", self.plot_options["y_spacing"])
        ]
        for i, (label_text, key, default_value) in enumerate(general_opts):
            row = i // 3
            col = (i % 3) * 2
            tk.Label(section_frame, text=label_text, anchor="e").grid(row=row, column=col, sticky="e", padx=5, pady=5)
            entry = tk.Entry(section_frame, width=15)
            entry.insert(0, str(default_value))
            entry.grid(row=row, column=col + 1, sticky="w", padx=5, pady=5)
            entries[(key, None)] = entry
        perf_frame = tk.LabelFrame(scroll_frame, text="Performance Options", padx=10, pady=10)
        perf_frame.grid(row=1, column=0, columnspan=8, sticky="ew", padx=5, pady=10)
        perf_params = ["Jsc", "Voc", "Efficiency", "Fill Factor"]
        perf_opts = [("Title:", "title"),
                     ("X-Label:", "xlabel"),
                     ("Y-Label:", "ylabel"),
                     ("Fwd Color:", "fcolor"),
                     ("Rev Color:", "rcolor"),
                     ("Fwd Marker:", "fmarker"),
                     ("Rev Marker:", "rmarker")]
        empty_label = tk.Label(perf_frame, text="", height=1)
        empty_label.grid(row=0, column=0)
        for j, param in enumerate(perf_params):
            header = tk.Label(perf_frame, text=param, font=("Arial", 9, "bold"))
            header.grid(row=1, column=j + 1, padx=5, pady=(0, 10), sticky="s")
        for i, (opt_text, subkey) in enumerate(perf_opts):
            row = i + 2
            tk.Label(perf_frame, text=opt_text, anchor="e").grid(row=row, column=0, sticky="e", padx=(5, 10), pady=5)
            for j, param in enumerate(perf_params):
                default = ""
                if subkey == "title":
                    default = self.plot_options["subplot_titles"].get(param, "")
                elif subkey == "xlabel":
                    default = self.plot_options["x_axis_labels"].get(param, "")
                elif subkey == "ylabel":
                    default = self.plot_options["y_axis_labels"].get(param, "")
                elif subkey == "fcolor":
                    default = self.plot_options["forward_color"].get(param, "")
                elif subkey == "rcolor":
                    default = self.plot_options["reverse_color"].get(param, "")
                elif subkey in ["fmarker", "rmarker"]:
                    default = self.plot_options["forward_marker"] if subkey == "fmarker" else self.plot_options["reverse_marker"]
                entry = tk.Entry(perf_frame, width=15)
                entry.insert(0, str(default))
                entry.grid(row=row, column=j + 1, padx=5, pady=5, sticky="w")
                entries[(param, subkey)] = entry
        iv_frame = tk.LabelFrame(scroll_frame, text="I-V Options", padx=10, pady=10)
        iv_frame.grid(row=2, column=0, columnspan=8, sticky="ew", padx=5, pady=10)
        iv_opts = [("Subplot Title:", "title"),
                   ("X-Axis Label:", "xlabel"),
                   ("Y-Axis Label:", "ylabel"),
                   ("Fwd Line Style:", "f_linestyle"),
                   ("Rev Line Style:", "r_linestyle"),
                   ("Fwd Marker:", "f_marker"),
                   ("Rev Marker:", "r_marker")]
        for i, (opt_text, subkey) in enumerate(iv_opts):
            tk.Label(iv_frame, text=f"I-V {opt_text}", anchor="e").grid(row=i, column=0, sticky="e", padx=5, pady=5)
            default = ""
            if subkey == "title":
                default = self.plot_options["subplot_titles"].get("IV", "")
            elif subkey == "xlabel":
                default = self.plot_options["x_axis_labels"].get("IV", "Voltage [V]")
            elif subkey == "ylabel":
                default = self.plot_options["y_axis_labels"].get("IV", "J [mA/cm²]")
            elif subkey in ["f_linestyle", "r_linestyle"]:
                default = self.plot_options["iv_line_style"].get("Fwd" if subkey == "f_linestyle" else "Rev",
                                                                 "-" if subkey == "f_linestyle" else ":")
            elif subkey in ["f_marker", "r_marker"]:
                default = self.plot_options["iv_marker"].get("Fwd" if subkey == "f_marker" else "Rev",
                                                             "o" if subkey == "f_marker" else "s")
            entry = tk.Entry(iv_frame, width=15)
            entry.insert(0, str(default))
            entry.grid(row=i, column=1, sticky="w", padx=5, pady=5)
            entries[("IV", subkey)] = entry
        button_frame = tk.Frame(scroll_frame)
        button_frame.grid(row=3, column=0, columnspan=8, pady=15)
        def apply_custom():
            try:
                self.plot_options["axis_label_fontsize"] = int(entries[("axis_label_fontsize", None)].get())
                self.plot_options["tick_label_fontsize"] = int(entries[("tick_label_fontsize", None)].get())
                self.plot_options["marker_size"] = int(entries[("marker_size", None)].get())
                sep_val = entries[("separate_forward_reverse", None)].get().strip().lower()
                self.plot_options["separate_forward_reverse"] = (sep_val == "true")
                self.plot_options["x_spacing"] = float(entries[("x_spacing", None)].get())
                self.plot_options["y_spacing"] = float(entries[("y_spacing", None)].get())
                for param in ["Jsc", "Voc", "Efficiency", "Fill Factor"]:
                    self.plot_options["subplot_titles"][param] = entries[(param, "title")].get().strip()
                    self.plot_options["x_axis_labels"][param] = entries[(param, "xlabel")].get().strip()
                    self.plot_options["y_axis_labels"][param] = entries[(param, "ylabel")].get().strip()
                    self.plot_options["forward_color"][param] = entries[(param, "fcolor")].get().strip()
                    self.plot_options["reverse_color"][param] = entries[(param, "rcolor")].get().strip()
                    self.plot_options["forward_marker"] = entries[(param, "fmarker")].get().strip()
                    self.plot_options["reverse_marker"] = entries[(param, "rmarker")].get().strip()
                self.plot_options["subplot_titles"]["IV"] = entries[("IV", "title")].get().strip()
                self.plot_options["x_axis_labels"]["IV"] = entries[("IV", "xlabel")].get().strip()
                self.plot_options["y_axis_labels"]["IV"] = entries[("IV", "ylabel")].get().strip()
                self.plot_options["iv_line_style"]["Fwd"] = entries[("IV", "f_linestyle")].get().strip()
                self.plot_options["iv_line_style"]["Rev"] = entries[("IV", "r_linestyle")].get().strip()
                self.plot_options["iv_marker"]["Fwd"] = entries[("IV", "f_marker")].get().strip()
                self.plot_options["iv_marker"]["Rev"] = entries[("IV", "r_marker")].get().strip()
                self.fig.subplots_adjust(wspace=self.plot_options["x_spacing"],
                                         hspace=self.plot_options["y_spacing"])
                messagebox.showinfo("Success", "Customization updated.")
                win.destroy()
            except Exception as ex:
                messagebox.showerror("Error", f"Invalid input: {ex}")
        tk.Button(button_frame, text="Apply", command=apply_custom, width=10).pack()
        win.focus_force()

    def open_group_window(self):
        if not self.multi_data:
            messagebox.showinfo("Info", "Load multiple files first.")
            return
        win = tk.Toplevel(self.root)
        win.title("Group and Order Files")
        win.geometry("550x400")

        tk.Label(win, text="Rename and order files into groups (same name → combined):", wraplength=520) \
            .pack(padx=10, pady=10)
        frame = tk.Frame(win)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        name_vars = []
        order_vars = []
        for idx, entry in enumerate(self.multi_data):
            row = tk.Frame(frame)
            row.grid(row=idx, column=0, sticky="w", pady=2)

            # Show original filename
            tk.Label(row, text=f"File {idx + 1}: {entry['filename']}").pack(side="left")

            # Editable group name
            nv = tk.StringVar(value=entry.get('group', entry['filename']))
            name_vars.append(nv)
            tk.Entry(row, textvariable=nv, width=20).pack(side="left", padx=5)

            # Spinbox for explicit ordering
            ov = tk.IntVar(value=idx + 1)
            order_vars.append(ov)
            tk.Spinbox(row, from_=1, to=len(self.multi_data), textvariable=ov, width=4).pack(side="left")

        def apply_grouping():
            # 1) Collect and sort by order
            items = [(order_vars[i].get(), name_vars[i].get().strip(), i)
                     for i in range(len(self.multi_data))]
            items.sort(key=lambda x: x[0])

            # 2) Group identical names (in sorted order)
            from collections import OrderedDict
            grouped = OrderedDict()
            for _, name, orig_idx in items:
                grouped.setdefault(name, []).append(orig_idx)

            # 3) Build new multi_data with combined DataFrames
            new_multi = []
            for name, indices in grouped.items():
                # Combine performance
                perf_list = [self.multi_data[i]['performance'] for i in indices]
                combined_perf = pd.concat(perf_list, axis=1)
                # Combine IV if exists
                iv_list = [self.multi_data[i].get('iv') for i in indices if self.multi_data[i].get('iv') is not None]
                combined_iv = pd.concat(iv_list, axis=1) if iv_list else None
                if combined_iv is not None and combined_iv.shape[1] == 1:
                    combined_iv = pd.concat([combined_iv, combined_iv], axis=1)
                new_multi.append({
                    'filename': name,
                    'performance': combined_perf,
                    'iv': combined_iv
                })

            self.multi_data = new_multi
            # Sync the custom labels string
            self.custom_labels_var.set(",".join([d['filename'] for d in new_multi]))

            messagebox.showinfo("Success", "Grouping and ordering applied.")
            win.destroy()
            self.generate_plots()

        tk.Button(win, text="Apply Grouping", command=apply_grouping).pack(pady=10)
        win.focus_force()

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_path:
            return
        # Clear multiple file data
        self.multi_data = []
        self.file_path_var.set(file_path)
        try:
            with open(file_path, "r", encoding="latin1") as f:
                lines = f.readlines()
            parameters = []
            for line in lines:
                parameters.append(line.strip())
                if "compliance" in line.lower():
                    break
            self.params_text.config(state="normal")
            self.params_text.delete("1.0", tk.END)
            self.params_text.insert(tk.END, "\n".join(parameters))
            self.params_text.config(state="disabled")
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            self.plot_title_var.set(base_name)
            start_idx = len(parameters) + 1
            full_data = pd.read_csv(file_path, sep="\t", skiprows=start_idx, encoding="latin1",
                                    engine="python", on_bad_lines='skip')
            data_numeric = full_data.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
            data_numeric = data_numeric.drop(data_numeric.columns[0], axis=1)
            if data_numeric.shape[1] % 2 != 0:
                data_numeric = data_numeric.iloc[:, :-1]
            print(f"Loaded performance data with {data_numeric.shape[1]} columns.")
            iv_start = None
            for i, line in enumerate(lines):
                if line.strip().startswith("Voltage"):
                    iv_start = i
                    break
            if iv_start is not None:
                try:
                    iv_data = pd.read_csv(file_path, sep="\t", skiprows=iv_start+2, encoding="latin1",
                                          engine="python", on_bad_lines='skip')
                except pd.errors.EmptyDataError:
                    iv_data = None
                if iv_data is not None and not iv_data.empty:
                    if iv_data.shape[1] % 2 != 0:
                        iv_data = iv_data.iloc[:, :-1]
                else:
                    iv_data = None
            else:
                iv_data = None
            self.data = {"filename": base_name, "performance": data_numeric, "iv": iv_data,
                         "params": "\n".join(parameters)}
            print("Single file loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def load_multiple_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_paths:
            return
        self.multi_data = []
        self.group_mapping = {}  # reset grouping on new load
        all_params = []
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="latin1") as f:
                    lines = f.readlines()
                parameters = []
                for line in lines:
                    parameters.append(line.strip())
                    if "compliance" in line.lower():
                        break
                active_area = None
                for line in lines:
                    if "active area" in line.lower():
                        parts = line.split(":")
                        if len(parts) > 1:
                            active_area = parts[1].strip()
                        break
                start_idx = len(parameters) + 2
                try:
                    perf = pd.read_csv(file_path, sep="\t", skiprows=start_idx, encoding="latin1",
                                       engine="python", on_bad_lines='skip')
                except pd.errors.EmptyDataError:
                    continue
                if perf.empty or len(perf.columns) == 0:
                    continue
                perf = perf.drop(perf.columns[0], axis=1)
                if perf.shape[1] % 2 != 0:
                    perf = perf.iloc[:, :-1]
                iv_start = None
                for i, line in enumerate(lines):
                    if line.strip().startswith("Voltage"):
                        iv_start = i
                        break
                if iv_start is not None:
                    try:
                        iv = pd.read_csv(file_path, sep="\t", skiprows=iv_start+2, encoding="latin1",
                                         engine="python", on_bad_lines='skip')
                    except pd.errors.EmptyDataError:
                        iv = None
                    if iv is not None and not iv.empty:
                        if iv.shape[1] % 2 != 0:
                            iv = iv.iloc[:, :-1]
                    else:
                        iv = None
                else:
                    iv = None
                filename = os.path.splitext(os.path.basename(file_path))[0]
                self.multi_data.append({
                    "filename": filename,
                    "performance": perf,
                    "iv": iv,
                    "active_area": active_area,
                    "params": "\n".join(parameters)
                })
                all_params.append(f"{filename}:\n" + "\n".join(parameters))
                print(f"Loaded file: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load {file_path}: {e}")
        if self.multi_data:
            self.plot_title_var.set("Comparison Plot")
            default_labels = [d["filename"] for d in self.multi_data]
            self.custom_labels_var.set(",".join(default_labels))
            combined_params = "\n\n---\n\n".join(all_params)
            self.params_text.config(state="normal")
            self.params_text.delete("1.0", tk.END)
            self.params_text.insert(tk.END, combined_params)
            self.params_text.config(state="disabled")
            print("Multiple files loaded successfully!")

    def generate_plots(self):
        if self.multi_data:
            self.generate_plots_multiple()
        elif self.data is not None:
            self.generate_plots_single()
        else:
            messagebox.showerror("Error", "No data loaded!")
            return
        if not self.plot_frame_container.winfo_ismapped():
            self.plot_frame_container.pack(fill="both", expand=True, padx=10, pady=5)
        self.canvas.draw()

    def open_filter_window(self):
        win = tk.Toplevel(self.root)
        win.title("Filter Settings")
        def create_filter_row(param, default_range, row):
            tk.Label(win, text=f"{param} range (min,max):").grid(row=row, column=0, sticky="w", padx=5, pady=5)
            entry = tk.Entry(win, width=20)
            entry.insert(0, f"{default_range[0]},{default_range[1]}")
            entry.grid(row=row, column=1, padx=5, pady=5)
            return entry
        entry_jsc = create_filter_row("Jsc", self.filter_options["Jsc"], 0)
        entry_voc = create_filter_row("Voc", self.filter_options["Voc"], 1)
        entry_eff = create_filter_row("Efficiency", self.filter_options["Efficiency"], 2)
        entry_ff = create_filter_row("Fill Factor", self.filter_options["Fill Factor"], 3)
        entry_volt = create_filter_row("Voltage", self.filter_options["Voltage"], 4)
        def apply_filters():
            try:
                for param, entry in zip(["Jsc", "Voc", "Efficiency", "Fill Factor", "Voltage"],
                                        [entry_jsc, entry_voc, entry_eff, entry_ff, entry_volt]):
                    parts = entry.get().split(',')
                    if len(parts) != 2:
                        raise ValueError(f"Invalid range for {param}")
                    self.filter_options[param] = (float(parts[0]), float(parts[1]))
                messagebox.showinfo("Success", "Filter settings updated.")
                win.destroy()
                self.generate_plots()
            except Exception as ex:
                messagebox.showerror("Error", f"Invalid input: {ex}")
        tk.Button(win, text="Apply Filters", command=apply_filters).grid(row=5, column=0, columnspan=2, pady=10)

    def generate_plots_single(self):
        # Single-file mode works as before.
        perf = self.data["performance"].apply(pd.to_numeric, errors="coerce")
        num_columns = perf.shape[1]
        if num_columns % 2 != 0:
            perf = perf.iloc[:, :num_columns - 1]
            num_columns = perf.shape[1]
        # ASSUMPTION: Row order: 0:J_sc, 1:V_oc, 2:Fill Factor, 3:Efficiency
        if num_columns == 1:
            x_positions = np.array([1])
            pixel_labels = ["Pixel 1"]
            jsc_fwd = np.array([perf.iloc[0, 0]])
            voc_fwd = np.array([perf.iloc[1, 0]])
            ff_fwd = np.array([perf.iloc[2, 0]])
            eff_fwd = np.array([perf.iloc[3, 0]])
        else:
            if self.plot_options["separate_forward_reverse"] or self.sep_fwd_rev_var.get():
                num_pixels = num_columns // 2
                offset = 0.2
                x_positions_fwd = np.array([i + 1 for i in range(num_pixels)])
                x_positions_rev = x_positions_fwd + offset
                major_ticks = (x_positions_fwd + x_positions_rev) / 2
                pixel_labels = [f"P{i + 1}" for i in range(num_pixels)]
                jsc = perf.iloc[0, :].values
                voc = perf.iloc[1, :].values
                ff = perf.iloc[2, :].values
                eff = perf.iloc[3, :].values
                # If only one pixel exists, duplicate it.
                if len(jsc) == 1:
                    jsc_fwd, jsc_rev = jsc, jsc
                    voc_fwd, voc_rev = voc, voc
                    ff_fwd, ff_rev = ff, ff
                    eff_fwd, eff_rev = eff, eff
                    x_positions_fwd = np.array([1])
                    x_positions_rev = np.array([1])
                    major_ticks = np.array([1])
                    pixel_labels = ["Pixel 1"]
                else:
                    jsc_fwd = jsc[::2]
                    jsc_rev = jsc[1::2]
                    voc_fwd = voc[::2]
                    voc_rev = voc[1::2]
                    ff_fwd = ff[::2]
                    ff_rev = ff[1::2]
                    eff_fwd = eff[::2]
                    eff_rev = eff[1::2]
            else:
                num_pixels = num_columns // 2
                x_positions = np.arange(1, num_pixels + 1)
                pixel_labels = [f"Pixel {i}" for i in x_positions]
                jsc_fwd = perf.iloc[0, ::2].values
                jsc_rev = perf.iloc[0, 1::2].values
                voc_fwd = perf.iloc[1, ::2].values
                voc_rev = perf.iloc[1, 1::2].values
                ff_fwd = perf.iloc[2, ::2].values
                ff_rev = perf.iloc[2, 1::2].values
                eff_fwd = perf.iloc[3, ::2].values
                eff_rev = perf.iloc[3, 1::2].values

        def apply_filter(values, param):
            low, high = self.filter_options.get(param, (-np.inf, np.inf))
            values = np.array(values, dtype=float)
            values[(values < low) | (values > high)] = np.nan
            return values

        jsc_fwd = apply_filter(jsc_fwd, "Jsc")
        jsc_rev = apply_filter(jsc_rev, "Jsc")
        voc_fwd = apply_filter(voc_fwd, "Voc")
        voc_rev = apply_filter(voc_rev, "Voc")
        ff_fwd = apply_filter(ff_fwd, "Fill Factor")
        ff_rev = apply_filter(ff_rev, "Fill Factor")
        eff_fwd = apply_filter(eff_fwd, "Efficiency")
        eff_rev = apply_filter(eff_rev, "Efficiency")

        for ax in [self.ax_jsc, self.ax_voc, self.ax_eff, self.ax_ff, self.ax_iv]:
            ax.clear()

        ms = self.plot_options["marker_size"]

        if self.plot_options["separate_forward_reverse"] or self.sep_fwd_rev_var.get():
            self.ax_jsc.set_ylabel(self.plot_options["y_axis_labels"].get("Jsc"))
            self.ax_jsc.set_xticks(major_ticks)
            self.ax_jsc.set_xticklabels([])  # No tick labels for Jsc
            self.ax_jsc.scatter(x_positions_fwd, jsc_fwd, marker=self.plot_options["forward_marker"],
                                s=ms * 10, color=self.plot_options["forward_color"].get("Jsc", "blue"), label="Fwd")
            self.ax_jsc.scatter(x_positions_rev, jsc_rev, marker=self.plot_options["reverse_marker"],
                                s=ms * 10, color=self.plot_options["reverse_color"].get("Jsc", "red"), label="Rev")
            self.ax_jsc.legend()
            self.ax_jsc.grid(True)

            self.ax_voc.set_ylabel(self.plot_options["y_axis_labels"].get("Voc"))
            self.ax_voc.set_xticks(major_ticks)
            self.ax_voc.set_xticklabels([])  # No tick labels for Voc
            self.ax_voc.scatter(x_positions_fwd, voc_fwd, marker=self.plot_options["forward_marker"],
                                s=ms * 10, color=self.plot_options["forward_color"].get("Voc", "blue"), label="Fwd")
            self.ax_voc.scatter(x_positions_rev, voc_rev, marker=self.plot_options["reverse_marker"],
                                s=ms * 10, color=self.plot_options["reverse_color"].get("Voc", "red"), label="Rev")
            self.ax_voc.legend()
            self.ax_voc.grid(True)

            # For Efficiency and Fill Factor, plot boxplots for each file's forward and reverse data
            self.ax_eff.set_ylabel(self.plot_options["y_axis_labels"].get("Efficiency"))
            self.ax_eff.set_xticks(major_ticks)
            self.ax_eff.set_xticklabels(pixel_labels, rotation=45, ha='right')

            # Create proxy artists for the boxplot legend
            box_fwd_patch = mpatches.Patch(color=self.plot_options["forward_color"].get("Efficiency", "blue"),
                                           fill=False, label='Fwd')
            box_rev_patch = mpatches.Patch(color=self.plot_options["reverse_color"].get("Efficiency", "red"),
                                           fill=False, label='Rev')
            orange_line = mlines.Line2D([], [], color='orange', marker='_', linestyle='None',
                                        markersize=10, label='Median')

            for i in range(len(eff_fwd)):
                # Create arrays with non-NaN values only for boxplots
                eff_fwd_filtered = eff_fwd[i:i + 1]
                eff_fwd_filtered = eff_fwd_filtered[~np.isnan(eff_fwd_filtered)]
                eff_rev_filtered = eff_rev[i:i + 1]
                eff_rev_filtered = eff_rev_filtered[~np.isnan(eff_rev_filtered)]

                # Only create boxplot if there are valid values
                if len(eff_fwd_filtered) > 0:
                    self.ax_eff.boxplot([eff_fwd_filtered], positions=[x_positions_fwd[i]], widths=0.1,
                                        patch_artist=True,
                                        boxprops=dict(facecolor='none',
                                                      color=self.plot_options["forward_color"].get("Efficiency",
                                                                                                   "blue")),
                                        medianprops=dict(color='orange'))

                if len(eff_rev_filtered) > 0:
                    self.ax_eff.boxplot([eff_rev_filtered], positions=[x_positions_rev[i]], widths=0.1,
                                        patch_artist=True,
                                        boxprops=dict(facecolor='none',
                                                      color=self.plot_options["reverse_color"].get("Efficiency",
                                                                                                   "red")),
                                        medianprops=dict(color='orange'))

            # Add legend for the boxplots
            self.ax_eff.legend(handles=[box_fwd_patch, box_rev_patch, orange_line], loc='upper left')
            self.ax_eff.grid(False)

            self.ax_ff.set_ylabel(self.plot_options["y_axis_labels"].get("Fill Factor"))
            self.ax_ff.set_xticks(major_ticks)
            self.ax_ff.set_xticklabels(pixel_labels, rotation=45, ha='right')

            # Create proxy artists for the boxplot legend (Fill Factor)
            box_fwd_patch_ff = mpatches.Patch(color=self.plot_options["forward_color"].get("Fill Factor", "blue"),
                                              fill=False, label='Fwd')
            box_rev_patch_ff = mpatches.Patch(color=self.plot_options["reverse_color"].get("Fill Factor", "red"),
                                              fill=False, label='Rev')

            for i in range(len(ff_fwd)):
                # Create arrays with non-NaN values only for boxplots
                ff_fwd_filtered = ff_fwd[i:i + 1]
                ff_fwd_filtered = ff_fwd_filtered[~np.isnan(ff_fwd_filtered)]
                ff_rev_filtered = ff_rev[i:i + 1]
                ff_rev_filtered = ff_rev_filtered[~np.isnan(ff_rev_filtered)]

                # Only create boxplot if there are valid values
                if len(ff_fwd_filtered) > 0:
                    self.ax_ff.boxplot([ff_fwd_filtered], positions=[x_positions_fwd[i]], widths=0.1,
                                       patch_artist=True,
                                       boxprops=dict(facecolor='none',
                                                     color=self.plot_options["forward_color"].get("Fill Factor",
                                                                                                  "blue")),
                                       medianprops=dict(color='orange'))

                if len(ff_rev_filtered) > 0:
                    self.ax_ff.boxplot([ff_rev_filtered], positions=[x_positions_rev[i]], widths=0.1,
                                       patch_artist=True,
                                       boxprops=dict(facecolor='none',
                                                     color=self.plot_options["reverse_color"].get("Fill Factor",
                                                                                                  "red")),
                                       medianprops=dict(color='orange'))

            # Add legend for Fill Factor boxplots
            self.ax_ff.legend(handles=[box_fwd_patch_ff, box_rev_patch_ff, orange_line], loc='upper left')
            self.ax_ff.grid(True)
        else:
            x_positions = np.arange(1, num_pixels + 1)
            pixel_labels = [f"Pixel {i}" for i in x_positions]
            self.ax_jsc.set_ylabel(self.plot_options["y_axis_labels"]["Jsc"])
            self.ax_jsc.set_xticks(x_positions)
            self.ax_jsc.set_xticklabels([])  # No tick labels for Jsc
            self.ax_jsc.scatter(x_positions, jsc_fwd, marker=self.plot_options["forward_marker"],
                                s=ms * 10, color=self.plot_options["forward_color"]["Jsc"], label="Fwd")
            self.ax_jsc.scatter(x_positions, jsc_rev, marker=self.plot_options["reverse_marker"],
                                s=ms * 10, color=self.plot_options["reverse_color"]["Jsc"], label="Rev")
            self.ax_jsc.legend()
            self.ax_jsc.grid(True)

            self.ax_voc.set_ylabel(self.plot_options["y_axis_labels"]["Voc"])
            self.ax_voc.set_xticks(x_positions)
            self.ax_voc.set_xticklabels([])  # No tick labels for Voc
            self.ax_voc.scatter(x_positions, voc_fwd, marker=self.plot_options["forward_marker"],
                                s=ms * 10, color=self.plot_options["forward_color"]["Voc"], label="Fwd")
            self.ax_voc.scatter(x_positions, voc_rev, marker=self.plot_options["reverse_marker"],
                                s=ms * 10, color=self.plot_options["reverse_color"]["Voc"], label="Rev")
            self.ax_voc.legend()
            self.ax_voc.grid(False)

            self.ax_eff.set_ylabel(self.plot_options["y_axis_labels"]["Efficiency"])
            self.ax_eff.set_xticks(x_positions)
            self.ax_eff.set_xticklabels(pixel_labels, rotation=45, ha='right')
            self.ax_eff.scatter(x_positions, eff_fwd, marker=self.plot_options["forward_marker"],
                                s=ms * 10, color=self.plot_options["forward_color"]["Efficiency"], label="Fwd")
            self.ax_eff.scatter(x_positions, eff_rev, marker=self.plot_options["reverse_marker"],
                                s=ms * 10, color=self.plot_options["reverse_color"]["Efficiency"], label="Rev")
            self.ax_eff.legend()
            self.ax_eff.grid(False)

            self.ax_ff.set_ylabel(self.plot_options["y_axis_labels"]["Fill Factor"])
            self.ax_ff.set_xticks(x_positions)
            self.ax_ff.set_xticklabels(pixel_labels, rotation=45, ha='right')
            self.ax_ff.scatter(x_positions, ff_fwd, marker=self.plot_options["forward_marker"],
                               s=ms * 10, color=self.plot_options["forward_color"]["Fill Factor"], label="Fwd")
            self.ax_ff.scatter(x_positions, ff_rev, marker=self.plot_options["reverse_marker"],
                               s=ms * 10, color=self.plot_options["reverse_color"]["Fill Factor"], label="Rev")
            self.ax_ff.legend()
            self.ax_ff.grid(False)

        # I-V curves (Single File mode)
        self.ax_iv.clear()
        if self.data.get("iv") is not None:
            iv = self.data["iv"].apply(pd.to_numeric, errors="coerce")
            voltage = iv.iloc[:, 0]
            vlow, vhigh = self.filter_options["Voltage"]
            mask = (voltage >= vlow) & (voltage <= vhigh)
            voltage = voltage[mask]
            num_iv_cols = iv.shape[1]
            colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'magenta', 'brown', 'pink', 'gray', 'olive',
                      'teal']
            if num_iv_cols == 2:
                y_data = iv.iloc[:, 1][mask]
                self.ax_iv.plot(voltage, y_data,
                                linestyle=self.plot_options["iv_line_style"]["Fwd"],
                                marker=self.plot_options["iv_marker"]["Fwd"],
                                markersize=4, color=colors[0],
                                label="Pixel 1 (Fwd)")
            elif num_iv_cols >= 3:
                # Calculate the actual number of curves to plot
                num_iv_curves = (num_iv_cols - 1)
                if num_iv_curves < 1:
                    num_iv_curves = 1

                for i in range(1, num_iv_cols):
                    if i % 2 == 1:  # Forward curve
                        pixel_num = (i // 2) + 1
                        y_data = iv.iloc[:, i][mask]
                        self.ax_iv.plot(voltage, y_data,
                                        linestyle=self.plot_options["iv_line_style"]["Fwd"],
                                        marker=self.plot_options["iv_marker"]["Fwd"],
                                        markersize=4, color=colors[(pixel_num - 1) % len(colors)],
                                        label=f"Pixel {pixel_num} (Fwd)")
                    else:  # Reverse curve
                        pixel_num = (i // 2)
                        y_data = iv.iloc[:, i][mask]
                        self.ax_iv.plot(voltage, y_data,
                                        linestyle=self.plot_options["iv_line_style"]["Rev"],
                                        marker=self.plot_options["iv_marker"]["Rev"],
                                        markersize=4, color=colors[(pixel_num - 1) % len(colors)],
                                        label=f"Pixel {pixel_num} (Rev)")
            self.ax_iv.set_xlabel(self.plot_options["x_axis_labels"].get("IV", "Voltage [V]"))
            self.ax_iv.set_ylabel(self.plot_options["y_axis_labels"].get("IV", "J [mA/cm²]"))
            self.ax_iv.legend(loc='upper left')
            self.ax_iv.grid(False)
        else:
            self.ax_iv.set_title("No I-V Data")
        self.fig.suptitle("Comparison Plot", fontsize=16, y=0.98)
        self.canvas.draw()

    def generate_plots_multiple(self):
        try:
            # Extract custom labels or use filenames
            custom = self.custom_labels_var.get().strip()
            if custom:
                labels = [lab.strip() for lab in custom.split(",")]
                if len(labels) != len(self.multi_data):
                    messagebox.showerror("Error", "Number of custom labels must match number of files!")
                    return
            else:
                labels = [d["filename"] for d in self.multi_data]

            # --- Grouping Section (if applicable) ---
            if self.group_mapping:
                grouped = {}
                for group, indices in self.group_mapping.items():
                    group_perf = [self.multi_data[i]["performance"] for i in indices]
                    combined_perf = pd.concat(group_perf, axis=1)
                    grouped[group] = {"performance": combined_perf, "iv": None}
                    group_iv_list = [self.multi_data[i]["iv"] for i in indices if self.multi_data[i]["iv"] is not None]
                    if group_iv_list:
                        iv_combined = pd.concat(group_iv_list, axis=1)
                        if iv_combined.shape[1] == 1:
                            iv_combined = pd.concat([iv_combined, iv_combined], axis=1)
                        grouped[group]["iv"] = iv_combined
                labels = list(grouped.keys())
                new_multi = []
                for group, d in grouped.items():
                    new_multi.append({"filename": group, "performance": d["performance"], "iv": d["iv"]})
                self.multi_data = new_multi
                self.custom_labels_var.set(",".join(labels))
                self.group_mapping = {}

            # --- Prepare Performance Data Arrays ---
            jsc_data, voc_data, ff_data, eff_data = [], [], [], []
            iv_curves = []
            for d in self.multi_data:
                perf = d["performance"].apply(pd.to_numeric, errors="coerce")
                # Expected row order: 0: J_sc, 1: V_oc, 2: Fill Factor, 3: Efficiency
                try:
                    jsc_vals = perf.iloc[0, :].values.astype(float)
                    voc_vals = perf.iloc[1, :].values.astype(float)
                    ff_vals = perf.iloc[2, :].values.astype(float)
                    eff_vals = perf.iloc[3, :].values.astype(float)
                except Exception as ex:
                    print(f"Warning: Could not extract performance metrics from file {d['filename']}: {ex}")
                    continue
                jsc_data.append(jsc_vals)
                voc_data.append(voc_vals)
                ff_data.append(ff_vals)
                eff_data.append(eff_vals)

                # Process IV curves
                if d.get("iv") is not None:
                    iv = d["iv"].apply(pd.to_numeric, errors="coerce") if isinstance(d["iv"], pd.DataFrame) else d["iv"]
                    if isinstance(iv, pd.DataFrame):
                        voltage = iv.iloc[:, 0]
                        vlow, vhigh = self.filter_options["Voltage"]
                        mask = (voltage >= vlow) & (voltage <= vhigh)
                        voltage = voltage[mask]
                        num_iv_cols = iv.shape[1]
                        colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'magenta', 'brown', 'pink',
                                  'gray']
                        if num_iv_cols == 2:
                            y_data = iv.iloc[:, 1][mask]
                            iv_curves.append((voltage, y_data, d["filename"]))
                        elif num_iv_cols >= 3:
                            pixel_index = 0  # Use first available pixel pair
                            col_fwd = 2 * pixel_index + 1
                            fwd = iv.iloc[:, col_fwd][mask] if col_fwd < num_iv_cols else None
                            col_rev = col_fwd + 1
                            rev = iv.iloc[:, col_rev][mask] if col_rev < num_iv_cols else None
                            iv_curves.append((voltage, (fwd, rev), d["filename"]))
                        else:
                            iv_curves.append((None, None, d["filename"]))
                    else:
                        iv_curves.append((None, None, d["filename"]))
                else:
                    iv_curves.append((None, None, d["filename"]))

            # --- Define Local Filtering Function ---
            def apply_filter(values, param):
                low, high = self.filter_options.get(param, (-np.inf, np.inf))
                values = np.array(values, dtype=float)
                values[(values < low) | (values > high)] = np.nan
                return values

            # Apply filters to all data arrays
            jsc_data = [apply_filter(arr, "Jsc") for arr in jsc_data]
            voc_data = [apply_filter(arr, "Voc") for arr in voc_data]
            ff_data = [apply_filter(arr, "Fill Factor") for arr in ff_data]
            eff_data = [apply_filter(arr, "Efficiency") for arr in eff_data]

            # --- Clear Previous Plots ---
            for ax in [self.ax_jsc, self.ax_voc, self.ax_eff, self.ax_ff, self.ax_iv]:
                ax.clear()

            ms = self.plot_options["marker_size"]

            # --- Plot Performance Metrics ---
            if self.plot_options["separate_forward_reverse"] or self.sep_fwd_rev_var.get():
                offset = 0.2
                nfiles = len(self.multi_data)
                x_positions_fwd = np.array([i + 1 for i in range(nfiles)])
                x_positions_rev = x_positions_fwd + offset

                # J_sc Plot: annotate medians and hide x tick labels.
                for i, data in enumerate(jsc_data):
                    if data is None or len(data) == 0:
                        continue
                    if len(data) % 2 != 0:
                        data = data[:-1]
                    fwd = data[::2]
                    rev = data[1::2]

                    # Filter NaN values for boxplots
                    fwd_filtered = fwd[~np.isnan(fwd)]
                    rev_filtered = rev[~np.isnan(rev)]

                    # Get colors for data points (same as what boxes previously had)
                    fwd_color = self.plot_options["forward_color"].get("Jsc", "blue")
                    rev_color = self.plot_options["reverse_color"].get("Jsc", "red")

                    if len(fwd_filtered) > 0:
                        self.ax_jsc.boxplot([fwd_filtered], positions=[x_positions_fwd[i]], widths=0.1,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_jsc.scatter(np.full(len(fwd_filtered), x_positions_fwd[i]), fwd_filtered,
                                            s=20, color=fwd_color, alpha=0.6)
                        med_fwd = np.nanmedian(fwd_filtered)  # Use filtered data for median
                        if not np.isnan(med_fwd) and len(fwd_filtered) > 0:
                            self.ax_jsc.text(x_positions_fwd[i] + 0.12, med_fwd, f"{med_fwd:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")

                    if len(rev_filtered) > 0:
                        self.ax_jsc.boxplot([rev_filtered], positions=[x_positions_rev[i]], widths=0.1,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_jsc.scatter(np.full(len(rev_filtered), x_positions_rev[i]), rev_filtered,
                                            s=20, color=rev_color, alpha=0.6)
                        med_rev = np.nanmedian(rev_filtered)  # Use filtered data for median
                        if not np.isnan(med_rev) and len(rev_filtered) > 0:
                            self.ax_jsc.text(x_positions_rev[i] + 0.12, med_rev, f"{med_rev:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")

                self.ax_jsc.set_xticks(x_positions_fwd)  # Ticks present but no labels
                self.ax_jsc.set_xticklabels([])
                self.ax_jsc.set_ylabel(self.plot_options["y_axis_labels"].get("Jsc", r"$J_{sc}$ [mA/cm²]"))
                self.ax_jsc.grid(False)  # Turn off grid

                # V_oc Plot: annotate medians and hide x tick labels.
                for i, data in enumerate(voc_data):
                    if data is None or len(data) == 0:
                        continue
                    if len(data) % 2 != 0:
                        data = data[:-1]
                    fwd = data[::2]
                    rev = data[1::2]

                    # Filter NaN values for boxplots
                    fwd_filtered = fwd[~np.isnan(fwd)]
                    rev_filtered = rev[~np.isnan(rev)]

                    # Get colors for data points (same as what boxes previously had)
                    fwd_color = self.plot_options["forward_color"].get("Voc", "blue")
                    rev_color = self.plot_options["reverse_color"].get("Voc", "red")

                    if len(fwd_filtered) > 0:
                        self.ax_voc.boxplot([fwd_filtered], positions=[x_positions_fwd[i]], widths=0.1,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_voc.scatter(np.full(len(fwd_filtered), x_positions_fwd[i]), fwd_filtered,
                                            s=20, color=fwd_color, alpha=0.6)
                        med_fwd = np.nanmedian(fwd_filtered)  # Use filtered data for median
                        if not np.isnan(med_fwd) and len(fwd_filtered) > 0:
                            self.ax_voc.text(x_positions_fwd[i] + 0.12, med_fwd, f"{med_fwd:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")

                    if len(rev_filtered) > 0:
                        self.ax_voc.boxplot([rev_filtered], positions=[x_positions_rev[i]], widths=0.1,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_voc.scatter(np.full(len(rev_filtered), x_positions_rev[i]), rev_filtered,
                                            s=20, color=rev_color, alpha=0.6)
                        med_rev = np.nanmedian(rev_filtered)  # Use filtered data for median
                        if not np.isnan(med_rev) and len(rev_filtered) > 0:
                            self.ax_voc.text(x_positions_rev[i] + 0.12, med_rev, f"{med_rev:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")

                self.ax_voc.set_xticks(x_positions_fwd)
                self.ax_voc.set_xticklabels([])
                self.ax_voc.set_ylabel(self.plot_options["y_axis_labels"].get("Voc", r"$V_{oc}$ [V]"))
                self.ax_voc.grid(False)  # Turn off grid

                # Efficiency Plot: annotate medians and show x tick labels.
                for i, data in enumerate(eff_data):
                    if data is None or len(data) == 0:
                        continue
                    if len(data) % 2 != 0:
                        data = data[:-1]
                    fwd = data[::2]
                    rev = data[1::2]

                    # Filter NaN values for boxplots
                    fwd_filtered = fwd[~np.isnan(fwd)]
                    rev_filtered = rev[~np.isnan(rev)]

                    # Get colors for data points (same as what boxes previously had)
                    fwd_color = self.plot_options["forward_color"].get("Efficiency", "blue")
                    rev_color = self.plot_options["reverse_color"].get("Efficiency", "red")

                    if len(fwd_filtered) > 0:
                        self.ax_eff.boxplot([fwd_filtered], positions=[x_positions_fwd[i]], widths=0.1,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_eff.scatter(np.full(len(fwd_filtered), x_positions_fwd[i]), fwd_filtered,
                                            s=20, color=fwd_color, alpha=0.6)
                        med_fwd = np.nanmedian(fwd_filtered)  # Use filtered data for median
                        if not np.isnan(med_fwd) and len(fwd_filtered) > 0:
                            self.ax_eff.text(x_positions_fwd[i] + 0.12, med_fwd, f"{med_fwd:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")

                    if len(rev_filtered) > 0:
                        self.ax_eff.boxplot([rev_filtered], positions=[x_positions_rev[i]], widths=0.1,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_eff.scatter(np.full(len(rev_filtered), x_positions_rev[i]), rev_filtered,
                                            s=20, color=rev_color, alpha=0.6)
                        med_rev = np.nanmedian(rev_filtered)  # Use filtered data for median
                        if not np.isnan(med_rev) and len(rev_filtered) > 0:
                            self.ax_eff.text(x_positions_rev[i] + 0.12, med_rev, f"{med_rev:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")

                self.ax_eff.set_xticks(np.array([x_positions_fwd[i] + offset / 2 for i in range(len(x_positions_fwd))]))
                self.ax_eff.set_xticklabels(labels, rotation=45, ha='right')
                self.ax_eff.set_ylabel(self.plot_options["y_axis_labels"].get("Efficiency", "Efficiency [%]"))
                self.ax_eff.grid(False)  # Already set to False in original

                # Fill Factor Plot: annotate medians and show x tick labels.
                for i, data in enumerate(ff_data):
                    if data is None or len(data) == 0:
                        continue
                    if len(data) % 2 != 0:
                        data = data[:-1]
                    fwd = data[::2]
                    rev = data[1::2]

                    # Filter NaN values for boxplots
                    fwd_filtered = fwd[~np.isnan(fwd)]
                    rev_filtered = rev[~np.isnan(rev)]

                    # Get colors for data points (same as what boxes previously had)
                    fwd_color = self.plot_options["forward_color"].get("Fill Factor", "blue")
                    rev_color = self.plot_options["reverse_color"].get("Fill Factor", "red")

                    if len(fwd_filtered) > 0:
                        self.ax_ff.boxplot([fwd_filtered], positions=[x_positions_fwd[i]], widths=0.1,
                                           patch_artist=True,
                                           boxprops=dict(facecolor='none', color='black'),
                                           medianprops=dict(color='orange'))
                        self.ax_ff.scatter(np.full(len(fwd_filtered), x_positions_fwd[i]), fwd_filtered,
                                           s=20, color=fwd_color, alpha=0.6)
                        med_fwd = np.nanmedian(fwd_filtered)  # Use filtered data for median
                        if not np.isnan(med_fwd) and len(fwd_filtered) > 0:
                            self.ax_ff.text(x_positions_fwd[i] + 0.12, med_fwd, f"{med_fwd:.2f}", fontsize=10,
                                            color='orange', ha="left", va="center")

                    if len(rev_filtered) > 0:
                        self.ax_ff.boxplot([rev_filtered], positions=[x_positions_rev[i]], widths=0.1,
                                           patch_artist=True,
                                           boxprops=dict(facecolor='none', color='black'),
                                           medianprops=dict(color='orange'))
                        self.ax_ff.scatter(np.full(len(rev_filtered), x_positions_rev[i]), rev_filtered,
                                           s=20, color=rev_color, alpha=0.6)
                        med_rev = np.nanmedian(rev_filtered)  # Use filtered data for median
                        if not np.isnan(med_rev) and len(rev_filtered) > 0:
                            self.ax_ff.text(x_positions_rev[i] + 0.12, med_rev, f"{med_rev:.2f}", fontsize=10,
                                            color='orange', ha="left", va="center")

                self.ax_ff.set_xticks(np.array([x_positions_fwd[i] + offset / 2 for i in range(len(x_positions_fwd))]))
                self.ax_ff.set_xticklabels(labels, rotation=45, ha='right')
                self.ax_ff.set_ylabel(self.plot_options["y_axis_labels"].get("Fill Factor", "Fill Factor"))
                self.ax_ff.grid(False)  # Turn off grid
            else:
                # When not separating forward/reverse (show combined data)
                x_positions = np.array([i + 1 for i in range(len(self.multi_data))])

                # J_sc Plot
                for i, data in enumerate(jsc_data):
                    if data is None or len(data) == 0:
                        continue
                    # Filter NaN values
                    data_filtered = data[~np.isnan(data)]

                    # Get color for data points (same as what boxes previously had)
                    data_color = self.plot_options["forward_color"].get("Jsc", "blue")

                    if len(data_filtered) > 0:
                        self.ax_jsc.boxplot([data_filtered], positions=[x_positions[i]], widths=0.2,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_jsc.scatter(np.full(len(data_filtered), x_positions[i]), data_filtered,
                                            s=20, color=data_color, alpha=0.6)
                        med = np.nanmedian(data_filtered)
                        if not np.isnan(med) and len(data_filtered) > 0:
                            self.ax_jsc.text(x_positions[i] + 0.12, med, f"{med:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")
                self.ax_jsc.set_xticks(x_positions)
                self.ax_jsc.set_xticklabels([])
                self.ax_jsc.set_ylabel(self.plot_options["y_axis_labels"].get("Jsc", r"$J_{sc}$ [mA/cm²]"))
                self.ax_jsc.grid(False)  # Turn off grid

                # V_oc Plot
                for i, data in enumerate(voc_data):
                    if data is None or len(data) == 0:
                        continue
                    # Filter NaN values
                    data_filtered = data[~np.isnan(data)]

                    # Get color for data points (same as what boxes previously had)
                    data_color = self.plot_options["forward_color"].get("Voc", "blue")

                    if len(data_filtered) > 0:
                        self.ax_voc.boxplot([data_filtered], positions=[x_positions[i]], widths=0.2,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_voc.scatter(np.full(len(data_filtered), x_positions[i]), data_filtered,
                                            s=20, color=data_color, alpha=0.6)
                        med = np.nanmedian(data_filtered)
                        if not np.isnan(med) and len(data_filtered) > 0:
                            self.ax_voc.text(x_positions[i] + 0.12, med, f"{med:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")
                self.ax_voc.set_xticks(x_positions)
                self.ax_voc.set_xticklabels([])
                self.ax_voc.set_ylabel(self.plot_options["y_axis_labels"].get("Voc", r"$V_{oc}$ [V]"))
                self.ax_voc.grid(False)  # Turn off grid

                # Efficiency Plot
                for i, data in enumerate(eff_data):
                    if data is None or len(data) == 0:
                        continue
                    # Filter NaN values
                    data_filtered = data[~np.isnan(data)]

                    # Get color for data points (same as what boxes previously had)
                    data_color = self.plot_options["forward_color"].get("Efficiency", "blue")

                    if len(data_filtered) > 0:
                        self.ax_eff.boxplot([data_filtered], positions=[x_positions[i]], widths=0.2,
                                            patch_artist=True,
                                            boxprops=dict(facecolor='none', color='black'),
                                            medianprops=dict(color='orange'))
                        self.ax_eff.scatter(np.full(len(data_filtered), x_positions[i]), data_filtered,
                                            s=20, color=data_color, alpha=0.6)
                        med = np.nanmedian(data_filtered)
                        if not np.isnan(med) and len(data_filtered) > 0:
                            self.ax_eff.text(x_positions[i] + 0.12, med, f"{med:.2f}", fontsize=10,
                                             color='orange', ha="left", va="center")
                self.ax_eff.set_xticks(x_positions)
                self.ax_eff.set_xticklabels(labels, rotation=45, ha='right')
                self.ax_eff.set_ylabel(self.plot_options["y_axis_labels"].get("Efficiency", "Efficiency [%]"))
                self.ax_eff.grid(False)  # Already set to False in original

                # Fill Factor Plot
                for i, data in enumerate(ff_data):
                    if data is None or len(data) == 0:
                        continue
                    # Filter NaN values
                    data_filtered = data[~np.isnan(data)]

                    # Get color for data points (same as what boxes previously had)
                    data_color = self.plot_options["forward_color"].get("Fill Factor", "blue")

                    if len(data_filtered) > 0:
                        self.ax_ff.boxplot([data_filtered], positions=[x_positions[i]], widths=0.2,
                                           patch_artist=True,
                                           boxprops=dict(facecolor='none', color='black'),
                                           medianprops=dict(color='orange'))
                        self.ax_ff.scatter(np.full(len(data_filtered), x_positions[i]), data_filtered,
                                           s=20, color=data_color, alpha=0.6)
                        med = np.nanmedian(data_filtered)
                        if not np.isnan(med) and len(data_filtered) > 0:
                            self.ax_ff.text(x_positions[i] + 0.12, med, f"{med:.2f}", fontsize=10,
                                            color='orange', ha="left", va="center")
                self.ax_ff.set_xticks(x_positions)
                self.ax_ff.set_xticklabels(labels, rotation=45, ha='right')
                self.ax_ff.set_ylabel(self.plot_options["y_axis_labels"].get("Fill Factor", "Fill Factor"))
                self.ax_ff.grid(False)  # Turn off grid

            # --- Plot I-V curves ---
            self.ax_iv.set_xlabel(self.plot_options["x_axis_labels"].get("IV", "Voltage [V]"))
            self.ax_iv.set_ylabel(self.plot_options["y_axis_labels"].get("IV", "J [mA/cm²]"))

            colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'magenta', 'brown', 'pink', 'gray']

            for i, (voltage, y_data, label) in enumerate(iv_curves):
                if voltage is None or y_data is None:
                    continue

                color = colors[i % len(colors)]
                if isinstance(y_data, tuple):  # Forward and reverse data
                    fwd, rev = y_data
                    if fwd is not None:
                        self.ax_iv.plot(voltage, fwd,
                                        linestyle=self.plot_options["iv_line_style"]["Fwd"],
                                        marker=self.plot_options["iv_marker"]["Fwd"],
                                        markersize=4, color=color,
                                        label=f"{label} (Fwd)")
                    if rev is not None:
                        self.ax_iv.plot(voltage, rev,
                                        linestyle=self.plot_options["iv_line_style"]["Rev"],
                                        marker=self.plot_options["iv_marker"]["Rev"],
                                        markersize=4, color=color,
                                        label=f"{label} (Rev)")
                else:  # Single dataset
                    self.ax_iv.plot(voltage, y_data,
                                    linestyle=self.plot_options["iv_line_style"]["Fwd"],
                                    marker=self.plot_options["iv_marker"]["Fwd"],
                                    markersize=4, color=color,
                                    label=label)

            self.ax_iv.legend(loc='upper left', fontsize=8)
            self.ax_iv.grid(False)  # Turn off grid
            # --- Overall Legend (top left, one row) ---
            median_line = mlines.Line2D([], [], color='orange', linestyle='-', linewidth=2, label='Median')
            box_patch = mpatches.Patch(facecolor='none', edgecolor='black', label='IQR Box')
            data_marker = mlines.Line2D([], [], marker='o', color='black', linestyle='None', markersize=5,
                                        label='Data Points')
            self.fig.legend(handles=[median_line, box_patch, data_marker],
                            loc='upper left', bbox_to_anchor=(0.01, 0.99), ncol=3, fontsize=10)
            self.fig.suptitle(self.plot_title_var.get(), fontsize=16, y=0.98)
            self.canvas.draw()

        except Exception as e:
            messagebox.showerror("Error", f"Error generating multiple plots: {str(e)}")
            import traceback
            traceback.print_exc()

    def save_plots(self):
        plot_title = self.fig._suptitle.get_text() if self.fig._suptitle else "Untitled_Plot"
        default_filename = plot_title + "_plots.png"
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png"), ("All Files", "*.*")],
                                                 initialfile=default_filename)
        if file_path:
            try:
                self.fig.savefig(file_path, dpi=300, bbox_inches="tight")
                print(f"Plots saved as: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save plots: {e}")

    def generate_plots_dispatch(self):
        if self.multi_data:
            self.generate_plots_multiple()
        elif self.data is not None:
            self.generate_plots_single()
        else:
            messagebox.showerror("Error", "No data loaded!")
            return
        if not self.plot_frame_container.winfo_ismapped():
            self.plot_frame_container.pack(fill="both", expand=True, padx=10, pady=5)
        self.canvas.draw()

    def generate_plots(self):
        self.generate_plots_dispatch()

    def load_multiple_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_paths:
            return
        self.multi_data = []
        self.group_mapping = {}  # reset grouping on new load
        all_params = []
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="latin1") as f:
                    lines = f.readlines()
                parameters = []
                for line in lines:
                    parameters.append(line.strip())
                    if "compliance" in line.lower():
                        break
                active_area = None
                for line in lines:
                    if "active area" in line.lower():
                        parts = line.split(":")
                        if len(parts) > 1:
                            active_area = parts[1].strip()
                        break
                start_idx = len(parameters) + 1
                try:
                    perf = pd.read_csv(file_path, sep="\t", skiprows=start_idx, encoding="latin1",
                                       engine="python", on_bad_lines='skip')
                except pd.errors.EmptyDataError:
                    continue
                if perf.empty or len(perf.columns) == 0:
                    continue
                perf = perf.drop(perf.columns[0], axis=1)
                if perf.shape[1] % 2 != 0:
                    perf = perf.iloc[:, :-1]
                iv_start = None
                for i, line in enumerate(lines):
                    if line.strip().startswith("Voltage"):
                        iv_start = i
                        break
                if iv_start is not None:
                    try:
                        iv = pd.read_csv(file_path, sep="\t", skiprows=iv_start+2, encoding="latin1",
                                         engine="python", on_bad_lines='skip')
                    except pd.errors.EmptyDataError:
                        iv = None
                    if iv is not None and not iv.empty:
                        if iv.shape[1] % 2 != 0:
                            iv = iv.iloc[:, :-1]
                    else:
                        iv = None
                else:
                    iv = None
                filename = os.path.splitext(os.path.basename(file_path))[0]
                self.multi_data.append({
                    "filename": filename,
                    "performance": perf,
                    "iv": iv,
                    "active_area": active_area,
                    "params": "\n".join(parameters)
                })
                all_params.append(f"{filename}:\n" + "\n".join(parameters))
                print(f"Loaded file: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load {file_path}: {e}")
        if self.multi_data:
            self.plot_title_var.set("Comparison Plot")
            default_labels = [d["filename"] for d in self.multi_data]
            self.custom_labels_var.set(",".join(default_labels))
            combined_params = "\n\n---\n\n".join(all_params)
            self.params_text.config(state="normal")
            self.params_text.delete("1.0", tk.END)
            self.params_text.insert(tk.END, combined_params)
            self.params_text.config(state="disabled")
            print("Multiple files loaded successfully!")

if __name__ == "__main__":
    root = tk.Tk()
    app = SuSiAnalysisTool(root)
    root.mainloop()
