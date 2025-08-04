#!/usr/bin/env python3
"""
Flask Development Server Manager
A GUI application to easily start and manage Flask development servers
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import subprocess
import threading
import socket
import webbrowser
from pathlib import Path
import json
import time


class FlaskServerManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Flask Studio")
        self.root.geometry("900x750")
        self.root.resizable(True, True)

        # Server state
        self.server_process = None
        self.server_running = False
        self.project_path = ""
        self.server_port = 5000
        self.config_file = "flask_manager_config.json"

        # Load saved configuration
        self.load_config()

        # Create GUI
        self.create_widgets()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Flask Studio",
                                font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Project Directory Section
        ttk.Label(main_frame, text="Project Directory:",
                  font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        # Directory selection frame
        dir_frame = ttk.Frame(main_frame)
        dir_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_frame.columnconfigure(0, weight=1)

        self.dir_var = tk.StringVar(value=self.project_path)
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, state="readonly")
        self.dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        self.browse_btn = ttk.Button(dir_frame, text="Browse", command=self.browse_directory)
        self.browse_btn.grid(row=0, column=1)

        # Virtual Environment Detection
        self.venv_var = tk.StringVar()
        self.venv_label = ttk.Label(main_frame, textvariable=self.venv_var,
                                    foreground="blue")
        self.venv_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        # Flask file detection
        self.flask_file_var = tk.StringVar()
        self.flask_file_label = ttk.Label(main_frame, textvariable=self.flask_file_var,
                                          foreground="green")
        self.flask_file_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Server Configuration Section
        config_frame = ttk.LabelFrame(main_frame, text="Server Configuration", padding="10")
        config_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)

        # Port selection
        ttk.Label(config_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.port_var = tk.StringVar(value=str(self.server_port))
        port_spinbox = ttk.Spinbox(config_frame, from_=5000, to=9999, textvariable=self.port_var, width=10)
        port_spinbox.grid(row=0, column=1, sticky=tk.W)

        # Auto-find port checkbox
        self.auto_port_var = tk.BooleanVar(value=True)
        auto_port_cb = ttk.Checkbutton(config_frame, text="Auto-find available port",
                                       variable=self.auto_port_var)
        auto_port_cb.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))

        # Python Interpreter Selection
        ttk.Label(config_frame, text="Python:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))

        self.python_var = tk.StringVar(value=sys.executable)
        python_frame = ttk.Frame(config_frame)
        python_frame.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        python_frame.columnconfigure(0, weight=1)

        python_entry = ttk.Entry(python_frame, textvariable=self.python_var, state="readonly")
        python_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        detect_venv_btn = ttk.Button(python_frame, text="Detect Venv", command=self.detect_virtual_env)
        detect_venv_btn.grid(row=0, column=1)

        # Debug mode checkbox
        self.debug_var = tk.BooleanVar(value=True)
        debug_cb = ttk.Checkbutton(config_frame, text="Debug mode (auto-reload)",
                                   variable=self.debug_var)
        debug_cb.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))

        # Server Control Section
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=6, column=0, columnspan=3, pady=(10, 0))

        self.start_btn = ttk.Button(control_frame, text="Start Server",
                                    command=self.start_server, style="Accent.TButton")
        self.start_btn.grid(row=0, column=0, padx=(0, 10))

        self.stop_btn = ttk.Button(control_frame, text="Stop Server",
                                   command=self.stop_server, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))

        self.open_browser_btn = ttk.Button(control_frame, text="Open in Browser",
                                           command=self.open_browser, state="disabled")
        self.open_browser_btn.grid(row=0, column=2, padx=(0, 10))

        # Server Status
        self.status_var = tk.StringVar(value="Server: Stopped")
        status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                 font=("Arial", 10, "bold"))
        status_label.grid(row=7, column=0, columnspan=3, pady=(10, 0))

        # URL Display
        self.url_var = tk.StringVar()
        url_label = ttk.Label(main_frame, textvariable=self.url_var,
                              foreground="blue", cursor="hand2")
        url_label.grid(row=8, column=0, columnspan=3, pady=(5, 0))
        url_label.bind("<Button-1>", lambda e: self.open_browser())

        # Console Output
        ttk.Label(main_frame, text="Server Output:",
                  font=("Arial", 10, "bold")).grid(row=9, column=0, sticky=tk.W, pady=(20, 5))

        # Console frame with scrollbar
        console_frame = ttk.Frame(main_frame)
        console_frame.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(10, weight=1)

        self.console_text = scrolledtext.ScrolledText(console_frame, height=15, width=80,
                                                      bg="black", fg="white", font=("Consolas", 9))
        self.console_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Clear console button
        clear_btn = ttk.Button(main_frame, text="Clear Console", command=self.clear_console)
        clear_btn.grid(row=11, column=0, sticky=tk.W)

        # Update flask file detection if directory already set
        if self.project_path:
            self.detect_flask_files()
            self.detect_virtual_env()

    def detect_virtual_env(self):
        """Detect and suggest virtual environment for the project"""
        if not self.project_path:
            self.venv_var.set("")
            return

        venv_paths = [
            os.path.join(self.project_path, 'venv'),
            os.path.join(self.project_path, '.venv'),
            os.path.join(self.project_path, 'env'),
            os.path.join(self.project_path, '.env')
        ]

        for venv_path in venv_paths:
            # Check for Scripts (Windows) or bin (Unix) directory
            scripts_dir = os.path.join(venv_path, 'Scripts')  # Windows
            bin_dir = os.path.join(venv_path, 'bin')  # Unix/Linux/Mac

            if os.path.exists(scripts_dir):
                python_exe = os.path.join(scripts_dir, 'python.exe')
                if os.path.exists(python_exe):
                    self.python_var.set(python_exe)
                    self.venv_var.set(f"🐍 Virtual environment detected: {os.path.basename(venv_path)}")
                    return
            elif os.path.exists(bin_dir):
                python_exe = os.path.join(bin_dir, 'python')
                if os.path.exists(python_exe):
                    self.python_var.set(python_exe)
                    self.venv_var.set(f"🐍 Virtual environment detected: {os.path.basename(venv_path)}")
                    return

        # Check if current Python has Flask installed
        try:
            import flask
            self.venv_var.set("✓ Flask available in current Python environment")
        except ImportError:
            self.venv_var.set("⚠ No virtual environment found. Flask may not be installed.")

    def check_flask_installation(self, python_path):
        """Check if Flask is installed in the specified Python environment"""
        try:
            result = subprocess.run([
                python_path, '-c', 'import flask; print(f"Flask {flask.__version__} installed")'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, "Flask not installed"
        except Exception as e:
            return False, str(e)

    def install_flask(self, python_path):
        """Install Flask in the specified Python environment"""
        self.log_message("Installing Flask...")
        try:
            # Install Flask using pip
            result = subprocess.run([
                python_path, '-m', 'pip', 'install', 'flask'
            ], capture_output=True, text=True, cwd=self.project_path)

            if result.returncode == 0:
                self.log_message("✓ Flask installed successfully!")
                self.log_message(result.stdout)
                return True
            else:
                self.log_message(f"✗ Flask installation failed: {result.stderr}")
                messagebox.showerror("Installation Failed", f"Failed to install Flask:\n{result.stderr}")
                return False
        except Exception as e:
            error_msg = f"Error installing Flask: {str(e)}"
            self.log_message(f"✗ {error_msg}")
            messagebox.showerror("Installation Error", error_msg)
            return False

    def browse_directory(self):
        """Open file dialog to select Flask project directory"""
        directory = filedialog.askdirectory(
            title="Select Flask Project Directory",
            initialdir=self.project_path if self.project_path else os.getcwd()
        )

        if directory:
            self.project_path = directory
            self.dir_var.set(directory)
            self.detect_flask_files()
            self.detect_virtual_env()
            self.save_config()

    def detect_flask_files(self):
        """Detect potential Flask application files in the selected directory"""
        if not self.project_path:
            self.flask_file_var.set("")
            return

        flask_files = []
        main_flask_files = []  # Files that can actually run the app

        # Check all Python files for Flask imports
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'Flask(' in content or 'from flask import' in content or 'import flask' in content:
                                rel_path = os.path.relpath(file_path, self.project_path)
                                flask_files.append(rel_path)

                                # Check if this file can run the app (has app.run() or __main__)
                                if 'app.run(' in content or 'if __name__' in content:
                                    main_flask_files.append(rel_path)

                    except (UnicodeDecodeError, PermissionError):
                        continue

        if flask_files:
            if main_flask_files:
                self.flask_file_var.set(f"✓ Flask app files found: {', '.join(main_flask_files[:2])} (runnable)")
            else:
                self.flask_file_var.set(f"✓ Flask files detected: {', '.join(flask_files[:3])} (may need flask run)")
        else:
            self.flask_file_var.set("⚠ No Flask files detected in this directory")

    def find_available_port(self, start_port=5000):
        """Find an available port starting from the given port"""
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        return start_port  # Fallback to original port

    def start_server(self):
        """Start the Flask development server"""
        if not self.project_path:
            messagebox.showerror("Error", "Please select a Flask project directory first!")
            return

        # Check Flask installation before starting
        python_path = self.python_var.get()
        flask_available, flask_info = self.check_flask_installation(python_path)

        if not flask_available:
            response = messagebox.askyesno(
                "Flask Not Found",
                f"Flask is not installed in the selected Python environment.\n\n"
                f"Python: {python_path}\n\n"
                f"Would you like to install Flask automatically?\n"
                f"(This will run: pip install flask)"
            )
            if response:
                if not self.install_flask(python_path):
                    return
            else:
                return
        else:
            self.log_message(f"✓ {flask_info}")

        if self.server_running:
            messagebox.showwarning("Warning", "Server is already running!")
            return

        # Find main Flask file - first check common names, then scan all Python files
        main_files = ['app.py', 'run.py', 'main.py', 'server.py', 'roscodetech.py']
        flask_file = None

        # First, try common file names in root directory
        for file in main_files:
            potential_path = os.path.join(self.project_path, file)
            if os.path.exists(potential_path):
                flask_file = file
                break

        # Look in mysite subdirectory (based on your structure)
        if not flask_file:
            mysite_path = os.path.join(self.project_path, 'mysite')
            if os.path.exists(mysite_path):
                for file in main_files:
                    potential_path = os.path.join(mysite_path, file)
                    if os.path.exists(potential_path):
                        flask_file = os.path.join('mysite', file)
                        break

        # If still not found, scan all Python files for Flask imports
        if not flask_file:
            self.log_message("Scanning for Flask files...")
            for root, dirs, files in os.walk(self.project_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Look for Flask app creation patterns
                                if (
                                        'Flask(' in content or 'from flask import' in content or 'import flask' in content) and \
                                        ('app.run(' in content or 'if __name__' in content):
                                    flask_file = os.path.relpath(file_path, self.project_path)
                                    self.log_message(f"Found Flask app file: {flask_file}")
                                    break
                        except (UnicodeDecodeError, PermissionError):
                            continue
                if flask_file:
                    break

        if not flask_file:
            messagebox.showerror("Error",
                                 "No Flask application file found!\n\nMake sure your Flask file contains:\n- Flask import\n- app.run() or if __name__ == '__main__'")
            return

        # Determine port
        if self.auto_port_var.get():
            try:
                desired_port = int(self.port_var.get())
            except ValueError:
                desired_port = 5000
            self.server_port = self.find_available_port(desired_port)
            self.port_var.set(str(self.server_port))
        else:
            try:
                self.server_port = int(self.port_var.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid port number!")
                return

        # Setup environment variables
        env = os.environ.copy()
        env['FLASK_APP'] = flask_file
        env['FLASK_ENV'] = 'development' if self.debug_var.get() else 'production'
        env['FLASK_DEBUG'] = '1' if self.debug_var.get() else '0'

        # Start server in a separate thread
        self.server_thread = threading.Thread(target=self._run_server, args=(flask_file, env), daemon=True)
        self.server_thread.start()

        # Update UI
        self.server_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.open_browser_btn.config(state="normal")

        url = f"http://localhost:{self.server_port}"
        self.url_var.set(f"Server URL: {url}")
        self.status_var.set("Server: Starting...")

        self.log_message(f"Starting Flask server on port {self.server_port}...")
        self.log_message(f"Flask file: {flask_file}")
        self.log_message(f"Debug mode: {'ON' if self.debug_var.get() else 'OFF'}")
        self.log_message(f"Project directory: {self.project_path}")
        self.log_message("-" * 60)

    def _run_server(self, flask_file, env):
        """Run the Flask server in a separate process"""
        try:
            # Change to project directory
            os.chdir(self.project_path)

            # Prepare command
            python_path = self.python_var.get()
            cmd = [
                python_path,
                flask_file
            ]

            # For files that don't accept command line args, use flask run
            flask_run_cmd = [
                python_path, '-m', 'flask', 'run',
                '--host=127.0.0.1',
                f'--port={self.server_port}',
                '--reload' if self.debug_var.get() else '--no-reload'
            ]

            # Try direct execution first, then flask run
            try:
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    env=env,
                    cwd=self.project_path
                )
            except FileNotFoundError:
                # Fallback to flask run command
                self.server_process = subprocess.Popen(
                    flask_run_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    env=env,
                    cwd=self.project_path
                )

            # Update status
            self.root.after(1000, lambda: self.status_var.set("Server: Running"))

            # Read output and display in console
            for line in iter(self.server_process.stdout.readline, ''):
                if line.strip():
                    self.root.after(0, lambda l=line.strip(): self.log_message(l))

                # Check if process ended
                if self.server_process.poll() is not None:
                    break

            # Server stopped
            self.root.after(0, self._server_stopped)

        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"Error starting server: {str(e)}"))
            self.root.after(0, self._server_stopped)

    def stop_server(self):
        """Stop the Flask development server"""
        if self.server_process:
            self.log_message("Stopping Flask server...")
            try:
                self.server_process.terminate()
                # Give it a moment to terminate gracefully
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.log_message("Force killing server process...")
                self.server_process.kill()
            except Exception as e:
                self.log_message(f"Error stopping server: {str(e)}")

            self.server_process = None

        self._server_stopped()

    def _server_stopped(self):
        """Update UI when server stops"""
        self.server_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.open_browser_btn.config(state="disabled")
        self.status_var.set("Server: Stopped")
        self.url_var.set("")
        self.log_message("Server stopped.")
        self.log_message("=" * 60)

    def open_browser(self):
        """Open the Flask application in the default web browser"""
        if self.server_running:
            url = f"http://localhost:{self.server_port}"
            webbrowser.open(url)
            self.log_message(f"Opening browser: {url}")

    def log_message(self, message):
        """Add a message to the console output"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        # Insert at end and scroll to bottom
        self.console_text.insert(tk.END, formatted_message)
        self.console_text.see(tk.END)

        # Limit console lines to prevent memory issues
        lines = int(self.console_text.index('end-1c').split('.')[0])
        if lines > 1000:
            self.console_text.delete('1.0', '100.0')

    def clear_console(self):
        """Clear the console output"""
        self.console_text.delete('1.0', tk.END)
        # Log message after clearing, not during clearing to avoid recursion
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] Console cleared.\n"
        self.console_text.insert(tk.END, formatted_message)
        self.console_text.see(tk.END)

    def save_config(self):
        """Save configuration to file"""
        config = {
            'project_path': self.project_path,
            'server_port': self.server_port
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.project_path = config.get('project_path', '')
                    self.server_port = config.get('server_port', 5000)
            except Exception as e:
                print(f"Error loading config: {e}")

    def on_closing(self):
        """Handle application closing"""
        if self.server_running:
            if messagebox.askokcancel("Quit", "Flask server is running. Stop server and quit?"):
                self.stop_server()
                self.save_config()
                self.root.destroy()
        else:
            self.save_config()
            self.root.destroy()


def main():
    """Main application entry point"""
    # Check Python version
    if sys.version_info < (3, 6):
        print("This application requires Python 3.6 or higher!")
        sys.exit(1)

    # Create and run the application
    root = tk.Tk()

    # Set icon (if available)
    try:
        # For Windows
        root.iconbitmap('flask_icon.ico')
    except:
        pass

    # Apply a modern theme if available
    try:
        style = ttk.Style()
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'vista' in available_themes:
            style.theme_use('vista')
    except:
        pass

    app = FlaskServerManager(root)

    # Center the window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # Start the GUI event loop
    root.mainloop()


if __name__ == "__main__":
    main()