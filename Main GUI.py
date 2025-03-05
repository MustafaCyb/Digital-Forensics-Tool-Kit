import subprocess
import os
import platform
import sys
import ctypes
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ForensicGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Digital Forensic Toolkit")
        self.geometry("600x400")
        self.resizable(False, False)
        self.check_privileges()
        self.create_widgets()
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def check_privileges(self):
        os_type = platform.system()
        if os_type == "Windows":
            if not ctypes.windll.shell32.IsUserAnAdmin():
                messagebox.showerror("Error", "Please Run the Program as Admin")
                sys.exit(-1)
        elif os_type == "Linux":
            if os.geteuid() != 0:
                messagebox.showerror("Error", "This script must be run as root. Please run with sudo.")
                sys.exit()
        else:
            ctk.messagebox.showerror("Error", "Unsupported OS")
            sys.exit()

    def create_widgets(self):
        # Main container
        main_frame = ctk.CTkFrame(self, corner_radius=15)
        main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Header
        header_label = ctk.CTkLabel(main_frame, 
                                  text="Digital Forensic Toolkit",
                                  font=("Roboto Medium", 24))
        header_label.pack(pady=20)

        # Tool grid
        tools_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tools_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Tool buttons
        tools = [
            ("Memory Dump", "1", "📝"),
            ("Network Forensics", "2", "🌐"),
            ("File Recovery", "3", "🔍"),
            ("Meta Data Extractor", "4", "📄"),
            ("Disk Imaging", "5", "💾"),
            ("Exit", "6", "🚪")
        ]

        for i, (name, num, icon) in enumerate(tools):
            btn = ctk.CTkButton(tools_frame,
                              text=f"{icon}\n{name}",
                              command=lambda n=num: self.handle_choice(n),
                              width=200,
                              height=120,
                              corner_radius=10,
                              font=("Roboto", 14),
                              compound="top")
            btn.grid(row=i//3, column=i%3, padx=10, pady=10)

    def handle_choice(self, choice):
        if choice == "6":
            self.destroy()
            return

        script_dirs = {
            "1": "1.Memory Capture",
            "2": "2.Network forensics",
            "3": "3.File Recovery",
            "4": "4.Meta Data Extractor",
            "5": "5.Disk Imaging"
        }

        if choice == "3":
            script_name = "Windows_File_Recovery.py" if platform.system() == "Windows" else "linux_File_Recovery.py"
            self.run_script(os.path.join(os.getcwd(), script_dirs[choice]), script_name)
        elif choice == "5":
            subdir = "Windows Cloner" if platform.system() == "Windows" else "Linux Cloner"
            self.run_script(os.path.join(os.getcwd(), script_dirs[choice], subdir))
        else:
            self.run_script(os.path.join(os.getcwd(), script_dirs[choice]))

    def run_script(self, script_directory, script_name="GUI.py"):
        script_path = os.path.join(script_directory, script_name)
        if not os.path.isfile(script_path):
            messagebox.showerror("Error", f"Script not found: {script_path}")
            return

        try:
            subprocess.run(["python", script_path], cwd=script_directory, check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to execute script: {e}")



if __name__ == "__main__":
    app = ForensicGUI()
    app.mainloop()
