import customtkinter
from tkinter import filedialog
import Winclone
import sys
import threading
import ctypes
import ctypes.wintypes
import os
import time

# Configure customtkinter appearance
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ''

    def write(self, text):
        self.buffer += text
        if '\n' in self.buffer:
            parts = self.buffer.split('\n')
            for part in parts[:-1]:
                self.text_widget.after(0, self.update_log, part + '\n')
            self.buffer = parts[-1]

    def flush(self):
        if self.buffer:
            self.text_widget.after(0, self.update_log, self.buffer)
            self.buffer = ''

    def update_log(self, text):
        self.text_widget.configure(state='normal')
        self.text_widget.insert('end', text)
        self.text_widget.configure(state='disabled')
        self.text_widget.see('end')

class DiskClonerApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Windows Disk Cloner")
        self.geometry("800x650")
        self.stop_event = threading.Event()
        self.total_size = 0
        self.clone_thread = None
        self.original_stdout = sys.stdout
        self.current_dest_file = None

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self.create_widgets()
        self.refresh_partitions()

    def create_widgets(self):
        # Partition Selection
        self.partition_label = customtkinter.CTkLabel(self, text="Source Partition:")
        self.partition_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        self.partition_combo = customtkinter.CTkComboBox(self, values=[], state="readonly")
        self.partition_combo.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.refresh_button = customtkinter.CTkButton(self, text="↻ Refresh", width=80, command=self.refresh_partitions)
        self.refresh_button.grid(row=1, column=1, padx=20, pady=5)

        # Destination Selection
        self.dest_label = customtkinter.CTkLabel(self, text="Destination File:")
        self.dest_label.grid(row=2, column=0, padx=20, pady=(20, 5), sticky="w")

        self.dest_entry = customtkinter.CTkEntry(self)
        self.dest_entry.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.browse_button = customtkinter.CTkButton(self, text="Browse...", width=80, command=self.select_destination)
        self.browse_button.grid(row=3, column=1, padx=20, pady=5)

        # Progress Bar
        self.progress_bar = customtkinter.CTkProgressBar(self)
        self.progress_bar.grid(row=4, column=0, columnspan=2, padx=20, pady=(20, 5), sticky="ew")
        self.progress_bar.set(0)

        # Control Buttons
        self.start_button = customtkinter.CTkButton(self, text="Start Clone", command=self.start_clone)
        self.start_button.grid(row=5, column=0, padx=20, pady=20, sticky="s")

        self.stop_button = customtkinter.CTkButton(self, text="Stop", fg_color="#d9534f", hover_color="#c9302c",
                                                 state="disabled", command=self.stop_clone)
        self.stop_button.grid(row=5, column=1, padx=20, pady=20, sticky="s")

        # Log Console
        self.log_text = customtkinter.CTkTextbox(self, wrap='word', state='disabled')
        self.log_text.grid(row=6, column=0, columnspan=2, padx=20, pady=(5, 20), sticky="nsew")

    def get_partition_size(self, device_path):
        """Get partition size using Windows API"""
        GENERIC_READ = 0x80000000
        OPEN_EXISTING = 3
        INVALID_HANDLE_VALUE = -1

        handle = ctypes.windll.kernel32.CreateFileW(
            device_path,
            GENERIC_READ,
            0,
            None,
            OPEN_EXISTING,
            0,
            None
        )

        if handle == INVALID_HANDLE_VALUE:
            raise ctypes.WinError()

        try:
            IOCTL_DISK_GET_LENGTH_INFO = 0x7405C
            class DiskLengthInfo(ctypes.Structure):
                _fields_ = [("Length", ctypes.c_ulonglong)]

            info = DiskLengthInfo()
            bytes_returned = ctypes.wintypes.DWORD()

            ctypes.windll.kernel32.DeviceIoControl(
                handle,
                IOCTL_DISK_GET_LENGTH_INFO,
                None,
                0,
                ctypes.byref(info),
                ctypes.sizeof(info),
                ctypes.byref(bytes_returned),
                None
            )
            return info.Length
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)

    def refresh_partitions(self):
        try:
            partitions = Winclone.list_partitions()
            values = [f"{p['device']} ({p['fstype']})" for p in partitions]
            self.partition_combo.configure(values=values)
            if values:
                self.partition_combo.set(values[0])
        except Exception as e:
            self.log(f"Error loading partitions: {str(e)}")

    def select_destination(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".dd",
            filetypes=[("Disk Image", "*.dd"), ("All Files", "*.*")]
        )
        if file_path:
            self.dest_entry.delete(0, 'end')
            self.dest_entry.insert(0, file_path)
            self.current_dest_file = file_path

    def log(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.configure(state='disabled')
        self.log_text.see('end')

    def start_clone(self):
        src = self.partition_combo.get().split()[0]
        dest = self.dest_entry.get()

        if not src or not dest:
            self.log("Error: Please select both partition and destination")
            return

        try:
            raw_src = f'\\\\.\\{src[0]}:' if not src.startswith('\\\\.\\') else src
            self.total_size = self.get_partition_size(raw_src)
            if self.total_size == 0:
                raise ValueError("Failed to get partition size")
        except Exception as e:
            self.log(f"Error: {str(e)}")
            return

        self.stop_event.clear()
        self.progress_bar.set(0)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.log("Starting clone process...")

        self.clone_thread = threading.Thread(
            target=self.run_clone,
            args=(src, dest),
            daemon=True
        )
        self.clone_thread.start()

    def run_clone(self, src, dest):
        try:
            sys.stdout = StdoutRedirector(self.log_text)
            
            def progress_update(bytes_copied):
                progress = bytes_copied / self.total_size
                self.progress_bar.set(progress)

            Winclone.clone_partition(src, dest, progress_update, self.stop_event)
            
            if self.stop_event.is_set():
                self.log("\nClone operation cancelled! Cleaning up...")
                self.cleanup_partial_file(dest)
            else:
                self.log("\nClone completed successfully!")
                self.progress_bar.set(1.0)
                
        except Exception as e:
            self.log(f"\nError: {str(e)}")
        finally:
            sys.stdout = self.original_stdout
            self.after(0, self.reset_ui)

    def cleanup_partial_file(self, dest):
        """Handle file deletion with retries and proper error handling"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if os.path.exists(dest):
                    os.remove(dest)
                    self.log(f"Successfully removed incomplete file: {dest}")
                    return
                else:
                    return
            except PermissionError as pe:
                if attempt == max_retries - 1:
                    self.log(f"Failed to remove file: {str(pe)}")
                    self.log("The file might still be in use. Please manually delete:")
                    self.log(dest)
                else:
                    self.log(f"Retrying file cleanup... ({attempt + 1}/{max_retries})")
                    time.sleep(0.5 * (attempt + 1))
            except Exception as e:
                self.log(f"Unexpected error during cleanup: {str(e)}")
                break

    def stop_clone(self):
        """Handle stop request safely"""
        self.stop_event.set()
        self.stop_button.configure(state="disabled")
        self.log("\nStop request received - waiting for processes to release files...")
        # Delay cleanup to allow handles to release
        self.after(500, self.cleanup_partial_file, self.dest_entry.get())

    def reset_ui(self):
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.current_dest_file = None

if __name__ == "__main__":
    app = DiskClonerApp()
    app.mainloop()