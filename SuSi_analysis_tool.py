import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import os
import numpy as np


class SuSiAnalysisTool:
    def __init__(self, root):
        self.root = root
        self.root.title("SuSi Analysis Tool")
        self.root.state("zoomed")  # Fullscreen

        # Top frame for file selection
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(fill="x", padx=10, pady=5)

        self.load_button = tk.Button(self.top_frame, text="Load Data File", command=self.load_file)
        self.load_button.pack(side=tk.LEFT, padx=5)

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

        # Button Frame (below file selection and title)
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill="x", padx=10, pady=5)
        self.generate_button = tk.Button(self.button_frame, text="Generate Plots", command=self.generate_plots)
        self.generate_button.pack(side=tk.LEFT, padx=5)
        self.save_button = tk.Button(self.button_frame, text="Save Plots", command=self.save_plots)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Measurement Parameters (no outer frame)
        self.params_frame = tk.Frame(root)
        self.params_frame.pack(fill="x", padx=10, pady=5)
        self.params_text = tk.Text(self.params_frame, height=10, wrap=tk.WORD, state="disabled", relief="flat")
        self.params_text.pack(fill="x")

        self.plot_frame = tk.Frame(root)

        # Create a figure with a more balanced size
        self.fig = plt.figure(figsize=(16, 8))

        # Create a grid layout that splits the page in half
        # Left half: Parameter plots (2x2 grid)
        # Right half: I-V curves
        gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 2], height_ratios=[1, 1])

        # Parameter plots (in the left half)
        self.ax_jsc = self.fig.add_subplot(gs[0, 0])
        self.ax_voc = self.fig.add_subplot(gs[0, 1])
        self.ax_eff = self.fig.add_subplot(gs[1, 0])
        self.ax_ff = self.fig.add_subplot(gs[1, 1])

        # I-V curves plot (in the right half, spanning both rows)
        self.ax_iv = self.fig.add_subplot(gs[:, 2])

        # Adjust subplot layout
        self.fig.subplots_adjust(left=0.07, right=0.98, top=0.92, bottom=0.1, wspace=0.2, hspace=0.3)

        # Create Canvas for displaying the figure
        self.canvas = FigureCanvasTkAgg(self.fig, self.plot_frame)
        self.canvas.get_tk_widget().pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Add Navigation Toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.data = None  # This will hold the numeric data
        self.iv_data = None  # This will hold the I-V curve data

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_path:
            return
        self.file_path_var.set(file_path)
        try:
            with open(file_path, "r", encoding="latin1") as f:
                lines = f.readlines()
            # Extract measurement parameters (until "compliance")
            parameters = []
            for line in lines:
                if "compliance" in line:
                    parameters.append(line.strip())
                    break
                parameters.append(line.strip())
            self.params_text.config(state="normal")
            self.params_text.delete("1.0", tk.END)
            self.params_text.insert(tk.END, "\n".join(parameters))
            self.params_text.config(state="disabled")
            # Set default plot title to file name without extension
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            self.plot_title_var.set(base_name)
            # Data assumed to start two lines after parameters
            start_idx = len(parameters) + 2
            self.data = pd.read_csv(file_path, sep="\t", skiprows=start_idx,
                                    encoding="latin1", engine="python", error_bad_lines=False)
            # Drop first column if it contains parameter names
            self.data = self.data.drop(self.data.columns[0], axis=1)
            # Ensure even number of columns; if odd, drop the last column.
            if self.data.shape[1] % 2 != 0:
                self.data = self.data.iloc[:, :-1]
                print("Odd number of columns detected; dropped the last column.")
            print("Success", "File loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def generate_plots(self):
        try:
            if self.data is None:
                messagebox.showerror("Error", "No data loaded!")
                return

            # Convert all columns to numeric
            self.data = self.data.apply(pd.to_numeric, errors='coerce')
            num_columns = self.data.shape[1]

            # Handle single column case
            if num_columns == 1:
                # Extract values from the single column
                jsc = self.data.iloc[0, 0] if self.data.shape[0] > 0 else 0
                voc = self.data.iloc[1, 0] if self.data.shape[0] > 1 else 0
                eff = self.data.iloc[2, 0] if self.data.shape[0] > 2 else 0
                ff = self.data.iloc[3, 0] if self.data.shape[0] > 3 else 0

                # Create single data point arrays
                jsc_fwd = np.array([jsc])
                jsc_rev = np.array([jsc])
                voc_fwd = np.array([voc])
                voc_rev = np.array([voc])
                eff_fwd = np.array([eff])
                eff_rev = np.array([eff])
                ff_fwd = np.array([ff])
                ff_rev = np.array([ff])

                x_positions = [1]
                pixel_labels = ["Pixel 1"]
                
            elif num_columns % 2 != 0:
                # Handle odd number of columns - use only complete pairs
                num_pixels = num_columns // 2
                self.data = self.data.iloc[:, :num_pixels * 2]  # Keep only even number of columns
                num_columns = self.data.shape[1]

                # Continue with the existing code for multiple columns...
                x_positions = list(range(1, num_pixels + 1))
                pixel_labels = [f"Pixel {i}" for i in x_positions]

                # Extract forward and reverse values
                jsc_fwd = self.data.iloc[0, ::2].values
                jsc_rev = self.data.iloc[0, 1::2].values
                voc_fwd = self.data.iloc[1, ::2].values
                voc_rev = self.data.iloc[1, 1::2].values
                eff_fwd = self.data.iloc[2, ::2].values
                eff_rev = self.data.iloc[2, 1::2].values
                ff_fwd = self.data.iloc[3, ::2].values
                ff_rev = self.data.iloc[3, 1::2].values
            else:
                # Original code for even number of columns
                num_pixels = num_columns // 2
                x_positions = list(range(1, num_pixels + 1))
                pixel_labels = [f"Pixel {i}" for i in x_positions]

                jsc_fwd = self.data.iloc[0, ::2].values
                jsc_rev = self.data.iloc[0, 1::2].values
                voc_fwd = self.data.iloc[1, ::2].values
                voc_rev = self.data.iloc[1, 1::2].values
                eff_fwd = self.data.iloc[2, ::2].values
                eff_rev = self.data.iloc[2, 1::2].values
                ff_fwd = self.data.iloc[3, ::2].values
                ff_rev = self.data.iloc[3, 1::2].values

            print(f"Jsc forward: {jsc_fwd}, reverse: {jsc_rev}")
            print(f"Voc forward: {voc_fwd}, reverse: {voc_rev}")
            print(f"Efficiency forward: {eff_fwd}, reverse: {eff_rev}")
            print(f"Fill Factor forward: {ff_fwd}, reverse: {ff_rev}")

            # Ensure the number of pixels corresponds to the length of the data
            if len(x_positions) != len(jsc_fwd) or len(x_positions) != len(jsc_rev):
                messagebox.showerror("Error", "Mismatch between number of pixels and Jsc data points!")
                return

            # Clear previous plots
            self.ax_jsc.clear()
            self.ax_voc.clear()
            self.ax_eff.clear()
            self.ax_ff.clear()
            self.ax_iv.clear()

            # Plot Jsc: forward as blue circles, reverse as blue squares (no connecting line)
            self.ax_jsc.set_ylabel("Jsc (mA/cm²)")
            self.ax_jsc.set_xticks(x_positions)
            self.ax_jsc.set_xticklabels(pixel_labels, rotation=90)
            self.ax_jsc.plot(x_positions, jsc_fwd, 'bo', markersize=8, label="Forward")
            self.ax_jsc.plot(x_positions, jsc_rev, linestyle='None', marker='s', color='blue', markersize=8,
                             label="Reverse")
            self.ax_jsc.legend()
            self.ax_jsc.set_title("Short Circuit Current")

            # Plot Voc: forward as red circles, reverse as red squares
            self.ax_voc.set_ylabel("Voc (V)")
            self.ax_voc.set_xticks(x_positions)
            self.ax_voc.set_xticklabels(pixel_labels, rotation=90)
            self.ax_voc.plot(x_positions, voc_fwd, 'ro', markersize=8, label="Forward")
            self.ax_voc.plot(x_positions, voc_rev, linestyle='None', marker='s', color='red', markersize=8,
                             label="Reverse")
            self.ax_voc.legend()
            self.ax_voc.set_title("Open Circuit Voltage")

            # Plot Efficiency: forward as green circles, reverse as green squares
            self.ax_eff.set_ylabel("Efficiency (%)")
            self.ax_eff.set_xticks(x_positions)
            self.ax_eff.set_xticklabels(pixel_labels, rotation=90)
            self.ax_eff.plot(x_positions, eff_fwd, 'go', markersize=8, label="Forward")
            self.ax_eff.plot(x_positions, eff_rev, linestyle='None', marker='s', color='green', markersize=8,
                             label="Reverse")
            self.ax_eff.legend()
            self.ax_eff.set_title("Efficiency")

            # Plot Fill Factor: forward as magenta circles, reverse as magenta squares
            self.ax_ff.set_ylabel("Fill Factor (%)")
            self.ax_ff.set_xticks(x_positions)
            self.ax_ff.set_xticklabels(pixel_labels, rotation=90)
            self.ax_ff.plot(x_positions, ff_fwd, 'mo', markersize=8, label="Forward")
            self.ax_ff.plot(x_positions, ff_rev, linestyle='None', marker='s', color='magenta', markersize=8,
                            label="Reverse")
            self.ax_ff.legend()
            self.ax_ff.set_title("Fill Factor")

            # Plot I-V curves if data is available
            if self.iv_data is not None:
                # Convert to numeric
                iv_data_numeric = self.iv_data.apply(pd.to_numeric, errors='coerce')

                # Debugging: print the I-V data and check if it's parsed correctly
                print("IV Data after conversion to numeric:")
                print(iv_data_numeric.head())

                # Check for the expected number of columns (pairs of voltage and current)
                if iv_data_numeric.shape[1] % 2 != 0:
                    messagebox.showerror("Error", "I-V data columns should be in pairs of voltage and current.")
                    return

                # Plot each pixel's I-V curve
                for i in range(iv_data_numeric.shape[1] // 2):
                    voltage = iv_data_numeric.iloc[:, 2 * i]
                    current = iv_data_numeric.iloc[:, 2 * i + 1]

                    # Debug: check the voltage and current
                    print(f"Voltage for Pixel {i + 1}: {voltage.values}")
                    print(f"Current for Pixel {i + 1}: {current.values}")

                    # Plot the I-V curve
                    color = ['blue', 'red', 'green', 'orange', 'pink', 'cyan'][i % 6]
                    self.ax_iv.plot(voltage, current, label=f"Pixel {i + 1}", color=color, linestyle='-', marker='o')

                self.ax_iv.set_xlabel("Voltage (V)")
                self.ax_iv.set_ylabel("Current (mA)")
                self.ax_iv.set_title("I-V Curves")
                self.ax_iv.legend(loc='upper left', bbox_to_anchor=(1.01, 1))  # Ensure legend is in plot area
                self.ax_iv.grid(True)

            # Set overall figure title from the editable plot title
            self.fig.suptitle(self.plot_title_var.get(), fontsize=14)

            # Pack the plot frame if it's not already visible
            if not self.plot_frame.winfo_ismapped():
                self.plot_frame.pack(fill="both", expand=True, padx=10, pady=5)

            # Draw canvas
            self.canvas.draw()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate plots: {e}")
            import traceback
            traceback.print_exc()

    def save_plots(self):
        if self.data is None:
            messagebox.showerror("Error", "No plots to save!")
            return

        default_filename = os.path.splitext(os.path.basename(self.file_path_var.get()))[0] + "_plots.png"
        save_path = filedialog.asksaveasfilename(defaultextension=".png", initialfile=default_filename,
                                                 filetypes=[("PNG files", "*.png"), ("All Files", "*.*")])
        if save_path:
            try:
                self.fig.savefig(save_path, dpi=150, bbox_inches='tight')
                messagebox.showinfo("Success", "Plots saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save plots: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SuSiAnalysisTool(root)
    root.mainloop()