#!/usr/bin/env python3
"""
Enhanced Flask Development Server Manager
A GUI application to easily start and manage Flask development servers
with automatic routing pattern detection and project structure analysis
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
import re
import ast


class FlaskProjectAnalyzer:
    """Analyzes Flask project structure and routing patterns"""

    def __init__(self, project_path):
        self.project_path = project_path
        self.flask_files = []
        self.routing_pattern = None
        self.main_app_file = None
        self.blueprints = []
        self.app_factory = None

    def analyze(self):
        """Perform comprehensive project analysis"""
        self.find_flask_files()
        self.detect_routing_pattern()
        self.find_main_app_file()
        self.detect_blueprints()
        self.detect_app_factory()

        return {
            'flask_files': self.flask_files,
            'routing_pattern': self.routing_pattern,
            'main_app_file': self.main_app_file,
            'blueprints': self.blueprints,
            'app_factory': self.app_factory,
            'recommended_run_method': self.get_recommended_run_method()
        }

    def find_flask_files(self):
        """Find all Python files that import or use Flask"""
        flask_files = []

        for root, dirs, files in os.walk(self.project_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    if self.is_flask_file(file_path):
                        rel_path = os.path.relpath(file_path, self.project_path)
                        flask_files.append({
                            'path': rel_path,
                            'full_path': file_path,
                            'has_app_run': self.has_app_run(file_path),
                            'has_routes': self.has_routes(file_path),
                            'has_blueprints': self.has_blueprints(file_path),
                            'is_factory': self.is_app_factory(file_path)
                        })

        self.flask_files = flask_files
        return flask_files

    def is_flask_file(self, file_path):
        """Check if file imports or uses Flask"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return any([
                    'from flask import' in content,
                    'import flask' in content,
                    'Flask(' in content,
                    '@app.route' in content,
                    'Blueprint(' in content
                ])
        except (UnicodeDecodeError, PermissionError):
            return False

    def has_app_run(self, file_path):
        """Check if file has app.run() call"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'app.run(' in content or '__name__' in content
        except:
            return False

    def has_routes(self, file_path):
        """Check if file defines routes"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return '@app.route' in content or '@main.route' in content or '.route(' in content
        except:
            return False

    def has_blueprints(self, file_path):
        """Check if file uses blueprints"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'Blueprint(' in content or 'register_blueprint' in content
        except:
            return False

    def is_app_factory(self, file_path):
        """Check if file contains app factory pattern"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'def create_app' in content and 'return app' in content
        except:
            return False

    def detect_routing_pattern(self):
        """Detect the routing pattern used in the project"""
        has_direct_routes = any(f['has_routes'] and not f['has_blueprints'] for f in self.flask_files)
        has_blueprint_routes = any(f['has_blueprints'] for f in self.flask_files)
        has_factory = any(f['is_factory'] for f in self.flask_files)

        if has_factory:
            self.routing_pattern = 'factory'
        elif has_blueprint_routes:
            self.routing_pattern = 'blueprint'
        elif has_direct_routes:
            self.routing_pattern = 'direct'
        else:
            self.routing_pattern = 'unknown'

        return self.routing_pattern

    def find_main_app_file(self):
        """Find the main application file"""
        # Priority order for main app files
        priority_names = ['app.py', 'run.py', 'main.py', 'server.py', '__init__.py']

        # Look for files with app.run() first
        runnable_files = [f for f in self.flask_files if f['has_app_run']]

        # Check priority names in runnable files
        for name in priority_names:
            for f in runnable_files:
                if os.path.basename(f['path']) == name:
                    self.main_app_file = f['path']
                    return self.main_app_file

        # If no priority match, take first runnable file
        if runnable_files:
            self.main_app_file = runnable_files[0]['path']
            return self.main_app_file

        # Look for app factory files
        factory_files = [f for f in self.flask_files if f['is_factory']]
        if factory_files:
            self.main_app_file = factory_files[0]['path']
            return self.main_app_file

        # Fallback to any Flask file
        if self.flask_files:
            self.main_app_file = self.flask_files[0]['path']

        return self.main_app_file

    def detect_blueprints(self):
        """Detect blueprint registrations"""
        blueprints = []

        for f in self.flask_files:
            if f['has_blueprints']:
                try:
                    with open(f['full_path'], 'r', encoding='utf-8') as file:
                        content = file.read()

                        # Find Blueprint definitions
                        blueprint_matches = re.findall(r'(\w+)\s*=\s*Blueprint\([\'"](\w+)[\'"]', content)
                        for var_name, bp_name in blueprint_matches:
                            blueprints.append({
                                'name': bp_name,
                                'variable': var_name,
                                'file': f['path']
                            })

                        # Find blueprint registrations
                        register_matches = re.findall(r'register_blueprint\((\w+)', content)
                        for bp_var in register_matches:
                            if not any(bp['variable'] == bp_var for bp in blueprints):
                                blueprints.append({
                                    'name': bp_var,
                                    'variable': bp_var,
                                    'file': f['path']
                                })

                except:
                    continue

        self.blueprints = blueprints
        return blueprints

    def detect_app_factory(self):
        """Detect app factory function"""
        for f in self.flask_files:
            if f['is_factory']:
                try:
                    with open(f['full_path'], 'r', encoding='utf-8') as file:
                        content = file.read()

                        # Look for create_app function
                        match = re.search(r'def\s+(create_app)\s*\([^)]*\)', content)
                        if match:
                            self.app_factory = {
                                'function': match.group(1),
                                'file': f['path']
                            }
                            break
                except:
                    continue

        return self.app_factory

    def get_recommended_run_method(self):
        """Get recommended method to run the Flask app"""
        if self.routing_pattern == 'factory':
            return 'flask_run'
        elif self.main_app_file and any(f['has_app_run'] for f in self.flask_files if f['path'] == self.main_app_file):
            return 'direct'
        else:
            return 'flask_run'


class FlaskServerManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Flask Studio Pro")
        self.root.geometry("1000x800")
        self.root.resizable(True, True)

        # Server state
        self.server_process = None
        self.server_running = False
        self.project_path = ""
        self.server_port = 5000
        self.config_file = "flask_studio_config.json"

        # Project analysis
        self.project_analyzer = None
        self.project_info = {}

        # Load saved configuration
        self.load_config()

        # Create GUI
        self.create_widgets()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Main frame with notebook for tabs
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Flask Studio Pro",
                                font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create tabs
        self.create_main_tab()
        self.create_analysis_tab()
        self.create_console_tab()

    def create_main_tab(self):
        """Create the main server control tab"""
        main_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="Server Control")

        # Configure grid
        main_tab.columnconfigure(1, weight=1)
        main_tab.rowconfigure(6, weight=1)

        current_row = 0

        # Project Directory Section
        ttk.Label(main_tab, text="Project Directory:",
                  font=("Arial", 10, "bold")).grid(row=current_row, column=0, sticky=tk.W, pady=(0, 5))
        current_row += 1

        # Directory selection frame
        dir_frame = ttk.Frame(main_tab)
        dir_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_frame.columnconfigure(0, weight=1)

        self.dir_var = tk.StringVar(value=self.project_path)
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, state="readonly")
        self.dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        self.browse_btn = ttk.Button(dir_frame, text="Browse", command=self.browse_directory)
        self.browse_btn.grid(row=0, column=1)

        self.analyze_btn = ttk.Button(dir_frame, text="Analyze", command=self.analyze_project)
        self.analyze_btn.grid(row=0, column=2, padx=(5, 0))
        current_row += 1

        # Project info display
        self.project_info_var = tk.StringVar()
        self.project_info_label = ttk.Label(main_tab, textvariable=self.project_info_var,
                                            foreground="blue", wraplength=700)
        self.project_info_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        current_row += 1

        # Server Configuration Section
        config_frame = ttk.LabelFrame(main_tab, text="Server Configuration", padding="10")
        config_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
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

        # Run method selection
        ttk.Label(config_frame, text="Run Method:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.run_method_var = tk.StringVar(value="auto")
        run_method_combo = ttk.Combobox(config_frame, textvariable=self.run_method_var,
                                        values=["auto", "direct", "flask_run"], state="readonly", width=15)
        run_method_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))

        # Run method info
        self.run_method_info_var = tk.StringVar()
        run_method_info = ttk.Label(config_frame, textvariable=self.run_method_info_var,
                                    foreground="gray", font=("Arial", 8))
        run_method_info.grid(row=1, column=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))

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
        current_row += 1

        # Server Control Section
        control_frame = ttk.Frame(main_tab)
        control_frame.grid(row=current_row, column=0, columnspan=3, pady=(10, 0))

        self.start_btn = ttk.Button(control_frame, text="Start Server",
                                    command=self.start_server, style="Accent.TButton")
        self.start_btn.grid(row=0, column=0, padx=(0, 10))

        self.stop_btn = ttk.Button(control_frame, text="Stop Server",
                                   command=self.stop_server, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))

        self.open_browser_btn = ttk.Button(control_frame, text="Open in Browser",
                                           command=self.open_browser, state="disabled")
        self.open_browser_btn.grid(row=0, column=2, padx=(0, 10))
        current_row += 1

        # Server Status
        self.status_var = tk.StringVar(value="Server: Stopped")
        status_label = ttk.Label(main_tab, textvariable=self.status_var,
                                 font=("Arial", 10, "bold"))
        status_label.grid(row=current_row, column=0, columnspan=3, pady=(10, 0))
        current_row += 1

        # URL Display
        self.url_var = tk.StringVar()
        url_label = ttk.Label(main_tab, textvariable=self.url_var,
                              foreground="blue", cursor="hand2")
        url_label.grid(row=current_row, column=0, columnspan=3, pady=(5, 0))
        url_label.bind("<Button-1>", lambda e: self.open_browser())

        # Update project analysis if directory already set (but only after all tabs are created)
        if self.project_path:
            self.root.after(100, self.delayed_analyze_project)

    def create_analysis_tab(self):
        """Create the project analysis tab"""
        analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(analysis_tab, text="Project Analysis")

        analysis_tab.columnconfigure(0, weight=1)
        analysis_tab.rowconfigure(0, weight=1)

        # Create treeview for project analysis
        self.analysis_tree = ttk.Treeview(analysis_tab, columns=("Type", "Details"), show="tree headings")
        self.analysis_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

        # Configure columns
        self.analysis_tree.heading("#0", text="Item")
        self.analysis_tree.heading("Type", text="Type")
        self.analysis_tree.heading("Details", text="Details")

        self.analysis_tree.column("#0", width=300)
        self.analysis_tree.column("Type", width=150)
        self.analysis_tree.column("Details", width=400)

        # Add scrollbar
        analysis_scrollbar = ttk.Scrollbar(analysis_tab, orient="vertical", command=self.analysis_tree.yview)
        analysis_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S), pady=10)
        self.analysis_tree.configure(yscrollcommand=analysis_scrollbar.set)

    def create_console_tab(self):
        """Create the console output tab"""
        console_tab = ttk.Frame(self.notebook)
        self.notebook.add(console_tab, text="Console Output")

        console_tab.columnconfigure(0, weight=1)
        console_tab.rowconfigure(0, weight=1)

        # Console output
        self.console_text = scrolledtext.ScrolledText(console_tab, height=25, width=100,
                                                      bg="black", fg="white", font=("Consolas", 9))
        self.console_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

        # Clear console button
        clear_btn = ttk.Button(console_tab, text="Clear Console", command=self.clear_console)
        clear_btn.grid(row=1, column=0, sticky=tk.W, padx=10, pady=(0, 10))

    def browse_directory(self):
        """Open file dialog to select Flask project directory"""
        directory = filedialog.askdirectory(
            title="Select Flask Project Directory",
            initialdir=self.project_path if self.project_path else os.getcwd()
        )

        if directory:
            self.project_path = directory
            self.dir_var.set(directory)
            self.analyze_project()
            self.detect_virtual_env()
            self.save_config()

    def analyze_project(self):
        """Analyze the Flask project structure"""
        if not self.project_path:
            return

        self.log_message("Analyzing Flask project structure...")

        try:
            self.project_analyzer = FlaskProjectAnalyzer(self.project_path)
            self.project_info = self.project_analyzer.analyze()

            # Update UI with analysis results
            self.update_project_info_display()
            self.update_analysis_tree()
            self.update_run_method_recommendation()

            self.log_message(f"✓ Project analysis complete. Found {len(self.project_info['flask_files'])} Flask files")

        except Exception as e:
            self.log_message(f"✗ Error analyzing project: {str(e)}")
            messagebox.showerror("Analysis Error", f"Failed to analyze project:\n{str(e)}")

    def update_run_method_recommendation(self):
        """Update the run method recommendation"""
        if not self.project_info:
            return

        recommended = self.project_info.get('recommended_run_method', 'flask_run')

        if self.run_method_var.get() == "auto":
            info_text = f"Recommended: {recommended}"
        else:
            info_text = f"Manual override (recommended: {recommended})"

        self.run_method_info_var.set(info_text)

    def update_project_info_display(self):
        """Update the project info display"""
        if not self.project_info:
            return

        info_parts = []

        # Main app file
        if self.project_info.get('main_app_file'):
            info_parts.append(f"📁 Main App: {self.project_info['main_app_file']}")

        # Routing pattern
        pattern = self.project_info.get('routing_pattern', 'unknown')
        pattern_icons = {
            'direct': '🔗',
            'blueprint': '🧩',
            'factory': '🏭',
            'unknown': '❓'
        }
        info_parts.append(f"{pattern_icons.get(pattern, '❓')} Pattern: {pattern.title()}")

        # Blueprints
        if self.project_info.get('blueprints'):
            bp_names = [bp['name'] for bp in self.project_info['blueprints']]
            info_parts.append(f"🧩 Blueprints: {', '.join(bp_names)}")

        self.project_info_var.set(" | ".join(info_parts))

    def update_analysis_tree(self):
        """Update the analysis tree view"""
        # Clear existing items
        for item in self.analysis_tree.get_children():
            self.analysis_tree.delete(item)

        if not self.project_info:
            return

        # Add project overview
        project_item = self.analysis_tree.insert("", "end", text="Project Overview",
                                                 values=("Summary",
                                                         f"Pattern: {self.project_info.get('routing_pattern', 'unknown')}"))

        # Add main app file
        if self.project_info.get('main_app_file'):
            self.analysis_tree.insert(project_item, "end", text=self.project_info['main_app_file'],
                                      values=("Main App", "Entry point"))

        # Add Flask files
        if self.project_info.get('flask_files'):
            files_item = self.analysis_tree.insert("", "end", text="Flask Files",
                                                   values=(
                                                   "Category", f"{len(self.project_info['flask_files'])} files"))

            for f in self.project_info['flask_files']:
                details = []
                if f['has_app_run']:
                    details.append("runnable")
                if f['has_routes']:
                    details.append("has routes")
                if f['has_blueprints']:
                    details.append("uses blueprints")
                if f['is_factory']:
                    details.append("app factory")

                self.analysis_tree.insert(files_item, "end", text=f['path'],
                                          values=("Flask File", ", ".join(details) if details else "basic"))

        # Add blueprints
        if self.project_info.get('blueprints'):
            bp_item = self.analysis_tree.insert("", "end", text="Blueprints",
                                                values=(
                                                "Category", f"{len(self.project_info['blueprints'])} blueprints"))

            for bp in self.project_info['blueprints']:
                self.analysis_tree.insert(bp_item, "end", text=bp['name'],
                                          values=("Blueprint", f"in {bp['file']}"))

        # Expand all items
        for item in self.analysis_tree.get_children():
            self.analysis_tree.item(item, open=True)

    def detect_flask_app_variable(self, file_path):
        """Detect the Flask app variable name in a file"""
        try:
            full_path = os.path.join(self.project_path, file_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Look for Flask app creation patterns
                patterns = [
                    r'(\w+)\s*=\s*Flask\(',  # app = Flask(...)
                    r'(\w+)\s*=\s*create_app\(',  # app = create_app(...)
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        return matches[0]  # Return first match

                return None
        except Exception as e:
            self.log_message(f"Error detecting Flask app variable: {str(e)}")
            return None

    def create_wsgi_file(self):
        """Create a wsgi.py file for flask run compatibility"""
        wsgi_content = """#!/usr/bin/env python3
'''
WSGI Entry Point
Auto-generated by Flask Studio Pro
'''

import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Try different import patterns
app = None

try:
    # Try app factory pattern
    from tmgpapp import create_app
    app = create_app()
    print("✓ Loaded app using factory pattern")
except ImportError:
    try:
        # Try direct app import
        from tmgpapp.tmgp_app import app
        print("✓ Loaded app from tmgp_app.py")
    except ImportError:
        try:
            # Try main app file
            from app import app
            print("✓ Loaded app from app.py") 
        except ImportError:
            print("❌ Could not find Flask app")
            raise ImportError("No Flask application found")

if __name__ == "__main__":
    if app:
        app.run(debug=True, host='127.0.0.1', port=5000)
"""

        wsgi_path = os.path.join(self.project_path, 'wsgi.py')
        with open(wsgi_path, 'w', encoding='utf-8') as f:
            f.write(wsgi_content)

        self.log_message(f"✓ Created wsgi.py: {wsgi_path}")
        return wsgi_path
        """Update the run method recommendation"""
        if not self.project_info:
            return

        recommended = self.project_info.get('recommended_run_method', 'flask_run')

        if self.run_method_var.get() == "auto":
            info_text = f"Recommended: {recommended}"
        else:
            info_text = f"Manual override (recommended: {recommended})"

        self.run_method_info_var.set(info_text)

    def detect_virtual_env(self):
        """Detect and suggest virtual environment for the project"""
        if not self.project_path:
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
                    self.log_message(f"🐍 Virtual environment detected: {os.path.basename(venv_path)}")
                    return
            elif os.path.exists(bin_dir):
                python_exe = os.path.join(bin_dir, 'python')
                if os.path.exists(python_exe):
                    self.python_var.set(python_exe)
                    self.log_message(f"🐍 Virtual environment detected: {os.path.basename(venv_path)}")
                    return

        # Check if Flask is available in current Python
        self.check_flask_installation(self.python_var.get())

    def check_flask_installation(self, python_path):
        """Check if Flask is installed in the specified Python environment"""
        try:
            result = subprocess.run([
                python_path, '-c', 'import flask; print(f"Flask {flask.__version__} installed")'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_message(f"✓ {result.stdout.strip()}")
                return True
            else:
                self.log_message("⚠ Flask not found in current Python environment")
                return False
        except Exception as e:
            self.log_message(f"⚠ Error checking Flask installation: {str(e)}")
            return False

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
        """Start the Flask development server with intelligent routing detection"""
        if not self.project_path:
            messagebox.showerror("Error", "Please select a Flask project directory first!")
            return

        if self.server_running:
            messagebox.showwarning("Warning", "Server is already running!")
            return

        # Ensure project is analyzed
        if not self.project_info:
            self.analyze_project()

        # Check Flask installation
        python_path = self.python_var.get()
        if not self.check_flask_installation(python_path):
            response = messagebox.askyesno(
                "Flask Not Found",
                f"Flask is not installed in the selected Python environment.\n\n"
                f"Would you like to install Flask automatically?"
            )
            if response:
                if not self.install_flask(python_path):
                    return
            else:
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

        # Determine run method
        run_method = self.run_method_var.get()
        if run_method == "auto":
            run_method = self.project_info.get('recommended_run_method', 'flask_run')

        # Setup environment variables
        env = os.environ.copy()
        env['FLASK_ENV'] = 'development' if self.debug_var.get() else 'production'
        env['FLASK_DEBUG'] = '1' if self.debug_var.get() else '0'

        # Determine main app file
        main_app_file = self.project_info.get('main_app_file')
        if not main_app_file:
            messagebox.showerror("Error", "No Flask application file found! Please analyze the project first.")
            return

        # Set FLASK_APP for flask run method
        if run_method == 'flask_run':
            # For app factory pattern, use module:function format
            if self.project_info.get('app_factory'):
                factory_file = self.project_info['app_factory']['file']
                factory_func = self.project_info['app_factory']['function']
                module_name = os.path.splitext(factory_file.replace('/', '.').replace('\\', '.'))[0]
                env['FLASK_APP'] = f"{module_name}:{factory_func}"
                self.log_message(f"Setting FLASK_APP to: {env['FLASK_APP']}")
            else:
                # For non-factory apps, we need to check if the file has a Flask app instance
                flask_app_var = self.detect_flask_app_variable(main_app_file)
                if flask_app_var:
                    module_name = os.path.splitext(main_app_file.replace('/', '.').replace('\\', '.'))[0]
                    env['FLASK_APP'] = f"{module_name}:{flask_app_var}"
                    self.log_message(f"Setting FLASK_APP to: {env['FLASK_APP']}")
                else:
                    # Fallback to direct execution if no app variable found
                    self.log_message("No Flask app variable found, switching to direct execution")
                    run_method = 'direct'

        # Start server in a separate thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            args=(main_app_file, env, run_method),
            daemon=True
        )
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
        self.log_message(f"Flask file: {main_app_file}")
        self.log_message(f"Run method: {run_method}")
        self.log_message(f"Debug mode: {'ON' if self.debug_var.get() else 'OFF'}")
        self.log_message(f"Project directory: {self.project_path}")
        self.log_message("-" * 60)

    def _run_server(self, flask_file, env, run_method):
        """Run the Flask server in a separate process"""
        try:
            # Change to project directory
            os.chdir(self.project_path)
            python_path = self.python_var.get()

            if run_method == 'flask_run':
                # Create wsgi.py if it doesn't exist for better flask run compatibility
                wsgi_path = os.path.join(self.project_path, 'wsgi.py')
                if not os.path.exists(wsgi_path):
                    self.create_wsgi_file()
                    env['FLASK_APP'] = 'wsgi:app'
                    self.log_message("Using wsgi.py entry point for flask run")

                # Use flask run command
                cmd = [
                    python_path, '-m', 'flask', 'run',
                    '--host=127.0.0.1',
                    f'--port={self.server_port}',
                    '--reload' if self.debug_var.get() else '--no-reload'
                ]
            else:
                # Direct execution
                cmd = [python_path, flask_file]

            self.log_message(f"Executing: {' '.join(cmd)}")

            self.server_process = subprocess.Popen(
                cmd,
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

    def install_flask(self, python_path):
        """Install Flask in the specified Python environment"""
        self.log_message("Installing Flask...")
        try:
            result = subprocess.run([
                python_path, '-m', 'pip', 'install', 'flask'
            ], capture_output=True, text=True, cwd=self.project_path)

            if result.returncode == 0:
                self.log_message("✓ Flask installed successfully!")
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

    def stop_server(self):
        """Stop the Flask development server"""
        if self.server_process:
            self.log_message("Stopping Flask server...")
            try:
                self.server_process.terminate()
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

    def delayed_analyze_project(self):
        """Analyze project after UI is fully initialized"""
        self.analyze_project()
        self.detect_virtual_env()

    def log_message(self, message):
        """Add a message to the console output"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        # Check if console_text exists (UI fully initialized)
        if hasattr(self, 'console_text'):
            # Insert at end and scroll to bottom
            self.console_text.insert(tk.END, formatted_message)
            self.console_text.see(tk.END)

            # Limit console lines to prevent memory issues
            lines = int(self.console_text.index('end-1c').split('.')[0])
            if lines > 1000:
                self.console_text.delete('1.0', '100.0')
        else:
            # Fallback to print if console not ready
            print(formatted_message.strip())

    def clear_console(self):
        """Clear the console output"""
        self.console_text.delete('1.0', tk.END)
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] Console cleared.\n"
        self.console_text.insert(tk.END, formatted_message)
        self.console_text.see(tk.END)

    def save_config(self):
        """Save configuration to file"""
        config = {
            'project_path': self.project_path,
            'server_port': self.server_port,
            'run_method': self.run_method_var.get(),
            'debug_mode': self.debug_var.get()
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
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