import os
import subprocess
import platform
import time
import ctypes
import sys
import threading
import shutil
from tkinter import messagebox
import customtkinter as ctk
from tkinter import filedialog

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MemoryDumpApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Memory Dump Tool")
        self.geometry("800x600")
        self.os_type = platform.system()
        self.dump_command = None
        self.running = False
        
        self.create_widgets()
        self.check_privileges()
        
    def create_widgets(self):
        # Output File Section
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.file_frame, text="Output File:").pack(side="left", padx=5)
        self.file_entry = ctk.CTkEntry(self.file_frame, width=400)
        self.file_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.file_entry.insert(0, "memory.raw")
        
        self.browse_btn = ctk.CTkButton(self.file_frame, text="Browse", command=self.browse_file)
        self.browse_btn.pack(side="left", padx=5)
        
        # Status Console
        self.console = ctk.CTkTextbox(self, wrap="word")
        self.console.pack(pady=10, padx=20, fill="both", expand=True)
        self.console.insert("end", "Status: Ready\n")
        self.console.configure(state="disabled")
        
        # Progress Bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(pady=5, padx=20, fill="x")
        self.progress.set(0)
        
        # Start Button
        self.start_btn = ctk.CTkButton(self, text="Start Memory Dump", command=self.start_dump)
        self.start_btn.pack(pady=10)
        
    def browse_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".raw",
            filetypes=[("RAW files", "*.raw"), ("All files", "*.*")],
            initialfile="memory.raw"
        )
        if file_path:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file_path)
            
    def log_message(self, message):
        self.console.configure(state="normal")
        self.console.insert("end", f"{message}\n")
        self.console.see("end")
        self.console.configure(state="disabled")
    
    def check_privileges(self):
        if self.os_type == "Windows":
            if not ctypes.windll.shell32.IsUserAnAdmin():
                self.log_message("Error: Please run as Administrator")
                self.start_btn.configure(state="disabled")
        elif self.os_type == "Linux":
            if os.geteuid() != 0:
                self.log_message("Error: Please run with sudo")
                self.start_btn.configure(state="disabled")
    
    def validate_tools(self):
        if self.os_type == "Windows":
            self.dump_command = "winpmem.exe"
            if not shutil.which(self.dump_command):
                if os.path.exists(self.dump_command):
                    return True
                self.log_message("Error: winpmem.exe not found in PATH or current directory")
                return False
        elif self.os_type == "Linux":
            self.dump_command = "./linpmem"
            if not shutil.which(self.dump_command):
                self.log_message("Error: linpmem not found in PATH")
                return False
        return True
    
    def add_raw_extension(self, filename):
        if not filename.lower().endswith(".raw"):
            return filename + ".raw"
        return filename
    
    def run_dump(self):
        try:
            output_file = self.add_raw_extension(self.file_entry.get())
            output_file = os.path.abspath(output_file)
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                self.log_message(f"Creating directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)

            self.log_message(f"Starting memory dump to {output_file}")

            if self.os_type == "Windows":
                command = f'{self.dump_command} "{output_file}"'
                process = subprocess.run(
                    command, 
                    shell=True, 
                    check=True, 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                process = subprocess.run(
                    [self.dump_command,"--output",output_file],
                    check=True,
                    capture_output=True,
                    text=True
                )
            
            if process.stdout:
                self.log_message(process.stdout)
            self.log_message("Memory dump completed successfully")
            
        except subprocess.CalledProcessError as e:
            self.log_message(f"Error during memory dump (Code {e.returncode}):")
            if e.stderr:
                self.log_message(f"STDERR: {e.stderr}")
            if e.stdout:
                self.log_message(f"STDOUT: {e.stdout}")
        except Exception as e:
            self.log_message(f"Unexpected error: {str(e)}")
        finally:
            self.running = False
            self.start_btn.configure(state="normal")
            self.progress.stop()
    
    def start_dump(self):
        if not self.validate_tools():
            return
            
        output_file = self.file_entry.get()
        if not output_file:
            messagebox.showerror("Error", "Please specify an output file")
            return
            
        self.running = True
        self.start_btn.configure(state="disabled")
        self.progress.start()
        
        dump_thread = threading.Thread(target=self.run_dump, daemon=True)
        dump_thread.start()
        self.monitor_thread(dump_thread)
    
    def monitor_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.monitor_thread(thread))
        else:
            self.progress.stop()
            self.progress.set(0)

if __name__ == "__main__":
    app = MemoryDumpApp()
    app.mainloop()
