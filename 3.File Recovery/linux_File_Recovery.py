import os
import threading
from concurrent.futures import ThreadPoolExecutor
import sys
import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog

# Check if running with root privileges
if os.geteuid() != 0:
    messagebox.showerror("Error", "This script must be run as root. Please run with sudo.")
    sys.exit()

# Signatures for various file types
file_signatures = {
    "jpg": [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd9'],  # JPEG files
    "pdf": [b'%PDF-', b'%%EOF'],  # PDF files
    "png": [b'\x89PNG\r\n\x1a\n', b'\x49\x45\x4e\x44\xae\x42\x60\x82'],  # PNG files
    "gif": [b'GIF87a', b'GIF89a'],  # GIF files
    "mp3": [b'\x49\x44\x33', b'\xff\xf3'],  # MP3 files
    "zip": [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],  # ZIP files
    "rar": [b'Rar!\x1a\x07\x00', b'Rar!\x1a\x07\x01'],  # RAR files
    "7z": [b'7z\xbc\xaf\x27\x1c'],  # 7z archive files
    "doc": [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # Microsoft Office pre-2007 files
    "docx": [b'PK\x03\x04'],  # Microsoft Office 2007+ files (ZIP container)
    "xls": [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # Microsoft Excel pre-2007 files
    "xlsx": [b'PK\x03\x04'],  # Microsoft Excel 2007+ files (ZIP container)
    "exe": [b'MZ'],  # Executable files
    "dll": [b'MZ'],  # Dynamic Link Libraries (same signature as EXE)
    "bmp": [b'BM'],  # Bitmap image files
    "wav": [b'RIFF', b'WAVE'],  # WAV audio files
    "avi": [b'RIFF', b'AVI '],  # AVI video files
    "mov": [b'\x00\x00\x00\x14ftypqt'],  # MOV video files
    "mp4": [b'\x00\x00\x00\x18ftypmp4'],  # MP4 video files
    "flv": [b'FLV\x01'],  # Flash video files
    "webp": [b'RIFF', b'WEBP'],  # WEBP image files
    "iso": [b'\x43\x44\x30\x30\x31'],  # ISO disc image files
    "tar": [b'ustar'],  # TAR archive files
    "gz": [b'\x1f\x8b'],  # Gzip compressed files
    "json": [b'{', b'[' ],  # JSON files (starts with "{" or "[")
    "xml": [b'<?xml'],  # XML files
    "html": [b'<!DOCTYPE html', b'<html'],  # HTML files
    "css": [b'/*', b'@import'],  # CSS files
    "js": [b'//', b'function', b'var'],  # JavaScript files
    "py": [b'#', b'import ', b'def '],  # Python files
    "txt": [b''],  # Plain text files (no specific signature)
    "sqlite": [b'SQLite format 3\x00'],  # SQLite database files
    "tar.gz": [b'\x1f\x8b\x08'],  # Tarball gzip files
    "class": [b'\xca\xfe\xba\xbe'],  # Java class files
    "jar": [b'PK\x03\x04'],  # Java archive files
    "psd": [b'8BPS'],  # Photoshop files
    "tiff": [b'II*\x00', b'MM\x00*'],  # TIFF image files
    "epub": [b'PK\x03\x04'],  # EPUB files (ZIP container)
}


def check_drive_access(drive):
    """Check if we can access the drive."""
    try:
        with open(drive, "rb") as test_file:
            test_file.read(1024)
        return True
    except Exception as e:
        print(f"Error accessing the drive: {str(e)}")
        return False

def recover_file(drive, file_type, signature, save_path, size=512, stop_event=None,log_callback=None):
    try:
        with open(drive, "rb") as fileD:
            byte = fileD.read(size)
            offs = 0
            drec = False
            rcvd = 0

            while byte:
                # Check stop signal
                if stop_event and stop_event.is_set():
                    print("Stopping recovery process...")
                    break

                found = byte.find(signature[0])
                if found >= 0:
                    drec = True
                    recovery_start_offset = found + (size * offs)
                    
                    if log_callback:
                      log_callback(f'==== Found {file_type.upper()} at location: {hex(recovery_start_offset)} ====')

                    file_name = os.path.join(save_path, f'{file_type}_{rcvd}.{file_type}')
                    with open(file_name, "wb") as fileN:
                        fileN.write(byte[found:])

                        while drec and not (stop_event and stop_event.is_set()):
                            byte = fileD.read(size)
                            if not byte:
                                break
                            bfind = byte.find(signature[-1])  # Use last element as end marker
                            if bfind >= 0:
                                # Write up to the END of the end marker (critical fix)
                                fileN.write(byte[:bfind + len(signature[-1])])
                                if log_callback:
                                    log_callback(f'==== Found {file_type.upper()} at location: {hex(recovery_start_offset)} ====')
                                rcvd += 1
                                drec = False
                            else:
                                fileN.write(byte)
                byte = fileD.read(size)
                offs += 1

            if log_callback:
                log_callback(f'==== Found {file_type.upper()} at location: {hex(recovery_start_offset)} ====')
            
    except Exception as e:
        if log_callback:
            log_callback(f'==== Found {file_type.upper()} at location: {hex(recovery_start_offset)} ====')

def recover_files(drive, selected_file_types, save_path, size=512, stop_event=None,log_callback=None):
    """Main function to recover multiple file types."""
    if not check_drive_access(drive):
        messagebox.showerror("Error", f"Cannot access drive {drive}. Please ensure proper permissions.")
        return

    with ThreadPoolExecutor(max_workers=5) as executor:
        for file_type in selected_file_types:
            signature = file_signatures[file_type]
            executor.submit(recover_file, drive, file_type, signature, save_path, size, stop_event,log_callback)

def get_available_drives():
    """Get a list of available drives in Linux."""
    drives = []
    for drive in os.listdir("/dev"):
        if drive.startswith("sd") or drive.startswith("nvme"):  # Typical device names in Linux
            drive_path = f"/dev/{drive}"
            if os.path.exists(drive_path):
                drives.append(drive_path)
    return drives

class FileRecoveryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Linux File Recovery")
        self.geometry("1000x800")
        self.resizable(True, True)

        # UI Elements
        self.drive_label = ctk.CTkLabel(self, text="Select Drive:")
        self.drive_label.pack(pady=(20, 5))

        self.drive_var = ctk.StringVar(value="")
        self.drive_menu = ctk.CTkOptionMenu(self, variable=self.drive_var, values=get_available_drives())
        self.drive_menu.pack(pady=5)

        self.file_types_label = ctk.CTkLabel(self, text="Select File Types to Recover:")
        self.file_types_label.pack(pady=(20, 5))

        # Create a frame for file type checkboxes
        file_types_frame = ctk.CTkFrame(self)
        file_types_frame.pack(pady=10, padx=20)

        self.file_type_vars = {ftype: ctk.BooleanVar(value=False) for ftype in file_signatures.keys()}

        # Arrange file type checkboxes in a grid
        row, col = 0, 0
        for file_type, var in self.file_type_vars.items():
            checkbox = ctk.CTkCheckBox(file_types_frame, text=f".{file_type}", variable=var)
            checkbox.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            col += 1
            if col > 4:  # Adjust the number of columns as needed
                col = 0
                row += 1

        self.save_path_button = ctk.CTkButton(self, text="Select Save Path", command=self.select_save_path)
        self.save_path_button.pack(pady=5)

        self.start_button = ctk.CTkButton(self, text="Start Recovery", command=self.start_recovery)
        self.start_button.pack(pady=(20, 10))

        self.stop_button = ctk.CTkButton(self, text="Stop", command=self.stop_recovery)
        self.stop_button.pack(pady=5)

        self.log_text = ctk.CTkTextbox(self, height=100, width=550)
        self.log_text.pack(pady=(10, 20))

        # Initialize save path and recovery thread variable
        self.save_path = None
        self.recovery_thread = None
        self.stop_event = None

    def append_log(self, message):
        # Schedule the GUI update on the main thread
        self.after(0, lambda: self.log_text.insert("end", message + "\n"))
        self.after(0, lambda: self.log_text.see("end"))  # Auto-scroll

    def select_save_path(self):
        """Open a directory dialog to select the save path."""
        self.save_path = filedialog.askdirectory()
        if self.save_path:
            messagebox.showinfo("Save Path", f"Files will be saved to: {self.save_path}")

    def start_recovery(self):
        selected_drive = self.drive_var.get()
        if not selected_drive:
            messagebox.showwarning("Warning", "Please select a drive.")
            return
        
        if not self.save_path:
            messagebox.showwarning("Warning", "Please select a save path.")
            return
    
        selected_file_types = [ftype for ftype, var in self.file_type_vars.items() if var.get()]
        if not selected_file_types:
            messagebox.showwarning("Warning", "Please select at least one file type to recover.")
            return
        
        # Create a stop event that will allow us to signal the recovery thread to stop
        self.stop_event = threading.Event()
        
        self.log_text.insert("end", f"Starting recovery on {selected_drive} for {selected_file_types}...\n")
        self.recovery_thread = threading.Thread(
            target=recover_files, 
            args=(selected_drive, selected_file_types, self.save_path, 512, self.stop_event,self.append_log)
        )
        self.recovery_thread.start()

    def stop_recovery(self):
        """Stop the ongoing recovery process."""
        if self.recovery_thread and self.recovery_thread.is_alive():
            self.stop_event.set()  # Signal the recovery thread to stop
            self.recovery_thread.join()  # Wait for the thread to finish
            self.log_text.insert("end", "Recovery process stopped.\n")
        else:
            messagebox.showwarning("Warning", "No recovery process is running.")

if __name__ == "__main__":
    app = FileRecoveryApp()
    app.mainloop()
