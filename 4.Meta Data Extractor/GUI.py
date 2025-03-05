import customtkinter
from tkinter import filedialog, messagebox, Menu
import sys
from io import StringIO
import threading
import queue
import os
from Metalookup import extract_metadata, extract_metadata_from_directory, detect_file_type

# Redirect stderr to null (suppresses unwanted error messages)
sys.stderr = open(os.devnull, 'w')

class EnhancedMetalookupGUI(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Meta Data Extractor")
        self.geometry("1200x800")
        self._running = threading.Event()
        self._running.set()

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Create control frame
        self.control_frame = customtkinter.CTkFrame(self)
        self.control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Action buttons
        self.dir_button = customtkinter.CTkButton(
            self.control_frame, 
            text="📁 Select Directory",
            command=self.select_directory,
            width=120
        )
        self.dir_button.pack(side="left", padx=5)

        self.file_button = customtkinter.CTkButton(
            self.control_frame,
            text="📄 Select File",
            command=self.select_file,
            width=120
        )
        self.file_button.pack(side="left", padx=5)

        self.clear_button = customtkinter.CTkButton(
            self.control_frame,
            text="🧹 Clear Log",
            command=self.clear_log,
            width=120
        )
        self.clear_button.pack(side="left", padx=5)

        self.stop_button = customtkinter.CTkButton(
            self.control_frame,
            text="⏹ Stop",
            command=self.stop_processing,
            fg_color="#d9534f",
            hover_color="#c9302c",
            width=80
        )
        self.stop_button.pack(side="right", padx=5)

        # Filter frame
        self.filter_frame = customtkinter.CTkFrame(self)
        self.filter_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.file_type_filters = {
            "All": customtkinter.CTkCheckBox(self.filter_frame, text="All", command=self.toggle_all_filters),
            "PDF": customtkinter.CTkCheckBox(self.filter_frame, text="PDF"),
            "Images": customtkinter.CTkCheckBox(self.filter_frame, text="Images"),
            "Office": customtkinter.CTkCheckBox(self.filter_frame, text="Office"),
            "Video": customtkinter.CTkCheckBox(self.filter_frame, text="Video"),
            "EXE": customtkinter.CTkCheckBox(self.filter_frame, text="EXE")
        }

        for i, (_, cb) in enumerate(self.file_type_filters.items()):
            cb.pack(side="left", padx=5, pady=2)
        self.file_type_filters["All"].select()

        # Log frame
        self.log_frame = customtkinter.CTkFrame(self)
        self.log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

        # Log textbox
        self.log_text = customtkinter.CTkTextbox(self.log_frame, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.bind("<Button-3>", self.show_context_menu)

        # Progress bar
        self.progress = customtkinter.CTkProgressBar(self)
        self.progress.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        self.progress.set(0)

        # Status bar
        self.status_label = customtkinter.CTkLabel(self, text="Ready", anchor="w")
        self.status_label.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        # Right-click context menu
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected)
        self.context_menu.add_command(label="Save Selection", command=self.save_selection)

        # Theme menu
        self.menu = customtkinter.CTkOptionMenu(
            self,
            values=["Dark", "Light", "System"],
            command=self.change_theme,
            width=100
        )
        self.menu.grid(row=5, column=0, padx=10, pady=5, sticky="e")

        # Output handling
        self.queue = queue.Queue()
        self.after(100, self.process_queue)
        self.total_files = 0
        self.processed_files = 0

    def toggle_all_filters(self):
        all_selected = self.file_type_filters["All"].get()
        for ft, cb in self.file_type_filters.items():
            if ft != "All":
                cb.configure(state="normal" if not all_selected else "disabled")
                if all_selected:
                    cb.deselect()

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.start_processing(self.run_metalookup_directory, directory)

    def select_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.start_processing(self.run_metalookup_file, file_path)

    def start_processing(self, target, *args):
        if not self._running.is_set():
            messagebox.showwarning("Warning", "Another operation is already running!")
            return

        self._running.clear()
        self.progress.configure(mode="determinate")
        self.progress.set(0)
        self.status_label.configure(text="Processing...")
        self.total_files = 0
        self.processed_files = 0
        
        threading.Thread(
            target=target,
            args=args,
            daemon=True
        ).start()

    def stop_processing(self):
        self._running.set()
        self.progress.stop()
        self.progress.set(0)
        self.status_label.configure(text="Stopped")
        self.append_log("\n[ Operation stopped by user ]\n")

    def run_metalookup_directory(self, directory):
        try:
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()

            self.count_files(directory)
            
            for root, _, files in os.walk(directory):
                if self._running.is_set():
                    break
                
                for name in files:
                    if self._running.is_set():
                        break
                    
                    file_path = os.path.join(root, name)
                    if self.should_process_file(file_path):
                        try:
                            metadata = extract_metadata(file_path)
                            print(f"Metadata for {file_path}:\n{metadata}\n")
                        except Exception as e:
                            print(f"Error processing {file_path}: {str(e)}")
                        
                        self.processed_files += 1
                        self.queue.put(self.processed_files)

            sys.stdout = old_stdout
            self.queue.put(("output", captured_output.getvalue()))
            
        except Exception as e:
            self.queue.put(("error", f"\nFatal Error: {str(e)}\n"))
        finally:
            self.progress.stop()
            self.progress.set(0)
            self.status_label.configure(text="Ready")
            self._running.set()

    def count_files(self, directory):
        self.total_files = 0
        for root, _, files in os.walk(directory):
            for name in files:
                file_path = os.path.join(root, name)
                if self.should_process_file(file_path):
                    self.total_files += 1

    def should_process_file(self, file_path):
        if self.file_type_filters["All"].get():
            return True

        file_type = detect_file_type(file_path)
        selected_types = [ft for ft, cb in self.file_type_filters.items() 
                        if cb.get() and ft != "All"]

        type_mapping = {
            "PDF": ["PDF"],
            "Images": ["JPEG", "PNG", "GIF87a", "GIF89a", "BMP", "TIFF", "WebP"],
            "Office": ["ZIP or Office Document"],
            "Video": ["MP4", "MKV or WebM", "AVI", "MPEG", "3GP", "OGG/OGV", "FLV"],
            "EXE": ["EXE"]
        }

        for selected in selected_types:
            if file_type in type_mapping.get(selected, []):
                return True
        return False

    def run_metalookup_file(self, file_path):
        try:
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()

            metadata = extract_metadata(file_path)
            print(f"Metadata for {file_path}:")
            print(metadata)

            sys.stdout = old_stdout
            self.queue.put(("output", captured_output.getvalue()))
            
        except Exception as e:
            self.queue.put(("error", f"\nError: {str(e)}\n"))
        finally:
            self.progress.stop()
            self.progress.set(0)
            self.status_label.configure(text="Ready")
            self._running.set()

    def process_queue(self):
        while not self.queue.empty():
            item = self.queue.get_nowait()
            if isinstance(item, tuple):
                if item[0] == "output":
                    self.append_log(item[1])
                elif item[0] == "error":
                    self.append_log(item[1])
            else:
                progress = item / self.total_files
                self.progress.set(progress)
                self.status_label.configure(
                    text=f"Processing {item}/{self.total_files} files " 
                         f"({progress*100:.1f}%)"
                )
        self.after(100, self.process_queue)

    def append_log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def change_theme(self, choice):
        customtkinter.set_appearance_mode(choice)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_selected(self):
        selected_text = self.log_text.get("sel.first", "sel.last")
        self.clipboard_clear()
        self.clipboard_append(selected_text)

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def save_selection(self):
        selected_text = self.log_text.get("sel.first", "sel.last")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, "w") as f:
                f.write(selected_text)

if __name__ == "__main__":
    customtkinter.set_appearance_mode("Dark")
    customtkinter.set_default_color_theme("blue")
    app = EnhancedMetalookupGUI()
    app.mainloop()