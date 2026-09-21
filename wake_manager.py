import subprocess
import sys
import ctypes
import os
import webbrowser
import threading
import tkinter as tk
from tkinter import messagebox, ttk

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
        return [line.strip() for line in result.stdout.split('\n') if line.strip()]
    except subprocess.CalledProcessError:
        return []

def center_window(window, width, height):
    """Calculates screen dimensions to center any Tkinter window dynamically."""
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

class WakeManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Wake Device Manager")
        
        center_window(self.root, 600, 600)
        
        self.setup_menu()
        
        history_frame = ttk.LabelFrame(root, text=" Last PC Wake Source History ", padding="10")
        history_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        self.history_text = tk.Text(history_frame, height=4, wrap=tk.WORD, font=("Consolas", 10), bg="#f5f5f5")
        self.history_text.pack(fill=tk.X, expand=True)
        self.history_text.config(state=tk.DISABLED) 
        
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        search_label = ttk.Label(search_frame, text="🔍 Search Filter: ", font=("Arial", 10))
        search_label.pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_devices())
        
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        label = ttk.Label(main_frame, text="Check devices to ALLOW waking the PC. Uncheck to DISABLE.", font=("Arial", 10, "bold"))
        label.pack(anchor=tk.W, pady=(0, 10))
        
        self.canvas = tk.Canvas(main_frame, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        btn_frame = ttk.Frame(root, padding="10")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.refresh_btn = ttk.Button(btn_frame, text="Refresh Everything", command=self.refresh_all)
        self.refresh_btn.pack(side=tk.RIGHT, padx=5)

        self.armed_devices = []
        self.all_capable_devices = []
        self.device_vars = {}
        
        self.last_toggled_device = None
        
        self.refresh_all()

    def setup_menu(self):
        """Creates a native application menu bar at the top of the window."""
        menubar = tk.Menu(self.root)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def show_about(self):
        """Displays a custom branded Informational window with a grid layout to prevent text clipping."""
        about_win = tk.Toplevel(self.root)
        about_win.title("About This Tool")
        about_win.resizable(False, False)
        
        center_window(about_win, 460, 220)
        
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
            
        real_logo_path = os.path.join(base_path, "logo.png")
        
        btn_frame = ttk.Frame(about_win, padding="10")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        close_btn = ttk.Button(btn_frame, text="OK", command=about_win.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)
        
        content_frame = ttk.Frame(about_win, padding="15")
        content_frame.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
        
        try:
            full_img = tk.PhotoImage(file=real_logo_path)
            logo_img = full_img.subsample(2, 2)
            about_win.image_reference = logo_img 
            
            logo_label = ttk.Label(content_frame, image=logo_img)
            logo_label.grid(row=0, column=0, sticky=tk.N, padx=(0, 15))
        except Exception as e:
            print(f"Image load failed: {e}")
            logo_label = ttk.Label(content_frame, text="[Logo]")
            logo_label.grid(row=0, column=0, sticky=tk.N, padx=(0, 15))

        youtube_link = tk.Label(
            content_frame, 
            text="My Youtube", 
            fg="#0066cc", 
            font=("Arial", 10, "underline"),
            cursor="hand2"
        )
        youtube_link.grid(row=1, column=0, sticky=tk.N, pady=(8, 0), padx=(0, 15))
        youtube_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://youtube.com/@desicyt"))

        about_text = """System Wake Device Manager v1.0

Made by Desic

A GUI wrapper for the native Windows powercfg utility.
For when you just can't put the PC to sleep."""
        
        text_label = ttk.Label(content_frame, text=about_text, justify=tk.LEFT)
        text_label.grid(row=0, column=1, rowspan=2, sticky=tk.NW)


    def refresh_all(self):
        """Disables controls, fires up a non-blocking loading window, and runs hardware queries."""
        self.search_entry.delete(0, tk.END)
        self.last_toggled_device = None
        self.refresh_btn.config(state=tk.DISABLED)
        
        self.loading_win = tk.Toplevel(self.root)
        self.loading_win.title("Scanning Hardware")
        self.loading_win.resizable(False, False)
        
        self.loading_win.transient(self.root)
        self.loading_win.grab_set()
        center_window(self.loading_win, 350, 120)
        
        lbl = ttk.Label(self.loading_win, text="Scanning for wake armed devices.\nPlease wait, filtering duplicate profiles.", font=("Arial", 10), justify=tk.CENTER)
        lbl.pack(pady=(15, 10))
        
        progress = ttk.Progressbar(self.loading_win, mode="indeterminate", length=250)
        progress.pack(pady=5)
        progress.start(10)
        
        self.loading_win.protocol("WM_DELETE_WINDOW", lambda: None)
        
        threading.Thread(target=self._async_load_worker, daemon=True).start()

    def _async_load_worker(self):
        """Asynchronous execution logic handling heavy platform data extraction loops."""
        self.load_last_wake_history()
        self.fetch_system_devices()
        
        self.root.after(0, self._finalize_ui_load)

    def _finalize_ui_load(self):
        """Closes loading splash screens smoothly and builds checkboxes."""
        self.filter_devices()
        self.refresh_btn.config(state=tk.NORMAL)
        
        if hasattr(self, 'loading_win') and self.loading_win.winfo_exists():
            self.loading_win.grab_release()
            self.loading_win.destroy()

    def load_last_wake_history(self):
        wake_info_lines = run_command(["powercfg", "/lastwake"])
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        
        if wake_info_lines:
            self.history_text.insert(tk.END, "\n".join(wake_info_lines))
        else:
            self.history_text.insert(tk.END, "Could not retrieve last wake device history.")
            
        self.history_text.config(state=tk.DISABLED)

    def is_device_modifiable(self, device_name, is_currently_armed):
        test_action = "/devicedisablewake" if is_currently_armed else "/deviceenablewake"
        revert_action = "/deviceenablewake" if is_currently_armed else "/devicedisablewake"
        
        try:
            res1 = subprocess.run(["powercfg", test_action, device_name], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res1.returncode != 0:
                return False
            
            subprocess.run(["powercfg", revert_action, device_name], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except:
            return False

    def fetch_system_devices(self):
        raw_armed = run_command(["powercfg", "/devicequery", "wake_armed"])
        raw_all = run_command(["powercfg", "/devicequery", "wake_from_any"])
        
        self.armed_devices = []
        self.all_capable_devices = []
        
        for device in raw_all:
            is_armed = device in raw_armed
            if self.is_device_modifiable(device, is_armed):
                self.all_capable_devices.append(device)
                if is_armed:
                    self.armed_devices.append(device)

    def filter_devices(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.device_vars.clear()
        
        if not self.all_capable_devices:
            no_device_lbl = ttk.Label(self.scrollable_frame, text="No editable wake-capable devices found.", font=("Arial", 10, "italic"))
            no_device_lbl.pack(pady=20, padx=10)
            return

        search_query = self.search_var.get().lower()

        def sorting_key(device_name):
            is_armed = device_name in self.armed_devices
            return (0 if is_armed else 1, device_name.lower())

        sorted_devices = sorted(self.all_capable_devices, key=sorting_key)

        style = ttk.Style()
        style.configure("Toggled.TFrame", background="#e1f5fe") 

        for device in sorted_devices:
            if search_query and search_query not in device.lower():
                continue
                
            is_armed = device in self.armed_devices
            var = tk.BooleanVar(value=is_armed)
            self.device_vars[device] = var
            
            is_last_changed = (device == self.last_toggled_device)
            
            chk_frame = ttk.Frame(
                self.scrollable_frame, 
                padding=2, 
                style="Toggled.TFrame" if is_last_changed else ""
            )
            chk_frame.pack(fill=tk.X, anchor=tk.W)
            
            if is_last_changed:
                label_text = f"📍 [CHANGED] {device}"
            else:
                label_text = f"⚙️ {device}" if is_armed else device
            
            chk = ttk.Checkbutton(
                chk_frame, 
                text=label_text, 
                variable=var,
                command=lambda d=device, v=var: self.toggle_wake(d, v)
            )
            chk.pack(anchor=tk.W, padx=5)

    def toggle_wake(self, device_name, var):
        cmd = ["powercfg", "/deviceenablewake" if var.get() else "/devicedisablewake", device_name]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            self.last_toggled_device = device_name
            
            raw_armed = run_command(["powercfg", "/devicequery", "wake_armed"])
            self.armed_devices = [d for d in self.all_capable_devices if d in raw_armed]
            self.filter_devices()
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to modify {device_name}.\nError info: {e.stderr}")
            var.set(not var.get())

if __name__ == "__main__":
    if not is_admin():
        if getattr(sys, 'frozen', False):
            executable = sys.executable
            arguments = subprocess.list2cmdline(sys.argv[1:])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, arguments, None, 1)
            sys.exit()
        else:
            root = tk.Tk()
            root.title("Permissions Required")
            center_window(root, 450, 160)
            
            lbl = ttk.Label(
                root, 
                text="Administrator Privileges Required!\n\nTo test this script without compiling it, open your terminal\n(Command Prompt or PowerShell) As Administrator, then type:\n\npython wake_manager.py", 
                font=("Arial", 10), 
                justify=tk.CENTER
            )
            lbl.pack(expand=True, pady=10)
            root.mainloop()
            sys.exit()

    root = tk.Tk()
    app = WakeManagerApp(root)
    root.mainloop()
