# **SuSi Analysis Tool**  

## **Overview**  
The **SuSi Analysis Tool** is a **Python-based GUI application** for analyzing and visualizing **solar cell measurement data** obtained from a **Sun Simulator (SuSi)**. The tool enables users to:  

- **Load and analyze a single measurement file** to visualize individual pixel performance and I-V curves.  
- **Compare multiple measurement files** by generating boxplots for performance parameters and selecting the **best efficiency** I-V curve from each file.  
- **Customize labels** for better file organization in multi-file mode.  
- **Save plots** for documentation and reporting.  

The tool is built using **Tkinter for GUI**, **Matplotlib for visualization**, and **Pandas for data handling**.  


## **Features**  

### **1. Single Measurement Analysis**  
When loading a **single** measurement file:  
- Extracts and displays **measurement parameters** from the file.  
- Plots four key **performance metrics**:  
  - **Jsc** (Short-circuit current density, mA/cm²)  
  - **Voc** (Open-circuit voltage, V)  
  - **Efficiency** (%)  
  - **Fill Factor** (%)  
- Plots **I-V curves** for all measured pixels (both forward and reverse sweeps).  
- Allows users to **save** the generated plots.  

### **2. Multiple Measurement Comparison**  
When loading **multiple** measurement files:  
- Displays **measurement parameters** for all loaded files.  
- Generates **boxplots** for Jsc, Voc, Efficiency, and Fill Factor, where:  
  - Each box represents all pixel values (forward and reverse) for one file.  
  - X-axis labels correspond to **file names** (or custom labels).  
- Plots **only the best-efficiency I-V curve** for each file.  
- Adds a **custom legend** to explain boxplot elements (median, IQR, outliers).  
- Allows users to **save** the comparison plots.
- 

## **Installation**  

### **Prerequisites**  
Ensure that you have **Python 3.8+** installed on your system.  
You also need the following Python libraries:  
- tkinter (GUI library, comes pre-installed with Python)  
- matplotlib (for plotting)  
- pandas (for data processing)  
- numpy (for numerical operations)  

### **Installation Steps**  
1. **Clone this repository**  
   git clone https://github.com/YOUR_USERNAME/SuSi-Analysis-Tool.git
   cd SuSi-Analysis-Tool


2. **Install required dependencies**  
   If using **pip**, run:  
   pip install -r requirements.txt

   Alternatively, install dependencies manually:  
   pip install matplotlib pandas numpy

3. **Run the application**  
   python susi_analysis.py
   (Replace susi_analysis.py with the actual filename of your script.)
   

## **Usage Instructions**  

### **1. Load a Single Measurement File**  
- Click **"Load Data File"** and select a .txt measurement file.  
- The measurement parameters will be displayed in a text box.  
- Click **"Generate Plots"** to visualize individual pixel performance and I-V curves.  
- Click **"Save Plots"** to export the figures.  

### **2. Load and Compare Multiple Files**  
- Click **"Load Multiple Files"** and select multiple .txt files.  
- The measurement parameters for all selected files will be displayed.  
- Click **"Generate Plots"** to visualize boxplots and best-efficiency I-V curves.  
- Optionally, enter **custom labels** for the files before plotting.  
- Click **"Save Plots"** to export the comparison figures.  


## **Author**  
Florian Kalaß

