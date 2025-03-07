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
        self.title("Forensic Toolkit")

        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Set window size to 60% width, 70% height
        win_width = int(screen_width * 0.6)
        win_height = int(screen_height * 0.7)

        # Calculate center position
        x_position = (screen_width - win_width) // 2
        y_position = (screen_height - win_height) // 2

        # Set geometry and center window
        self.geometry(f"{win_width}x{win_height}+{x_position}+{y_position}")
        self.resizable(False, False)  # Set to (True, True) if you want resizing

        # Create UI elements
        self.create_widgets()

    def create_widgets(self):
        # Main container frame
        main_frame = ctk.CTkFrame(self, corner_radius=15)
        main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Header label
        header_label = ctk.CTkLabel(
            main_frame, text="Digital Forensic Toolkit", font=("Roboto Medium", 24)
        )
        header_label.pack(pady=20)

        # Tools grid frame
        tools_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tools_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Tool buttons with Unicode icons
        tools = [
            ("Memory Dump", "1", "📝"),
            ("Network Forensics", "2", "🌐"),
            ("File Recovery", "3", "🔍"),
            ("Meta Data Extractor", "4", "📄"),
            ("Disk Imaging", "5", "💾"),
            ("Exit", "6", "🚪"),
        ]

        for i, (name, num, icon) in enumerate(tools):
            btn = ctk.CTkButton(
                tools_frame,
                text=f"{icon}\n{name}",
                command=lambda n=num: self.handle_choice(n),
                width=200,
                height=100,
                corner_radius=10,
                font=("Roboto", 14),
                compound="top",
            )
            btn.grid(row=i // 3, column=i % 3, padx=10, pady=10)

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
