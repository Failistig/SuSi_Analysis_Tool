import tkinter as tk
from tkinter import filedialog, messagebox
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

        # Top frame for file selection and buttons
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(fill="x", padx=10, pady=5)

        self.load_button = tk.Button(self.top_frame, text="Load Data File", command=self.load_file)
        self.load_button.pack(side=tk.LEFT, padx=5)

        self.load_multi_button = tk.Button(self.top_frame, text="Load Multiple Files", command=self.load_multiple_files)
        self.load_multi_button.pack(side=tk.LEFT, padx=5)

        self.file_path_var = tk.StringVar()
        self.file_path_entry = tk.Entry(self.top_frame, textvariable=self.file_path_var, state="readonly", width=80)
        self.file_path_entry.pack(side=tk.LEFT, padx=5)

        # Plot Title Frame (editable)
        self.title_frame = tk.Frame(root)
        self.title_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(self.title_frame, text="Plot Title:").pack(side=tk.LEFT, padx=5)
        self.plot_title_var = tk.StringVar()
        self.plot_title_entry = tk.Entry(self.title_frame, textvariable=self.plot_title_var, width=50)
        self.plot_title_entry.pack(side=tk.LEFT, padx=5)

        # For multiple file mode: Custom file labels (comma-separated)
        tk.Label(self.title_frame, text="File Labels (comma-separated):").pack(side=tk.LEFT, padx=5)
        self.custom_labels_var = tk.StringVar()
        self.custom_labels_entry = tk.Entry(self.title_frame, textvariable=self.custom_labels_var, width=50)
        self.custom_labels_entry.pack(side=tk.LEFT, padx=5)

        # Button Frame
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill="x", padx=10, pady=5)
        self.generate_button = tk.Button(self.button_frame, text="Generate Plots", command=self.generate_plots)
        self.generate_button.pack(side=tk.LEFT, padx=5)
        self.save_button = tk.Button(self.button_frame, text="Save Plots", command=self.save_plots)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Measurement Parameters section
        self.params_frame = tk.Frame(self.root)
        self.params_frame.pack(padx=10, pady=5, fill='x')
        self.params_label = tk.Label(self.params_frame, text="Measurement Parameters", font=("Arial", 12, "bold"))
        self.params_label.pack(padx=5, pady=(5, 2))
        self.params_text = tk.Text(self.params_frame, height=7, width=50)
        self.params_text.pack(padx=5, pady=(0, 5), fill='x')
        self.params_text.config(state="disabled")

        # Create plot frame but do not pack it now (plots remain hidden until Generate Plots is clicked)
        self.plot_frame = tk.Frame(root)
        # It will be packed in generate_plots().

        # Create a figure with balanced size for both single and multi file modes.
        self.fig = plt.figure(figsize=(20, 7.2))
        gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 2], height_ratios=[1, 1])
        # Performance subplots (left half, 2x2 grid)
        self.ax_jsc = self.fig.add_subplot(gs[0, 0])
        self.ax_voc = self.fig.add_subplot(gs[0, 1])
        self.ax_eff = self.fig.add_subplot(gs[1, 0])
        self.ax_ff = self.fig.add_subplot(gs[1, 1])
        # I-V subplot (right half, spanning both rows)
        self.ax_iv = self.fig.add_subplot(gs[:, 2])
        self.fig.subplots_adjust(left=0.07, right=0.98, top=0.92, bottom=0.12, wspace=0.2, hspace=0.05)

        # Create Canvas and Navigation Toolbar (canvas is packed into plot_frame later)
        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        self.canvas.get_tk_widget().pack(padx=10, pady=10, fill='both', expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Data holders
        self.data = None  # Single file: dict with keys "filename", "performance", "iv"
        self.multi_data = []  # List of dicts for multiple files (same keys; may include "active_area" and "params")

    def extract_parameters(self, lines):
        """Extract measurement parameters from file lines, skipping any 'Keithley' header.
           Returns a string of parameters.
        """
        params = []
        for line in lines:
            # Skip the header line if it starts with "Keithley,"
            if line.lower().startswith("keithley,"):
                continue
            params.append(line.strip())
            if "compliance" in line.lower():
                break
        return "\n".join(params)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_path:
            return
        self.file_path_var.set(file_path)
        try:
            with open(file_path, "r", encoding="latin1") as f:
                lines = f.readlines()
            # Extract measurement parameters using the subroutine.
            parameters = self.extract_parameters(lines)
            self.params_text.config(state="normal")
            self.params_text.delete("1.0", tk.END)
            self.params_text.insert(tk.END, parameters)
            self.params_text.config(state="disabled")
            # Set default plot title based on filename
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            self.plot_title_var.set(base_name)
            # Load performance metrics data (starting two lines after parameters)
            start_idx = len(parameters.split("\n")) + 2
            perf = pd.read_csv(file_path, sep="\t", skiprows=start_idx, encoding="latin1",
                               engine="python", error_bad_lines=False)
            if perf.empty:
                raise ValueError("No columns to parse from file (performance data empty)")
            perf = perf.drop(perf.columns[0], axis=1)
            if perf.shape[1] % 2 != 0:
                perf = perf.iloc[:, :-1]
            # Load I-V data
            iv_start = None
            for i, line in enumerate(lines):
                if line.strip().startswith("Voltage"):
                    iv_start = i
                    break
            if iv_start is not None:
                iv = pd.read_csv(file_path, sep="\t", skiprows=iv_start + 2,
                                 encoding="latin1", engine="python", error_bad_lines=False)
                if iv.empty:
                    iv = None
                elif iv.shape[1] % 2 != 0:
                    iv = iv.iloc[:, :-1]
            else:
                iv = None
            self.data = {"filename": base_name, "performance": perf, "iv": iv, "params": parameters}
            print("Single file loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def load_multiple_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_paths:
            return
        self.multi_data = []  # Clear previous multi-file data
        all_params = []  # To collect measurement parameters for each file
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="latin1") as f:
                    lines = f.readlines()
                # Extract measurement parameters using the subroutine.
                parameters = self.extract_parameters(lines)
                # For each file, we keep only the first active area (if present)
                active_area = None
                for line in lines:
                    if "active area" in line.lower():
                        parts = line.split(":")
                        if len(parts) > 1:
                            active_area = parts[1].strip()
                        break
                # Load performance metrics data
                start_idx = len(parameters.split("\n")) + 2
                try:
                    perf = pd.read_csv(file_path, sep="\t", skiprows=start_idx, encoding="latin1",
                                       engine="python", error_bad_lines=False)
                except pd.errors.EmptyDataError:
                    print(f"Skipping file {file_path}: No performance data found.")
                    continue
                if perf.empty or len(perf.columns) == 0:
                    print(f"Skipping file {file_path}: No columns to parse in performance data.")
                    continue
                perf = perf.drop(perf.columns[0], axis=1)
                if perf.shape[1] % 2 != 0:
                    perf = perf.iloc[:, :-1]
                # Load I-V data
                iv_start = None
                for i, line in enumerate(lines):
                    if line.strip().startswith("Voltage"):
                        iv_start = i
                        break
                if iv_start is not None:
                    try:
                        iv = pd.read_csv(file_path, sep="\t", skiprows=iv_start + 2, encoding="latin1",
                                         engine="python", error_bad_lines=False)
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
                    "params": parameters
                })
                all_params.append(f"{filename}:\n{parameters}")
                print(f"Loaded file: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load {file_path}: {e}")
        if self.multi_data:
            self.plot_title_var.set("Comparison Plot")
            # Build default custom labels: only the filename (active area not appended to label)
            default_labels = [d["filename"] for d in self.multi_data]
            self.custom_labels_var.set(",".join(default_labels))
            # Combine measurement parameters for display (separated by a divider)
            combined_params = "\n\n---\n\n".join(all_params)
            self.params_text.config(state="normal")
            self.params_text.delete("1.0", tk.END)
            self.params_text.insert(tk.END, combined_params)
            self.params_text.config(state="disabled")

    def generate_plots(self):
        if self.multi_data:
            self.generate_plots_multiple()
        elif self.data is not None:
            self.generate_plots_single()
        else:
            messagebox.showerror("Error", "No data loaded!")
            return
        # Pack the plot frame so that plots become visible.
        if not self.plot_frame.winfo_ismapped():
            self.plot_frame.pack(padx=10, pady=5, fill='both', expand=True)
        self.canvas.draw()

    def generate_plots_single(self):
        try:
            perf = self.data["performance"].apply(pd.to_numeric, errors='coerce')
            num_columns = perf.shape[1]
            if num_columns == 1:
                jsc = perf.iloc[0, 0]
                voc = perf.iloc[1, 0]
                eff = perf.iloc[2, 0]
                ff = perf.iloc[3, 0]
                x_positions = [1]
                pixel_labels = ["Pixel 1"]
            else:
                num_pixels = num_columns // 2
                x_positions = list(range(1, num_pixels + 1))
                pixel_labels = [f"Pixel {i}" for i in x_positions]
                jsc_fwd = perf.iloc[0, ::2].values
                jsc_rev = perf.iloc[0, 1::2].values
                voc_fwd = perf.iloc[1, ::2].values
                voc_rev = perf.iloc[1, 1::2].values
                ff_fwd = perf.iloc[2, ::2].values
                ff_rev = perf.iloc[2, 1::2].values
                eff_fwd = perf.iloc[3, ::2].values
                eff_rev = perf.iloc[3, 1::2].values

            for ax in [self.ax_jsc, self.ax_voc, self.ax_eff, self.ax_ff, self.ax_iv]:
                ax.clear()

            self.ax_jsc.set_ylabel("J_sc [mA/cm²]", fontsize=14)
            self.ax_jsc.set_xticks(x_positions)
            self.ax_jsc.set_xticklabels([])
            self.ax_jsc.plot(x_positions, jsc_fwd, marker='o', linestyle='None', markersize=8, color='blue',
                             label="Forward")
            self.ax_jsc.plot(x_positions, jsc_rev, marker='s', linestyle='None', markersize=8, color='lightblue',
                             label="Reverse")
            self.ax_jsc.legend(fontsize=10)
            self.ax_jsc.grid(True)

            self.ax_voc.set_ylabel("V_oc [V]", fontsize=14)
            self.ax_voc.set_xticks(x_positions)
            self.ax_voc.set_xticklabels([])
            self.ax_voc.plot(x_positions, voc_fwd, marker='o', linestyle='None', markersize=8, color='red',
                             label="Forward")
            self.ax_voc.plot(x_positions, voc_rev, marker='s', linestyle='None', markersize=8, color='tomato',
                             label="Reverse")
            self.ax_voc.legend(fontsize=10)
            self.ax_voc.grid(True)

            self.ax_eff.set_ylabel("Efficiency [%]", fontsize=14)
            self.ax_eff.set_xticks(x_positions)
            self.ax_eff.set_xticklabels(pixel_labels, rotation=45, ha='right')
            self.ax_eff.plot(x_positions, eff_fwd, marker='o', linestyle='None', markersize=8, color='green',
                             label="Forward")
            self.ax_eff.plot(x_positions, eff_rev, marker='s', linestyle='None', markersize=8, color='limegreen',
                             label="Reverse")
            self.ax_eff.legend(fontsize=10)
            self.ax_eff.grid(True)

            self.ax_ff.set_ylabel("Fill Factor [%]", fontsize=14)
            self.ax_ff.set_xticks(x_positions)
            self.ax_ff.set_xticklabels(pixel_labels, rotation=45, ha='right')
            self.ax_ff.plot(x_positions, ff_fwd, marker='o', linestyle='None', markersize=8, color='magenta',
                            label="Forward")
            self.ax_ff.plot(x_positions, ff_rev, marker='s', linestyle='None', markersize=8, color='violet',
                            label="Reverse")
            self.ax_ff.legend(fontsize=10)
            self.ax_ff.grid(True)

            if self.data["iv"] is not None:
                iv = self.data["iv"].apply(pd.to_numeric, errors='coerce')
                voltage = iv.iloc[:, 0]
                num_pixels_iv = (iv.shape[1] - 1) // 2
                for i in range(num_pixels_iv):
                    forward = iv.iloc[:, 2 * i + 1]
                    reverse = iv.iloc[:, 2 * i + 2]
                    color = ['blue', 'red', 'green', 'orange', 'pink', 'cyan'][i % 6]
                    self.ax_iv.plot(voltage, forward, label=f"Pixel {i + 1} (Fwd)", color=color, linestyle='-',
                                    marker='o', markersize=4)
                    self.ax_iv.plot(voltage, reverse, label=f"Pixel {i + 1} (Rev)", color=color, linestyle=':',
                                    marker='s', markersize=4)
                self.ax_iv.set_xlabel("Voltage [V]", fontsize=14)
                self.ax_iv.set_ylabel("J [mA/cm²]", fontsize=14)
                self.ax_iv.legend(loc='upper left', fontsize=10)
                self.ax_iv.grid(True)
            else:
                self.ax_iv.clear()
                self.ax_iv.set_title("No I-V Data")
            self.fig.suptitle(self.plot_title_var.get(), fontsize=16, y=0.98)
            self.canvas.draw()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate plots: {e}")

    def generate_plots_multiple(self):
        """
        For multiple files:
         - LEFT: Create boxplots for each performance metric.
           Each box represents all pixel values (forward and reverse) for one file.
           X-axis ticks are set to the file names (without active area info) or custom labels.
           Individual data points are also plotted over the boxplots.
         - RIGHT: Plot the best (highest efficiency) forward I-V curve from each file.
        """
        try:
            if not self.multi_data:
                messagebox.showerror("Error", "No multiple files loaded!")
                return

            custom = self.custom_labels_var.get().strip()
            if custom:
                labels = [lab.strip() for lab in custom.split(",")]
                if len(labels) != len(self.multi_data):
                    messagebox.showerror("Error", "Number of custom labels must match number of files!")
                    return
            else:
                labels = [d["filename"] for d in self.multi_data]

            jsc_data, voc_data, eff_data, ff_data = [], [], [], []
            iv_curves = []  # list of tuples: (voltage, forward curve, filename)
            for d in self.multi_data:
                perf = d["performance"].apply(pd.to_numeric, errors='coerce')
                jsc_vals = perf.iloc[0, :].values.astype(float)
                voc_vals = perf.iloc[1, :].values.astype(float)
                ff_vals = perf.iloc[2, :].values.astype(float)
                eff_vals = perf.iloc[3, :].values.astype(float)
                jsc_data.append(jsc_vals)
                voc_data.append(voc_vals)
                eff_data.append(eff_vals)
                ff_data.append(ff_vals)

                best_idx = np.argmax(eff_vals)
                pixel_index = best_idx // 2
                if d["iv"] is not None:
                    iv = d["iv"].apply(pd.to_numeric, errors='coerce')
                    voltage = iv.iloc[:, 0]
                    fwd = iv.iloc[:, 2 * pixel_index + 1]
                    iv_curves.append((voltage, fwd, d["filename"]))
                else:
                    iv_curves.append((None, None, d["filename"]))

            for ax in [self.ax_jsc, self.ax_voc, self.ax_eff, self.ax_ff, self.ax_iv]:
                ax.clear()

            x_positions = list(range(1, len(self.multi_data) + 1))
            # Boxplot settings: Transparent boxes so data points remain visible.
            boxprops = dict(facecolor='none', color='black')
            medianprops = dict(color='orange', linewidth=2)
            whiskerprops = dict(color='black', linestyle='--')
            flierprops = dict(marker='o', markerfacecolor='black', markersize=4)

            # Plot boxplots and data points for each metric
            self.ax_jsc.boxplot(jsc_data, positions=x_positions, patch_artist=True,
                                boxprops=boxprops, medianprops=medianprops,
                                whiskerprops=whiskerprops, flierprops=flierprops)
            # Add individual data points
            for i, data in enumerate(jsc_data):
                x = np.random.normal(x_positions[i], 0.05, size=len(data))  # Add jitter
                self.ax_jsc.scatter(x, data, alpha=0.6, s=20, color='darkblue')
            self.ax_jsc.set_ylabel("J_sc [mA/cm²]", fontsize=14)
            self.ax_jsc.set_xticks(x_positions)
            self.ax_jsc.set_xticklabels(labels, rotation=45, ha='right')
            self.ax_jsc.grid(True)

            self.ax_voc.boxplot(voc_data, positions=x_positions, patch_artist=True,
                                boxprops=boxprops, medianprops=medianprops,
                                whiskerprops=whiskerprops, flierprops=flierprops)
            # Add individual data points
            for i, data in enumerate(voc_data):
                x = np.random.normal(x_positions[i], 0.05, size=len(data))  # Add jitter
                self.ax_voc.scatter(x, data, alpha=0.6, s=20, color='darkred')
            self.ax_voc.set_ylabel("V_oc [V]", fontsize=14)
            self.ax_voc.set_xticks(x_positions)
            self.ax_voc.set_xticklabels(labels, rotation=45, ha='right')
            self.ax_voc.grid(True)

            self.ax_eff.boxplot(eff_data, positions=x_positions, patch_artist=True,
                                boxprops=boxprops, medianprops=medianprops,
                                whiskerprops=whiskerprops, flierprops=flierprops)
            # Add individual data points
            for i, data in enumerate(eff_data):
                x = np.random.normal(x_positions[i], 0.05, size=len(data))  # Add jitter
                self.ax_eff.scatter(x, data, alpha=0.6, s=20, color='darkgreen')
            self.ax_eff.set_ylabel("Efficiency [%]", fontsize=14)
            self.ax_eff.set_xticks(x_positions)
            self.ax_eff.set_xticklabels(labels, rotation=45, ha='right')
            self.ax_eff.grid(True)

            self.ax_ff.boxplot(ff_data, positions=x_positions, patch_artist=True,
                               boxprops=boxprops, medianprops=medianprops,
                               whiskerprops=whiskerprops, flierprops=flierprops)
            # Add individual data points
            for i, data in enumerate(ff_data):
                x = np.random.normal(x_positions[i], 0.05, size=len(data))  # Add jitter
                self.ax_ff.scatter(x, data, alpha=0.6, s=20, color='darkmagenta')
            self.ax_ff.set_ylabel("Fill Factor [%]", fontsize=14)
            self.ax_ff.set_xticks(x_positions)
            self.ax_ff.set_xticklabels(labels, rotation=45, ha='right')
            self.ax_ff.grid(True)

            # Enhanced legend for boxplots: Including data points
            median_line = mlines.Line2D([], [], color='orange', linestyle='-', linewidth=2, label='Median')
            box_line = mpatches.Patch(facecolor='none', edgecolor='black', label='IQR (25th-75th percentile)')
            outlier_marker = mlines.Line2D([], [], marker='o', color='black', linestyle='None', markersize=4,
                                           label='Outliers')
            data_point = mlines.Line2D([], [], marker='o', color='darkblue', linestyle='None', markersize=5,
                                      label='Data Points')


            self.fig.legend(handles=[median_line, box_line, outlier_marker,
                                     data_point],
                            loc='upper left', bbox_to_anchor=(0.01, 0.95), ncol=2, fontsize=9)

            # I-V plot: Plot best forward I-V curve from each file.
            colors = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'magenta']
            for i, (voltage, fwd, fname) in enumerate(iv_curves):
                if voltage is not None and fwd is not None:
                    self.ax_iv.plot(voltage, fwd, label=fname, color=colors[i % len(colors)],
                                    linestyle='-', marker='o', markersize=4)
            self.ax_iv.set_xlabel("Voltage [V]", fontsize=14)
            self.ax_iv.set_ylabel("J [mA/cm²]", fontsize=14)
            self.ax_iv.legend(loc='upper left', fontsize=10)
            self.ax_iv.grid(True)

            self.fig.suptitle(self.plot_title_var.get(), fontsize=16, y=0.98)
            self.canvas.draw()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate multiple-file plots: {e}")

    def save_plots(self):
        plot_title = self.fig._suptitle.get_text() if self.fig._suptitle else "Untitled_Plot"
        suggested_filename = plot_title + "Plots.png"
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                                                 initialfile=suggested_filename)
        if file_path:
            self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
            print(f"Plots saved as: {file_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SuSiAnalysisTool(root)
    root.mainloop()
