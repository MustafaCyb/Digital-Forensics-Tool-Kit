import customtkinter as ctk
from tkinter import filedialog
import threading
import os,sys
from capture import capture_traffic
from Main_analizer import generate_report 
import datetime

# Redirect stderr to null (suppresses unwanted error messages)
sys.stderr = open(os.devnull, 'w')

# Set appearance mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class NetworkAnalyzerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Network Forensics")
        self.geometry("800x600")
        
        # Create main container
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Create tabs
        self.capture_tab = self.tabview.add("Packet Capture")
        self.analysis_tab = self.tabview.add("PCAP Analysis")
        
        # Initialize UI components
        self.create_capture_tab()
        self.create_analysis_tab()
        
        # Create necessary directories
        self.create_directories()
    
    def create_directories(self):
        required_dirs = ["Pcaps", "Logs", "Generated_Reports"]
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
    
    def create_capture_tab(self):
        # Capture Duration
        ctk.CTkLabel(self.capture_tab, text="Capture Duration (seconds):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.duration_entry = ctk.CTkEntry(self.capture_tab)
        self.duration_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # BPF Filter
        ctk.CTkLabel(self.capture_tab, text="Filter (e.g., tcp, udp):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.filter_entry = ctk.CTkEntry(self.capture_tab)
        self.filter_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # File Name
        ctk.CTkLabel(self.capture_tab, text="File Name:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.filename_entry = ctk.CTkEntry(self.capture_tab)
        self.filename_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # Start Button
        self.start_btn = ctk.CTkButton(self.capture_tab, text="Start Capture", command=self.start_capture)
        self.start_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Status Console
        self.capture_status = ctk.CTkTextbox(self.capture_tab, height=150)
        self.capture_status.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
    
    def create_analysis_tab(self):
        # PCAP File Selection
        ctk.CTkLabel(self.analysis_tab, text="PCAP File:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.pcap_path_entry = ctk.CTkEntry(self.analysis_tab, width=400)
        self.pcap_path_entry.grid(row=0, column=1, padx=10, pady=5)
        self.browse_btn = ctk.CTkButton(self.analysis_tab, text="Browse", command=self.browse_pcap)
        self.browse_btn.grid(row=0, column=2, padx=10, pady=5)
        
        # Report Name
        ctk.CTkLabel(self.analysis_tab, text="Report Name:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.report_entry = ctk.CTkEntry(self.analysis_tab)
        self.report_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Protocol Filter
        ctk.CTkLabel(self.analysis_tab, text="Protocol Filter:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.protocol_filter_entry = ctk.CTkEntry(self.analysis_tab)
        self.protocol_filter_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # Generate Button
        self.generate_btn = ctk.CTkButton(self.analysis_tab, text="Generate Report", command=self.start_analysis)
        self.generate_btn.grid(row=3, column=0, columnspan=3, pady=10)
        
        # Analysis Status
        self.analysis_status = ctk.CTkTextbox(self.analysis_tab, height=150)
        self.analysis_status.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
    
    def browse_pcap(self):
        filepath = filedialog.askopenfilename(filetypes=[("PCAP files", "*.pcap")])
        if filepath:
            self.pcap_path_entry.delete(0, ctk.END)
            self.pcap_path_entry.insert(0, filepath)
    
    def start_capture(self):
        duration = self.duration_entry.get()
        if not duration.isdigit():
            self.update_capture_status("Error: Please enter a valid number for duration")
            return
        
        # Generate filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = self.filename_entry.get() or "network_capture"
        pcap_file = f"Pcaps/{file_name}_{timestamp}.pcap"
        log_file = f"Logs/{file_name}_{timestamp}.log"
        
        # Start capture in thread
        thread = threading.Thread(
            target=self.run_capture,
            args=(pcap_file, log_file, int(duration)),
            daemon=True
        )
        thread.start()
    
    def run_capture(self, pcap_file, log_file, duration):
        self.update_capture_status("Starting capture...")
        self.start_btn.configure(state="disabled")
        
        try:
            capture_traffic(
                output_file=pcap_file,
                log_file=log_file,
                duration=duration,
                filter_exp=self.filter_entry.get() or None
            )
            self.update_capture_status(f"Capture completed!\nPCAP: {pcap_file}\nLog: {log_file}")
        except Exception as e:
            self.update_capture_status(f"Error during capture: {str(e)}")
        finally:
            self.start_btn.configure(state="normal")
    
    def start_analysis(self):
        pcap_path = self.pcap_path_entry.get()
        report_name = self.report_entry.get()
        
        if not pcap_path:
            self.update_analysis_status("Error: Please select a PCAP file")
            return
        
        if not report_name:
            self.update_analysis_status("Error: Please enter a report name")
            return
        
        output_file = f"Generated_Reports/{report_name}.html"
        
        # Start analysis in thread
        thread = threading.Thread(
            target=self.run_analysis,
            args=(pcap_path, output_file),
            daemon=True
        )
        thread.start()


    def run_analysis(self, pcap_path, output_file):
        self.update_analysis_status("Starting analysis...")
        self.generate_btn.configure(state="disabled")
        
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Attempt to get a capture object from generate_report
            capture = generate_report(
                file_path=pcap_path,
                output_file=output_file,
                filter_protocol=self.protocol_filter_entry.get() or None
            )
            
            # Only run cleanup if a valid capture object was returned
            if capture is not None and hasattr(capture, "close_async"):
                loop.run_until_complete(capture.close_async())
            
            self.update_analysis_status(f"Report generated: {output_file}")
        except Exception as e:
            self.update_analysis_status(f"Analysis error: {str(e)}")
        finally:
            self.generate_btn.configure(state="normal")




    def update_capture_status(self, message):
        self.capture_status.insert(ctk.END, message + "\n")
        self.capture_status.see(ctk.END)
    
    def update_analysis_status(self, message):
        self.analysis_status.insert(ctk.END, message + "\n")
        self.analysis_status.see(ctk.END)

if __name__ == "__main__":
    app = NetworkAnalyzerApp()
    app.mainloop()