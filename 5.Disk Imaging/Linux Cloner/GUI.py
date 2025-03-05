import customtkinter
from tkinter import filedialog
import Lincloner
import sys
import threading
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

class LinuxDiskCloner(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Linux Disk Cloner")
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
        self.check_root()

    def check_root(self):
        if os.geteuid() != 0:
            self.log_text.configure(state='normal')
            self.log_text.insert('end', "ERROR: This application requires root privileges!\n")
            self.log_text.insert('end', "Please run with sudo:\n$ sudo python GUI.py\n")
            self.log_text.configure(state='disabled')
            self.start_button.configure(state="disabled")

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

    def refresh_partitions(self):
        try:
            partitions = Lincloner.list_partitions()
            values = [f"{p['device']} ({p['fstype']} - {p['total_size']//(1024**3)}GB)" for p in partitions]
            self.partition_combo.configure(values=values)
            if values:
                self.partition_combo.set(values[0])
        except Exception as e:
            self.log(f"Error loading partitions: {str(e)}")

    def select_destination(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".img",
            filetypes=[("Disk Image", "*.img"), ("All Files", "*.*")]
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

        if not src.startswith('/dev/'):
            self.log("Error: Invalid device path")
            return

        if not dest:
            self.log("Error: Please select destination file")
            return

        try:
            # Get device size using Linux block device handling
            fd = os.open(src, os.O_RDONLY | os.O_NONBLOCK)
            try:
                self.total_size = os.lseek(fd, 0, os.SEEK_END)
                if self.total_size == 0:
                    raise ValueError("Failed to get partition size - is this a valid block device?")
                
                self.log(f"Device size: {self.total_size//(1024**3)} GB")
            finally:
                os.close(fd)

            # Check available disk space
            dest_dir = os.path.dirname(os.path.abspath(dest))
            stat = os.statvfs(dest_dir)
            free_space = stat.f_frsize * stat.f_bavail
            if free_space < self.total_size:
                raise ValueError(f"Not enough space in {dest_dir}. Need {self.total_size//(1024**3)}GB, available {free_space//(1024**3)}GB")

            # Confirm overwrite
            if os.path.exists(dest):
                confirm = input(f"Overwrite existing file {dest}? (y/N): ")
                if confirm.lower() != 'y':
                    self.log("Operation cancelled")
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

        except PermissionError as pe:
            self.log(f"Permission error: {str(pe)}")
            self.log("Make sure to run with sudo and that the user has read access to the block device")
        except OSError as ose:
            self.log(f"OS error: {str(ose)}")
            self.log("The device might be busy or not exist")
        except Exception as e:
            self.log(f"Error: {str(e)}")

    def run_clone(self, src, dest):
        try:
            sys.stdout = StdoutRedirector(self.log_text)
            
            def progress_update(current, total):
                progress = current / total
                self.progress_bar.set(progress)

            # Pass stop_event correctly as keyword argument
            if Lincloner.clone_partition(
                src, 
                dest, 
                progress_callback=progress_update,
                stop_event=self.stop_event
            ):
                self.log("\nClone completed successfully!")
                self.log("Verifying checksum... (add verification logic here)")
            
        except Exception as e:
            self.log(f"\nError: {str(e)}")
        finally:
            sys.stdout = self.original_stdout
            self.after(0, self.reset_ui)


    def stop_clone(self):
        self.stop_event.set()
        self.stop_button.configure(state="disabled")
        self.log("\nStop request received - cleaning up...")
        self.after(500, self.cleanup_partial_file, self.dest_entry.get())

    def cleanup_partial_file(self, dest):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if os.path.exists(dest):
                    os.remove(dest)
                    self.log(f"Removed incomplete file: {dest}")
                    return
            except Exception as e:
                if attempt == max_retries - 1:
                    self.log(f"Failed to remove file: {str(e)}")
                    self.log("Please delete manually: " + dest)

    def reset_ui(self):
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.current_dest_file = None

if __name__ == "__main__":
    app = LinuxDiskCloner()
    app.mainloop()
