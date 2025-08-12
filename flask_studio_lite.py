#!/usr/bin/env python3
"""
Universal Flask Studio - Smart Flask Development Server Manager
Works with any Flask project structure
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import subprocess
import threading
import socket
import webbrowser
import json
import time
from pathlib import Path


class UniversalFlaskStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Flask Studio")
        self.root.geometry("800x650")

        # Server state
        self.server_process = None
        self.server_running = False
        self.project_path = ""
        self.config_file = "flask_studio_config.json"

        # Load config and create GUI
        self.load_config()
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(9, weight=1)  # Changed from row 8 to row 9

        # Title
        title_label = ttk.Label(main_frame, text="🌶️ Universal Flask Studio",
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Project Directory
        ttk.Label(main_frame, text="Project Directory:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w",
                                                                                          pady=5)

        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5, padx=(10, 0))
        dir_frame.columnconfigure(0, weight=1)

        self.dir_var = tk.StringVar(value=self.project_path)
        ttk.Entry(dir_frame, textvariable=self.dir_var, state="readonly").grid(row=0, column=0, sticky="ew",
                                                                               padx=(0, 10))
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).grid(row=0, column=1)

        # Flask App Setting
        ttk.Label(main_frame, text="Flask App:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=5)

        app_frame = ttk.Frame(main_frame)
        app_frame.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5, padx=(10, 0))
        app_frame.columnconfigure(0, weight=1)

        self.flask_app_var = tk.StringVar()
        ttk.Entry(app_frame, textvariable=self.flask_app_var).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(app_frame, text="Auto-Detect", command=self.auto_detect_flask_app).grid(row=0, column=1)

        # Python Path
        ttk.Label(main_frame, text="Python Executable:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w",
                                                                                          pady=5)

        python_frame = ttk.Frame(main_frame)
        python_frame.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5, padx=(10, 0))
        python_frame.columnconfigure(0, weight=1)

        self.python_var = tk.StringVar(value=sys.executable)
        ttk.Entry(python_frame, textvariable=self.python_var).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(python_frame, text="Auto-Detect", command=self.detect_python).grid(row=0, column=1)

        # Port and options
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        options_frame.columnconfigure(2, weight=1)

        ttk.Label(options_frame, text="Port:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w",
                                                                                padx=(0, 10))
        self.port_var = tk.StringVar(value="5000")
        ttk.Spinbox(options_frame, from_=5000, to=9999, textvariable=self.port_var, width=8).grid(row=0, column=1,
                                                                                                  padx=(0, 20))

        self.auto_port_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Auto-find available port", variable=self.auto_port_var).grid(row=0,
                                                                                                          column=2,
                                                                                                          sticky="w")

        # Debug and reload options
        debug_frame = ttk.Frame(main_frame)
        debug_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)

        self.debug_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(debug_frame, text="Debug mode", variable=self.debug_var).grid(row=0, column=0, sticky="w",
                                                                                      padx=(0, 20))

        self.reload_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(debug_frame, text="Auto-reload on changes", variable=self.reload_var).grid(row=0, column=1,
                                                                                                   sticky="w")

        # Host option
        host_frame = ttk.Frame(main_frame)
        host_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=5)

        ttk.Label(host_frame, text="Host:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.host_var = tk.StringVar(value="127.0.0.1")
        host_combo = ttk.Combobox(host_frame, textvariable=self.host_var, values=["127.0.0.1", "localhost", "0.0.0.0"],
                                  width=15)
        host_combo.grid(row=0, column=1, sticky="w")

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, pady=20)

        self.start_btn = ttk.Button(button_frame, text="▶️ Start Server", command=self.start_server)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="⏹️ Stop Server", command=self.stop_server, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5)

        self.browser_btn = ttk.Button(button_frame, text="🌐 Open Browser", command=self.open_browser, state="disabled")
        self.browser_btn.grid(row=0, column=2, padx=5)

        self.test_btn = ttk.Button(button_frame, text="🧪 Test Config", command=self.test_config)
        self.test_btn.grid(row=0, column=3, padx=5)

        # Status with clickable URL
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=8, column=0, columnspan=3, pady=(10, 20))

        self.status_var = tk.StringVar(value="Ready - Select a project directory to begin")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 10, "bold"))
        self.status_label.grid(row=0, column=0)

        # Clickable URL label (initially hidden)
        self.url_label = tk.Label(status_frame, text="", fg="blue", font=("Arial", 10, "bold", "underline"),
                                  cursor="hand2")
        self.url_label.grid(row=0, column=1, padx=(10, 0))
        self.url_label.bind("<Button-1>", self.on_url_click)
        self.url_label.grid_remove()  # Hide initially

        # Console output
        console_frame = ttk.Frame(main_frame)
        console_frame.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=(0, 0))
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(1, weight=1)

        ttk.Label(console_frame, text="Console Output:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w",
                                                                                          pady=(0, 5))

        self.console_text = scrolledtext.ScrolledText(console_frame, height=15, bg="#1e1e1e", fg="#ffffff",
                                                      font=("Consolas", 9))
        self.console_text.grid(row=1, column=0, sticky="nsew")

        # Console controls
        console_controls = ttk.Frame(console_frame)
        console_controls.grid(row=2, column=0, sticky="w", pady=(5, 0))
        ttk.Button(console_controls, text="Clear", command=self.clear_console).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(console_controls, text="Save Log", command=self.save_log).grid(row=0, column=1)

        # Welcome message
        self.log("🌶️ Universal Flask Studio initialized")
        self.log("📁 Select a project directory to get started")

    def on_url_click(self, event):
        """Handle clicking on the server URL"""
        if self.server_running:
            self.open_browser()

    def update_status_with_url(self, message, url=None):
        """Update status with optional clickable URL"""
        self.status_var.set(message)

        if url and self.server_running:
            self.url_label.config(text=url)
            self.url_label.grid()  # Show the URL label
        else:
            self.url_label.grid_remove()  # Hide the URL label

    def browse_directory(self):
        """Browse for Flask project directory"""
        directory = filedialog.askdirectory(
            title="Select Flask Project Directory",
            initialdir=self.project_path or os.getcwd()
        )
        if directory:
            self.project_path = directory
            self.dir_var.set(directory)
            self.log(f"📁 Selected project: {directory}")
            self.auto_detect_flask_app()
            self.detect_python()
            self.save_config()

    def auto_detect_flask_app(self):
        """Smart detection of Flask app with multiple strategies"""
        if not self.project_path:
            return

        self.log("🔍 Auto-detecting Flask app...")

        # Strategy 1: Look for common patterns
        patterns = [
            # WSGI patterns (most common in production)
            "wsgi:app", "wsgi:application",

            # App factory patterns
            "app:create_app()", "app:create_app",

            # Direct app patterns
            "app:app", "app.py:app", "main.py:app", "run.py:app", "server.py:app",

            # Application patterns
            "application:app", "application.py:app",

            # Project-specific patterns
            f"{os.path.basename(self.project_path).lower()}:app",
        ]

        # Strategy 2: Test each pattern
        for pattern in patterns:
            if self.test_flask_app(pattern):
                self.flask_app_var.set(pattern)
                self.log(f"✅ Detected Flask app: {pattern}")
                return

        # Strategy 3: Scan for Flask files
        flask_files = self.find_flask_files()
        if flask_files:
            # Try the most promising file
            for flask_file in flask_files:
                test_patterns = [f"{flask_file}:app", f"{flask_file}:application", f"{flask_file}:create_app"]
                for pattern in test_patterns:
                    if self.test_flask_app(pattern):
                        self.flask_app_var.set(pattern)
                        self.log(f"✅ Found Flask app: {pattern}")
                        return

            # Fallback to first file found
            first_file = flask_files[0]
            app_setting = f"{first_file}:app"
            self.flask_app_var.set(app_setting)
            self.log(f"⚠️ Using best guess: {app_setting}")
        else:
            self.log("❌ No Flask app detected - please set manually")

    def find_flask_files(self):
        """Find Python files that likely contain Flask apps"""
        flask_files = []

        # Check root directory first
        root_files = []
        for file in os.listdir(self.project_path):
            if file.endswith('.py'):
                file_path = os.path.join(self.project_path, file)
                if self.is_flask_file(file_path):
                    module_name = file.replace('.py', '')
                    root_files.append(module_name)

        # Prioritize certain filenames
        priority_files = ['wsgi', 'app', 'main', 'run', 'server', 'application']
        for priority in priority_files:
            if priority in root_files:
                flask_files.insert(0, priority)
                root_files.remove(priority)

        flask_files.extend(root_files)

        # Then check subdirectories (limited depth)
        for root, dirs, files in os.walk(self.project_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if
                       not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.venv', 'env',
                                                           '.env']]

            # Limit depth to avoid going too deep
            depth = root.replace(self.project_path, '').count(os.sep)
            if depth >= 2:
                dirs.clear()
                continue

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    if self.is_flask_file(file_path):
                        rel_path = os.path.relpath(file_path, self.project_path)
                        module = rel_path.replace(os.sep, '.').replace('.py', '')
                        if module not in flask_files:
                            flask_files.append(module)

        return flask_files

    def is_flask_file(self, file_path):
        """Check if a Python file contains Flask code"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                flask_indicators = [
                    'from flask import', 'import flask', 'Flask(__name__)', 'Flask(',
                    '@app.route', 'app = Flask', 'application = Flask',
                    'create_app()', 'def create_app'
                ]
                return any(indicator in content for indicator in flask_indicators)
        except:
            return False

    def test_flask_app(self, flask_app_setting):
        """Test if a Flask app setting works"""
        if not self.project_path:
            return False

        try:
            # Quick syntax check first
            if ':' not in flask_app_setting:
                return False

            test_cmd = [
                self.python_var.get(), '-c',
                f'import os; os.chdir(r"{self.project_path}"); '
                f'import sys; sys.path.insert(0, r"{self.project_path}"); '
                f'import os; os.environ["FLASK_APP"] = "{flask_app_setting}"; '
                f'from flask.cli import ScriptInfo; '
                f'info = ScriptInfo(); app = info.load_app(); print("OK")'
            ]

            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            return result.returncode == 0 and "OK" in result.stdout
        except:
            return False

    def detect_python(self):
        """Auto-detect Python executable (prioritize virtual environments)"""
        if not self.project_path:
            return

        self.log("🐍 Detecting Python executable...")

        # Check for virtual environments
        venv_patterns = ['.venv', 'venv', '.env', 'env', 'virtualenv']

        for pattern in venv_patterns:
            venv_path = os.path.join(self.project_path, pattern)

            # Windows
            python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
            if os.path.exists(python_exe):
                self.python_var.set(python_exe)
                self.log(f"✅ Found virtual environment: {pattern}")
                return

            # Unix/Linux/Mac
            python_exe = os.path.join(venv_path, 'bin', 'python')
            if os.path.exists(python_exe):
                self.python_var.set(python_exe)
                self.log(f"✅ Found virtual environment: {pattern}")
                return

        # Fallback to system Python
        self.log("⚠️ Using system Python (no virtual environment found)")

    def test_config(self):
        """Test the current configuration"""
        if not self.project_path:
            messagebox.showerror("Error", "Please select a project directory first!")
            return

        self.log("🧪 Testing configuration...")

        # Test 1: Directory exists
        if not os.path.exists(self.project_path):
            self.log("❌ Project directory does not exist")
            return

        # Test 2: Python executable
        if not os.path.exists(self.python_var.get()):
            self.log("❌ Python executable not found")
            return
        else:
            self.log("✅ Python executable found")

        # Test 3: Flask app
        if not self.flask_app_var.get().strip():
            self.log("❌ No Flask app specified")
            return

        if self.test_flask_app(self.flask_app_var.get()):
            self.log("✅ Flask app configuration is valid")
        else:
            self.log("❌ Flask app configuration failed")
            return

        # Test 4: Port availability
        try:
            port = int(self.port_var.get())
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.host_var.get(), port))
                self.log(f"✅ Port {port} is available")
        except:
            self.log(f"⚠️ Port {port} may be in use")

        self.log("🎉 Configuration test completed!")

    def find_available_port(self, start_port=5000):
        """Find an available port"""
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.host_var.get(), port))
                    return port
            except OSError:
                continue
        return start_port

    def start_server(self):
        """Start the Flask development server"""
        if self.server_running:
            messagebox.showwarning("Warning", "Server is already running!")
            return

        if not self.project_path:
            messagebox.showerror("Error", "Please select a project directory!")
            return

        if not self.flask_app_var.get().strip():
            messagebox.showerror("Error", "Please set the Flask app or use Auto-Detect!")
            return

        # Determine port
        try:
            port = int(self.port_var.get())
        except ValueError:
            port = 5000

        if self.auto_port_var.get():
            original_port = port
            port = self.find_available_port(port)
            if port != original_port:
                self.port_var.set(str(port))
                self.log(f"🔄 Port {original_port} was busy, using {port}")

        # Start server in thread
        self.server_thread = threading.Thread(target=self._run_server, args=(port,), daemon=True)
        self.server_thread.start()

        # Update UI
        self.server_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.browser_btn.config(state="normal")

        # Create clickable status
        host_display = "localhost" if self.host_var.get() in ["127.0.0.1", "0.0.0.0"] else self.host_var.get()
        url = f"http://{host_display}:{port}"
        self.update_status_with_url("🟢 Server running on", url)

        self.log("🚀 Starting Flask server...")
        self.log(f"📁 Directory: {self.project_path}")
        self.log(f"🌶️ Flask App: {self.flask_app_var.get()}")
        self.log(f"🔌 Host: {self.host_var.get()}:{port}")
        self.log("-" * 50)

    def _run_server(self, port):
        """Run the Flask server"""
        try:
            env = os.environ.copy()
            env['FLASK_APP'] = self.flask_app_var.get()
            env['FLASK_ENV'] = 'development' if self.debug_var.get() else 'production'
            env['FLASK_DEBUG'] = '1' if self.debug_var.get() else '0'

            cmd = [
                self.python_var.get(), '-m', 'flask', 'run',
                f'--host={self.host_var.get()}',
                f'--port={port}'
            ]

            if self.reload_var.get():
                cmd.append('--reload')

            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env=env,
                cwd=self.project_path
            )

            # Read output
            for line in iter(self.server_process.stdout.readline, ''):
                if line.strip():
                    self.root.after(0, lambda l=line.strip(): self.log(l))

                if self.server_process.poll() is not None:
                    break

        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Error: {str(e)}"))

        # Server stopped
        self.root.after(0, self._server_stopped)

    def stop_server(self):
        """Stop the Flask server"""
        if self.server_process:
            self.log("🛑 Stopping server...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            except:
                pass
            self.server_process = None
        self._server_stopped()

    def _server_stopped(self):
        """Update UI when server stops"""
        self.server_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.browser_btn.config(state="disabled")
        self.update_status_with_url("🔴 Server stopped")
        self.log("🔴 Server stopped")

    def open_browser(self):
        """Open browser to the running server"""
        if self.server_running:
            host = self.host_var.get()
            port = self.port_var.get()
            # Convert host to localhost for browser
            browser_host = "localhost" if host in ["127.0.0.1", "0.0.0.0"] else host
            url = f"http://{browser_host}:{port}"
            webbrowser.open(url)
            self.log(f"🌐 Opened browser: {url}")

    def log(self, message):
        """Add message to console"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.console_text.insert(tk.END, formatted_message)
        self.console_text.see(tk.END)

        # Limit console to 1000 lines
        lines = int(self.console_text.index('end-1c').split('.')[0])
        if lines > 1000:
            self.console_text.delete('1.0', '100.0')

    def clear_console(self):
        """Clear the console"""
        self.console_text.delete('1.0', tk.END)
        self.log("Console cleared")

    def save_log(self):
        """Save console log to file"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Console Log"
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.console_text.get("1.0", tk.END))
                self.log(f"💾 Log saved to: {filename}")
        except Exception as e:
            self.log(f"❌ Error saving log: {str(e)}")

    def save_config(self):
        """Save configuration"""
        config = {
            'project_path': self.project_path,
            'flask_app': self.flask_app_var.get() if hasattr(self, 'flask_app_var') else '',
            'port': self.port_var.get() if hasattr(self, 'port_var') else '5000',
            'host': self.host_var.get() if hasattr(self, 'host_var') else '127.0.0.1',
            'python_path': self.python_var.get() if hasattr(self, 'python_var') else sys.executable,
            'debug': self.debug_var.get() if hasattr(self, 'debug_var') else True,
            'reload': self.reload_var.get() if hasattr(self, 'reload_var') else True,
            'auto_port': self.auto_port_var.get() if hasattr(self, 'auto_port_var') else True
        }
        try:
            config_path = os.path.join(self.project_path, self.config_file) if self.project_path else self.config_file
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass

    def load_config(self):
        """Load configuration"""
        config_path = self.config_file
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.project_path = config.get('project_path', '')
                    self._saved_config = config
            except:
                self._saved_config = {}
        else:
            self._saved_config = {}

    def restore_config_values(self):
        """Restore saved config values after widgets are created"""
        if hasattr(self, '_saved_config'):
            config = self._saved_config
            if hasattr(self, 'flask_app_var'):
                self.flask_app_var.set(config.get('flask_app', ''))
            if hasattr(self, 'port_var'):
                self.port_var.set(config.get('port', '5000'))
            if hasattr(self, 'host_var'):
                self.host_var.set(config.get('host', '127.0.0.1'))
            if hasattr(self, 'python_var'):
                self.python_var.set(config.get('python_path', sys.executable))
            if hasattr(self, 'debug_var'):
                self.debug_var.set(config.get('debug', True))
            if hasattr(self, 'reload_var'):
                self.reload_var.set(config.get('reload', True))
            if hasattr(self, 'auto_port_var'):
                self.auto_port_var.set(config.get('auto_port', True))

    def on_closing(self):
        """Handle window close"""
        if self.server_running:
            if messagebox.askokcancel("Quit", "Server is running. Stop and quit?"):
                self.stop_server()
                self.save_config()
                self.root.destroy()
        else:
            self.save_config()
            self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()

    # Apply modern theme if available
    try:
        style = ttk.Style()
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'vista' in available_themes:
            style.theme_use('vista')
    except:
        pass

    app = UniversalFlaskStudio(root)

    # Restore config values after widgets are created
    app.restore_config_values()

    # Auto-analyze if project path is set
    if app.project_path:
        root.after(100, app.auto_detect_flask_app)
        root.after(200, app.detect_python)

    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()