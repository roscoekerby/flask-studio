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
                            'is_factory': self.is_app_factory(file_path),
                            'has_app_creation': self.has_app_creation(file_path),
                            'app_variable': self.detect_app_variable(file_path)
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
                    'Blueprint(' in content,
                    'create_app(' in content
                ])
        except (UnicodeDecodeError, PermissionError):
            return False

    def has_app_run(self, file_path):
        """Check if file has app.run() call"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'app.run(' in content or ('__name__' in content and '__main__' in content)
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

    def has_app_creation(self, file_path):
        """Check if file creates a Flask app instance"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return any([
                    re.search(r'\w+\s*=\s*Flask\s*\(', content),
                    re.search(r'\w+\s*=\s*create_app\s*\(', content),
                    re.search(r'\w+\s*=\s*[\w\.]+\.create_app\s*\(', content)
                ])
        except:
            return False

    def detect_app_variable(self, file_path):
        """Detect the Flask app variable name in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Look for Flask app creation patterns
                patterns = [
                    r'(\w+)\s*=\s*Flask\s*\(',  # app = Flask(...)
                    r'(\w+)\s*=\s*create_app\s*\(',  # app = create_app(...)
                    r'(\w+)\s*=\s*[\w\.]+\.create_app\s*\(',  # app = module.create_app(...)
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        return matches[0]  # Return first match

                return None
        except Exception as e:
            return None

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
        """Find the main application file with intelligent detection"""
        # Get project name for dynamic file detection
        project_name = os.path.basename(self.project_path).lower()

        # IMPROVED: Dynamic priority list that adapts to project structure
        priority_patterns = [
            # 1. Files matching project name + app.py pattern (HIGHEST PRIORITY)
            f"{project_name}app.py",
            f"{project_name}.py",
            # 2. Standard entry point files
            'wsgi.py',
            'app.py',
            'run.py',
            'main.py',
            'server.py',
        ]

        # Look for files with app.run() first (RUNNABLE FILES GET PRIORITY)
        runnable_files = [f for f in self.flask_files if f['has_app_run']]

        # Check priority patterns in runnable files
        for pattern in priority_patterns:
            for f in runnable_files:
                filename = os.path.basename(f['path'])
                if filename == pattern or filename.lower() == pattern:
                    self.main_app_file = f['path']
                    return self.main_app_file

        # IMPROVED: Look for files that create app instances but prioritize those with proper entry points
        app_creation_files = [f for f in self.flask_files if f['has_app_creation']]

        # Prioritize files that are NOT __init__.py for direct execution
        non_init_files = [f for f in app_creation_files if not f['path'].endswith('__init__.py')]

        for pattern in priority_patterns:
            for f in non_init_files:
                filename = os.path.basename(f['path'])
                if filename == pattern or filename.lower() == pattern:
                    self.main_app_file = f['path']
                    return self.main_app_file

        # If no priority match, take first runnable file
        if runnable_files:
            self.main_app_file = runnable_files[0]['path']
            return self.main_app_file

        # IMPROVED: For factory patterns, look for files that actually instantiate the app
        # rather than just define the factory
        for f in self.flask_files:
            try:
                with open(f['full_path'], 'r', encoding='utf-8') as file:
                    content = file.read()

                # Look for files that both import create_app AND create an app instance
                if ('create_app' in content and
                        any(pattern in content for pattern in [
                            'app = create_app()',
                            'application = create_app()',
                            'if __name__' in content
                        ])):
                    self.main_app_file = f['path']
                    return self.main_app_file
            except:
                continue

        # FALLBACK: Look for factory files only if no other option
        factory_files = [f for f in self.flask_files if f['is_factory']]
        if factory_files:
            # Prefer non-__init__.py factory files
            non_init_factories = [f for f in factory_files if not f['path'].endswith('__init__.py')]
            if non_init_factories:
                self.main_app_file = non_init_factories[0]['path']
            else:
                self.main_app_file = factory_files[0]['path']

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

    def _create_run_script(self):
        """IMPROVED: Create a run.py script based on project analysis"""
        try:
            # Find the best Flask app setup
            app_factory = self.project_info.get('app_factory')
            flask_files = self.project_info.get('flask_files', [])

            run_script_content = None

            # IMPROVED: Better factory detection
            if app_factory or any(f.get('is_factory') for f in flask_files):
                # Find the factory module
                factory_file = None
                factory_module = None

                # Look for __init__.py files with create_app
                for f in flask_files:
                    if f.get('is_factory'):
                        factory_file = f['path']
                        # Convert path to module name
                        if factory_file.endswith('__init__.py'):
                            # For __init__.py files, use the parent directory as module
                            factory_module = os.path.dirname(factory_file).replace('/', '.').replace('\\', '.')
                        else:
                            factory_module = os.path.splitext(factory_file.replace('/', '.').replace('\\', '.'))[0]
                        break

                if factory_module:
                    run_script_content = f'''#!/usr/bin/env python3
    """
    Auto-generated Flask run script for {self.project_path}
    Generated by Flask Studio Pro
    """
    import os
    import sys

    # Add project root to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        # Import the create_app factory function
        from {factory_module} import create_app

        # Create the Flask app
        app = create_app()

        if __name__ == '__main__':
            # Run the development server
            app.run(
                host='127.0.0.1',
                port=5000,
                debug=True
            )

    except ImportError as e:
        print(f"Import error: {{e}}")
        print("Please check your project structure and dependencies.")
        print(f"Tried to import create_app from: {factory_module}")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating Flask app: {{e}}")
        sys.exit(1)
    '''
            else:
                # Look for a file with direct Flask app creation
                app_file = None
                app_var = None

                for f in flask_files:
                    if f.get('has_app_creation') and f.get('app_variable'):
                        app_file = f['path']
                        app_var = f['app_variable']
                        break

                if app_file and app_var:
                    module_name = os.path.splitext(app_file.replace('/', '.').replace('\\', '.'))[0]

                    run_script_content = f'''#!/usr/bin/env python3
    """
    Auto-generated Flask run script for {self.project_path}
    Generated by Flask Studio Pro
    """
    import os
    import sys

    # Add project root to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from {module_name} import {app_var}

        if __name__ == '__main__':
            # Run the development server
            {app_var}.run(
                host='127.0.0.1',
                port=5000,
                debug=True
            )

    except ImportError as e:
        print(f"Import error: {{e}}")
        print("Please check your project structure and dependencies.")
        sys.exit(1)
    except Exception as e:
        print(f"Error running Flask app: {{e}}")
        sys.exit(1)
    '''

            if run_script_content:
                run_script_path = os.path.join(self.project_path, 'run.py')
                with open(run_script_path, 'w', encoding='utf-8') as f:
                    f.write(run_script_content)

                self.log_message(f"📝 Created run script: {run_script_path}")
                return True
            else:
                self.log_message("⚠️ Could not determine Flask app structure for run script")
                return False

        except Exception as e:
            self.log_message(f"❌ Error creating run script: {str(e)}")
            return False

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

        # NEW: Added diagnostic button
        diagnose_btn = ttk.Button(dir_frame, text="Diagnose", command=self.diagnose_project)
        diagnose_btn.grid(row=0, column=3, padx=(5, 0))

    def diagnose_project(self):
        """Provide detailed diagnostic information about the Flask project"""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please select a project directory first.")
            return

        self.log_message("🔍 Starting detailed project diagnosis...")
        self.log_message("=" * 60)

        # Basic project info
        self.log_message(f"📁 Project Directory: {self.project_path}")
        self.log_message(f"📁 Project Name: {os.path.basename(self.project_path)}")

        # Check for common Flask files
        common_files = ['app.py', 'run.py', 'wsgi.py', 'main.py', 'server.py', '__init__.py']
        self.log_message("\n📋 Checking for common Flask files:")
        for file in common_files:
            file_path = os.path.join(self.project_path, file)
            if os.path.exists(file_path):
                self.log_message(f"  ✅ Found: {file}")
            else:
                self.log_message(f"  ❌ Missing: {file}")

        # Check directory structure
        self.log_message("\n📂 Directory Structure (first 2 levels):")
        for root, dirs, files in os.walk(self.project_path):
            level = root.replace(self.project_path, '').count(os.sep)
            if level < 2:
                indent = '  ' * level
                self.log_message(f"{indent}{os.path.basename(root)}/")
                subindent = '  ' * (level + 1)
                for file in files[:5]:  # Limit to first 5 files
                    if file.endswith('.py'):
                        self.log_message(f"{subindent}📄 {file}")
                if len(files) > 5:
                    self.log_message(f"{subindent}... and {len(files) - 5} more files")

        # Scan for Flask content
        self.log_message("\n🔍 Scanning for Flask code:")
        flask_files = self._scan_for_flask_files()

        if not flask_files:
            self.log_message("  ❌ No Flask files found!")
            self.log_message("  💡 Make sure you have Python files that import Flask")
        else:
            self.log_message(f"  ✅ Found {len(flask_files)} Flask files:")
            for f in flask_files:
                self.log_message(f"    📄 {f['path']}")
                if f['has_app_creation']:
                    self.log_message(f"      🏭 Creates Flask app")
                if f['is_factory']:
                    self.log_message(f"      🏭 Has app factory (create_app)")
                if f['has_app_run']:
                    self.log_message(f"      ▶️ Has app.run() call")

                # Show a snippet of the file
                try:
                    with open(f['full_path'], 'r', encoding='utf-8') as file:
                        content = file.read()
                        lines = content.split('\n')[:10]  # First 10 lines
                        self.log_message(f"      📝 First few lines:")
                        for i, line in enumerate(lines, 1):
                            if line.strip():
                                self.log_message(f"        {i:2d}: {line[:60]}{'...' if len(line) > 60 else ''}")
                except Exception as e:
                    self.log_message(f"      ❌ Error reading file: {e}")

        # Check Python environment
        self.log_message(f"\n🐍 Python Environment:")
        python_path = self.python_var.get()
        self.log_message(f"  📍 Python Path: {python_path}")

        if os.path.exists(python_path):
            self.log_message(f"  ✅ Python executable exists")
            # Check Python version
            try:
                result = subprocess.run([python_path, '--version'],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.log_message(f"  🐍 Version: {result.stdout.strip()}")
                else:
                    self.log_message(f"  ⚠️ Could not get Python version")
            except Exception as e:
                self.log_message(f"  ⚠️ Error checking Python version: {e}")
        else:
            self.log_message(f"  ❌ Python executable not found!")

        # Check Flask installation
        self.log_message(f"\n🌶️ Flask Installation:")
        try:
            result = subprocess.run([
                python_path, '-c',
                'import flask; print(f"Flask {flask.__version__} - {flask.__file__}")'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_message(f"  ✅ {result.stdout.strip()}")
            else:
                self.log_message(f"  ❌ Flask not installed or accessible")
                self.log_message(f"  📝 Error: {result.stderr.strip()}")
        except Exception as e:
            self.log_message(f"  ❌ Error checking Flask: {e}")

        # Test import capabilities
        self.log_message(f"\n🧪 Testing Import Capabilities:")
        if flask_files:
            test_file = flask_files[0]
            module_name = os.path.splitext(test_file['path'].replace('/', '.').replace('\\', '.'))[0]

            self.log_message(f"  🧪 Testing import of: {module_name}")
            try:
                result = subprocess.run([
                    python_path, '-c', f'import {module_name}; print("✅ Import successful")'
                ], capture_output=True, text=True, timeout=10, cwd=self.project_path)

                if result.returncode == 0:
                    self.log_message(f"  ✅ Module import successful")
                else:
                    self.log_message(f"  ❌ Module import failed:")
                    self.log_message(f"    📝 {result.stderr.strip()}")
            except Exception as e:
                self.log_message(f"  ❌ Error testing import: {e}")

        # Suggest solutions
        self.log_message(f"\n💡 Recommendations:")
        if not flask_files:
            self.log_message("  1. Ensure you have Python files with Flask imports")
            self.log_message("  2. Check that you're in the correct project directory")
        else:
            self.log_message("  1. Try the 'Create Run Script' option if startup fails")
            self.log_message("  2. Check the Console Output for detailed error messages")
            self.log_message("  3. Verify all dependencies are installed in your virtual environment")

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

        # NEW: Added diagnostic button
        diagnose_btn = ttk.Button(dir_frame, text="Diagnose", command=self.diagnose_project)
        diagnose_btn.grid(row=0, column=3, padx=(5, 0))
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

        # FLASK_APP Override
        ttk.Label(config_frame, text="FLASK_APP:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.flask_app_var = tk.StringVar()
        flask_app_entry = ttk.Entry(config_frame, textvariable=self.flask_app_var, width=30)
        flask_app_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(10, 0))

        auto_detect_btn = ttk.Button(config_frame, text="Auto-Detect", command=self.auto_detect_flask_app)
        auto_detect_btn.grid(row=2, column=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))

        # Python Interpreter Selection - FIXED: Made editable
        ttk.Label(config_frame, text="Python:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))

        self.python_var = tk.StringVar(value=sys.executable)
        python_frame = ttk.Frame(config_frame)
        python_frame.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        python_frame.columnconfigure(0, weight=1)

        # CHANGED: Removed state="readonly" to make it editable
        self.python_entry = ttk.Entry(python_frame, textvariable=self.python_var)
        self.python_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        detect_venv_btn = ttk.Button(python_frame, text="Detect Venv", command=self.detect_virtual_env)
        detect_venv_btn.grid(row=0, column=1, padx=(0, 5))

        # NEW: Added Browse button for Python executable
        browse_python_btn = ttk.Button(python_frame, text="Browse", command=self.browse_python_executable)
        browse_python_btn.grid(row=0, column=2)

        # Debug mode checkbox
        self.debug_var = tk.BooleanVar(value=True)
        debug_cb = ttk.Checkbutton(config_frame, text="Debug mode (auto-reload)",
                                   variable=self.debug_var)
        debug_cb.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
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

        # Update project analysis if directory already set
        if self.project_path:
            self.root.after(100, self.delayed_analyze_project)
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

        # FLASK_APP Override
        ttk.Label(config_frame, text="FLASK_APP:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.flask_app_var = tk.StringVar()
        flask_app_entry = ttk.Entry(config_frame, textvariable=self.flask_app_var, width=30)
        flask_app_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(10, 0))

        auto_detect_btn = ttk.Button(config_frame, text="Auto-Detect", command=self.auto_detect_flask_app)
        auto_detect_btn.grid(row=2, column=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))

        # Python Interpreter Selection - FIXED: Made editable
        ttk.Label(config_frame, text="Python:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))

        self.python_var = tk.StringVar(value=sys.executable)
        python_frame = ttk.Frame(config_frame)
        python_frame.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        python_frame.columnconfigure(0, weight=1)

        # CHANGED: Removed state="readonly" to make it editable
        self.python_entry = ttk.Entry(python_frame, textvariable=self.python_var)
        self.python_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        detect_venv_btn = ttk.Button(python_frame, text="Detect Venv", command=self.detect_virtual_env)
        detect_venv_btn.grid(row=0, column=1, padx=(0, 5))

        # NEW: Added Browse button for Python executable
        browse_python_btn = ttk.Button(python_frame, text="Browse", command=self.browse_python_executable)
        browse_python_btn.grid(row=0, column=2)

        # Debug mode checkbox
        self.debug_var = tk.BooleanVar(value=True)
        debug_cb = ttk.Checkbutton(config_frame, text="Debug mode (auto-reload)",
                                   variable=self.debug_var)
        debug_cb.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
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

        # Update project analysis if directory already set
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

    def browse_python_executable(self):
        """Browse for Python executable"""
        # Determine file extension based on OS
        if sys.platform.startswith('win'):
            filetypes = [("Python Executable", "python.exe"), ("All Files", "*.*")]
            initialname = "python.exe"
        else:
            filetypes = [("Python Executable", "python*"), ("All Files", "*")]
            initialname = "python"

        # Try to start from current python directory
        initial_dir = os.path.dirname(self.python_var.get()) if self.python_var.get() else ""

        python_path = filedialog.askopenfilename(
            title="Select Python Executable",
            initialdir=initial_dir,
            filetypes=filetypes
        )

        if python_path:
            self.python_var.set(python_path)
            self.log_message(f"📍 Python executable manually set: {python_path}")

            # Check if Flask is available in the selected Python
            self.check_flask_installation(python_path)
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
            self.auto_detect_flask_app()  # Auto-detect FLASK_APP after analysis

            self.log_message(f"✓ Project analysis complete. Found {len(self.project_info['flask_files'])} Flask files")

        except Exception as e:
            self.log_message(f"✗ Error analyzing project: {str(e)}")
            messagebox.showerror("Analysis Error", f"Failed to analyze project:\n{str(e)}")

    def auto_detect_flask_app(self):
        """Auto-detect the correct FLASK_APP setting"""
        if not self.project_info:
            return

        try:
            main_app_file = self.project_info.get('main_app_file')
            if main_app_file:
                detector = SmartFlaskDetector(self.project_path, main_app_file)
                flask_app_setting = detector.get_flask_app_setting()
                self.flask_app_var.set(flask_app_setting)
                self.log_message(f"🧠 Auto-detected FLASK_APP: {flask_app_setting}")
            else:
                self.log_message("⚠ Could not auto-detect FLASK_APP - no main app file found")
        except Exception as e:
            self.log_message(f"⚠ Error auto-detecting FLASK_APP: {str(e)}")

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
                if f['has_app_creation']:
                    details.append("creates app")
                if f['app_variable']:
                    details.append(f"app var: {f['app_variable']}")

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

        # Set FLASK_APP - use manual override if set, otherwise use smart detection
        if run_method == 'flask_run':
            if self.flask_app_var.get().strip():
                # Use manual override
                flask_app_setting = self.flask_app_var.get().strip()
                env['FLASK_APP'] = flask_app_setting
                self.log_message(f"Using manual FLASK_APP override: {flask_app_setting}")
            else:
                # Use smart detection
                flask_app_setting = self.get_smart_flask_app_setting(main_app_file)
                env['FLASK_APP'] = flask_app_setting
                self.log_message(f"🧠 Smart detection: FLASK_APP={flask_app_setting}")

            # Test the FLASK_APP setting before starting the server
            if not self.test_flask_app_setting(env['FLASK_APP'], python_path, env):
                # If the current setting fails, try alternatives
                alternative_settings = self.get_alternative_flask_app_settings(main_app_file)

                working_setting = None
                for alt_setting in alternative_settings:
                    self.log_message(f"🔄 Trying alternative: {alt_setting}")
                    if self.test_flask_app_setting(alt_setting, python_path, env):
                        working_setting = alt_setting
                        break

                if working_setting:
                    env['FLASK_APP'] = working_setting
                    self.flask_app_var.set(working_setting)  # Update the UI
                    self.log_message(f"✓ Found working FLASK_APP: {working_setting}")
                else:
                    self.log_message("❌ No working FLASK_APP setting found. Trying direct execution...")
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
        if run_method == 'flask_run':
            self.log_message(f"FLASK_APP: {env.get('FLASK_APP', 'Not set')}")
        self.log_message("-" * 60)

    def _run_server(self, flask_file, env, run_method):
        """Run the Flask server in a separate process"""
        try:
            # Change to project directory
            os.chdir(self.project_path)
            python_path = self.python_var.get()

            if run_method == 'flask_run':
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
            if run_method == 'flask_run' and 'FLASK_APP' in env:
                self.log_message(f"Environment: FLASK_APP={env['FLASK_APP']}")

            # Set encoding explicitly and add error handling
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                cwd=self.project_path
            )

            # Update status
            self.root.after(1000, lambda: self.status_var.set("Server: Running"))

            # Track if we've seen a successful start
            startup_successful = False
            error_lines = []

            # Read output and display in console
            for line in iter(self.server_process.stdout.readline, ''):
                if line.strip():
                    self.root.after(0, lambda l=line.strip(): self.log_message(l))

                    # Check for successful startup indicators
                    if any(indicator in line.lower() for indicator in [
                        'running on', 'serving flask app', '* running on http'
                    ]):
                        startup_successful = True

                    # Check for startup errors
                    if any(error_indicator in line.lower() for error_indicator in [
                        'traceback', 'error:', 'failed to', 'could not', 'importerror', 'modulenotfounderror'
                    ]):
                        error_lines.append(line.strip())

                # Check if process ended early (within first 5 seconds)
                if self.server_process.poll() is not None:
                    if not startup_successful and error_lines:
                        # Server failed to start, try to provide helpful suggestions
                        self.root.after(0, lambda: self._handle_startup_failure(error_lines))
                    break

            # Server stopped
            self.root.after(0, self._server_stopped)

        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"Error starting server: {str(e)}"))
            self.root.after(0, self._server_stopped)

    def _handle_startup_failure(self, error_lines):
        """Handle server startup failures with helpful suggestions"""
        self.log_message("🚨 Server failed to start. Analyzing error...")

        # Analyze the error
        error_text = " ".join(error_lines).lower()
        suggestions = []

        if 'could not locate a flask application' in error_text or 'failed to find flask application' in error_text:
            suggestions.extend([
                "❌ Flask app not found. Try these solutions:",
                "1. Check the FLASK_APP setting in the Server Configuration",
                "2. Click 'Auto-Detect' to automatically find the correct setting",
                "3. Try changing Run Method to 'direct' instead of 'flask_run'",
                "4. Ensure your app file has a Flask app instance named 'app'"
            ])
        elif 'importerror' in error_text or 'modulenotfounderror' in error_text:
            suggestions.extend([
                "❌ Import error detected. Try these solutions:",
                "1. Check if all required packages are installed in your virtual environment",
                "2. Verify the Python path is pointing to the correct virtual environment",
                "3. Run 'pip install -r requirements.txt' if you have a requirements file",
                "4. Check for typos in import statements"
            ])
        elif 'permission denied' in error_text:
            suggestions.extend([
                "❌ Permission error. Try these solutions:",
                "1. Run as administrator/with sudo",
                "2. Check file permissions",
                "3. Ensure the Python executable is accessible"
            ])
        else:
            suggestions.extend([
                "❌ Server startup failed. Try these solutions:",
                "1. Check the Console Output tab for detailed error information",
                "2. Try changing the Run Method to 'direct'",
                "3. Verify your Flask app structure and imports",
                "4. Check if the port is already in use"
            ])

        # Show suggestions with option to try direct mode
        for suggestion in suggestions:
            self.log_message(suggestion)

        # Ask user if they want to try direct execution mode
        if hasattr(self, 'run_method_var') and self.run_method_var.get() != 'direct':
            self.root.after(1000, self._offer_direct_mode_retry)

    def test_flask_app_setting(self, flask_app_setting, python_path, env):
        """Test if a FLASK_APP setting can load successfully"""
        try:
            self.log_message(f"🧪 Testing FLASK_APP: {flask_app_setting}")

            # Create a test environment
            test_env = env.copy()
            test_env['FLASK_APP'] = flask_app_setting

            # Test by trying to load the app
            test_cmd = [
                python_path, '-c',
                'import os; from flask.cli import ScriptInfo; '
                f'os.environ["FLASK_APP"] = "{flask_app_setting}"; '
                'info = ScriptInfo(); app = info.load_app(); print("✓ App loaded successfully")'
            ]

            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.project_path,
                env=test_env
            )

            if result.returncode == 0:
                self.log_message(f"✓ FLASK_APP test passed: {flask_app_setting}")
                return True
            else:
                self.log_message(f"❌ FLASK_APP test failed: {result.stderr.strip()}")
                return False

        except Exception as e:
            self.log_message(f"❌ Error testing FLASK_APP: {str(e)}")
            return False

    # IMPROVED: Better alternative FLASK_APP settings
    def get_alternative_flask_app_settings(self, main_app_file):
        """Generate alternative FLASK_APP settings to try - IMPROVED VERSION"""
        alternatives = []

        if not main_app_file:
            return alternatives

        # STEP 1: Analyze the actual project structure
        project_name = os.path.basename(self.project_path).lower()
        flask_files_found = self._scan_for_flask_files()

        # STEP 2: Look for the actual entry point files first
        entry_point_files = [
            f"{project_name}app.py",
            f"{project_name}.py",
            "wsgi.py",
            "app.py",
            "run.py",
            "main.py"
        ]

        for entry_file in entry_point_files:
            entry_path = os.path.join(self.project_path, entry_file)
            if os.path.exists(entry_path):
                module_name = os.path.splitext(entry_file)[0]
                alternatives.extend([
                    f"{module_name}:app",
                    f"{module_name}:application",
                    module_name  # For factory functions
                ])

        # STEP 3: Add alternatives based on actual Flask files found
        for flask_file_info in flask_files_found:
            rel_path = flask_file_info['path']

            # Skip __init__.py files for direct execution alternatives
            if rel_path.endswith('__init__.py'):
                # For __init__.py files, try the parent directory as module
                parent_dir = os.path.dirname(rel_path)
                if parent_dir:
                    parent_module = parent_dir.replace('/', '.').replace('\\', '.')
                    alternatives.append(parent_module)
                    if flask_file_info.get('is_factory'):
                        alternatives.append(f"{parent_module}:create_app")
                continue

            module_path = os.path.splitext(rel_path.replace('/', '.').replace('\\', '.'))[0]

            if flask_file_info.get('has_app_creation'):
                alternatives.extend([
                    f"{module_path}:app",
                    f"{module_path}:application"
                ])

            if flask_file_info.get('is_factory'):
                alternatives.extend([
                    module_path,
                    f"{module_path}:create_app"
                ])

        # Remove duplicates while preserving order
        seen = set()
        unique_alternatives = []
        for alt in alternatives:
            if alt not in seen:
                seen.add(alt)
                unique_alternatives.append(alt)

        return unique_alternatives

    def _scan_for_flask_files(self):
        """Scan the project directory for Flask files and return detailed info"""
        flask_files = []

        for root, dirs, files in os.walk(self.project_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if
                       not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.venv']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.project_path)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Check if it's a Flask file
                        is_flask = any([
                            'from flask import' in content,
                            'import flask' in content,
                            'Flask(' in content,
                            '@app.route' in content,
                            'Blueprint(' in content,
                            'create_app(' in content
                        ])

                        if is_flask:
                            flask_files.append({
                                'path': rel_path,
                                'full_path': file_path,
                                'has_app_creation': bool(re.search(r'\w+\s*=\s*Flask\s*\(', content)),
                                'is_factory': 'def create_app' in content,
                                'has_app_run': 'app.run(' in content or (
                                            '__name__' in content and '__main__' in content),
                                'content_preview': content[:200] + '...' if len(content) > 200 else content
                            })

                    except Exception:
                        continue

        return flask_files

    def _handle_startup_failure(self, error_lines):
        """Handle server startup failures with helpful suggestions"""
        self.log_message("🚨 Server failed to start. Analyzing error...")

        # Analyze the error
        error_text = " ".join(error_lines).lower()
        suggestions = []

        if 'could not locate a flask application' in error_text or 'failed to find flask application' in error_text:
            suggestions.extend([
                "❌ Flask app not found. Try these solutions:",
                "1. Check the FLASK_APP setting in the Server Configuration",
                "2. Click 'Auto-Detect' to automatically find the correct setting",
                "3. Try changing Run Method to 'direct' instead of 'flask_run'",
                "4. Ensure your app file has a Flask app instance named 'app'"
            ])
        elif 'importerror' in error_text or 'modulenotfounderror' in error_text:
            suggestions.extend([
                "❌ Import error detected. Try these solutions:",
                "1. Check if all required packages are installed in your virtual environment",
                "2. Verify the Python path is pointing to the correct virtual environment",
                "3. Run 'pip install -r requirements.txt' if you have a requirements file",
                "4. Check for typos in import statements"
            ])
        elif 'permission denied' in error_text:
            suggestions.extend([
                "❌ Permission error. Try these solutions:",
                "1. Run as administrator/with sudo",
                "2. Check file permissions",
                "3. Ensure the Python executable is accessible"
            ])
        else:
            suggestions.extend([
                "❌ Server startup failed. Try these solutions:",
                "1. Check the Console Output tab for detailed error information",
                "2. Try changing the Run Method to 'direct'",
                "3. Verify your Flask app structure and imports",
                "4. Check if the port is already in use"
            ])

        # Show suggestions with option to try direct mode
        for suggestion in suggestions:
            self.log_message(suggestion)

        # Ask user if they want to try direct execution mode
        if hasattr(self, 'run_method_var') and self.run_method_var.get() != 'direct':
            self.root.after(1000, self._offer_direct_mode_retry)
        else:
            # We're already in direct mode, offer to create a run script
            self.root.after(1000, self._offer_create_run_script)

    def _offer_create_run_script(self):
        """Offer to create a simple run script for the Flask app"""
        response = messagebox.askyesno(
            "Create Run Script?",
            "Both 'flask run' and direct execution failed.\n\n"
            "Would you like me to create a simple 'run.py' script "
            "that can start your Flask application?\n\n"
            "This will analyze your project structure and create "
            "an appropriate startup script."
        )

        if response:
            self.log_message("🛠️ Creating run script...")
            if self._create_run_script():
                self.log_message("✅ Run script created successfully!")
                # Analyze project again to pick up the new file
                self.analyze_project()
                # Ask if they want to try running with the new script
                retry_response = messagebox.askyesno(
                    "Try New Script?",
                    "Run script created successfully!\n\n"
                    "Would you like to try starting the server with the new 'run.py' script?"
                )
                if retry_response:
                    # Update the main app file to the new run.py
                    self.project_info['main_app_file'] = 'run.py'
                    self.root.after(1000, self.start_server)
            else:
                self.log_message("❌ Failed to create run script. Please check the console for details.")

    def _create_run_script(self):
        """Create a run.py script based on project analysis"""
        try:
            # Find the best Flask app setup
            app_factory = self.project_info.get('app_factory')
            flask_files = self.project_info.get('flask_files', [])

            run_script_content = None

            if app_factory:
                # Use app factory pattern
                factory_module = app_factory['module']
                factory_function = app_factory['function']

                run_script_content = f'''#!/usr/bin/env python3
"""
Auto-generated Flask run script
"""
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from {factory_module} import {factory_function}

    # Create the Flask app
    app = {factory_function}()

    if __name__ == '__main__':
        # Run the development server
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True
        )

except ImportError as e:
    print(f"Import error: {{e}}")
    print("Please check your project structure and dependencies.")
    sys.exit(1)
except Exception as e:
    print(f"Error creating Flask app: {{e}}")
    sys.exit(1)
'''
            else:
                # Look for a file with direct Flask app creation
                app_file = None
                app_var = None

                for f in flask_files:
                    if f.get('has_app_creation') and f.get('app_variable'):
                        app_file = f['path']
                        app_var = f['app_variable']
                        break

                if app_file and app_var:
                    module_name = os.path.splitext(app_file.replace('/', '.').replace('\\', '.'))[0]

                    run_script_content = f'''#!/usr/bin/env python3
"""
Auto-generated Flask run script
"""
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from {module_name} import {app_var}

    if __name__ == '__main__':
        # Run the development server
        {app_var}.run(
            host='127.0.0.1',
            port=5000,
            debug=True
        )

except ImportError as e:
    print(f"Import error: {{e}}")
    print("Please check your project structure and dependencies.")
    sys.exit(1)
except Exception as e:
    print(f"Error running Flask app: {{e}}")
    sys.exit(1)
'''

            if run_script_content:
                run_script_path = os.path.join(self.project_path, 'run.py')
                with open(run_script_path, 'w', encoding='utf-8') as f:
                    f.write(run_script_content)

                self.log_message(f"📝 Created run script: {run_script_path}")
                return True
            else:
                self.log_message("⚠️ Could not determine Flask app structure for run script")
                return False

        except Exception as e:
            self.log_message(f"❌ Error creating run script: {str(e)}")
            return False

    def get_smart_flask_app_setting(self, flask_file):
        """Use smart detection to determine correct FLASK_APP setting"""
        detector = SmartFlaskDetector(self.project_path, flask_file)
        flask_app = detector.get_flask_app_setting()

        self.log_message(f"🧠 Smart detection result: FLASK_APP={flask_app}")
        return flask_app

    def _offer_direct_mode_retry(self):
        """Offer to retry with direct execution mode"""
        response = messagebox.askyesno(
            "Try Direct Mode?",
            "The server failed to start with 'flask run'.\n\n"
            "Would you like to try running the Flask app directly instead?\n"
            "(This will change the Run Method to 'direct')"
        )

        if response:
            self.run_method_var.set('direct')
            self.log_message("🔄 Switching to direct execution mode...")
            # Small delay before restarting
            self.root.after(1000, self.start_server)

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
            'debug_mode': self.debug_var.get(),
            'flask_app_override': self.flask_app_var.get() if hasattr(self, 'flask_app_var') else '',
            'python_path': self.python_var.get()  # NEW: Save python path
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

                    # NEW: Load python path if available
                    saved_python_path = config.get('python_path', sys.executable)
                    if os.path.exists(saved_python_path):
                        # Only use saved path if it still exists
                        pass  # Will be set after widgets are created
                    else:
                        saved_python_path = sys.executable

                    # Store for later use
                    self._saved_python_path = saved_python_path

            except Exception as e:
                print(f"Error loading config: {e}")
                self._saved_python_path = sys.executable

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


class SmartFlaskDetector:
    """Intelligently detects the correct FLASK_APP setting for any Flask project"""

    def __init__(self, project_path, main_app_file):
        self.project_path = project_path
        self.main_app_file = main_app_file
        self.project_name = os.path.basename(project_path).lower()

    def get_flask_app_setting(self):
        """
        Dynamically determine the correct FLASK_APP setting by analyzing the project structure.
        IMPROVED to handle complex factory patterns better.
        """

        # Strategy 1: Check for project-specific app files (like skinsightapp.py)
        project_specific = self._check_project_specific_files()
        if project_specific:
            return project_specific

        # Strategy 2: Handle factory patterns better
        factory_pattern = self._improved_factory_check()
        if factory_pattern:
            return factory_pattern

        # Strategy 3: Check if main file has ready-to-use app variable
        app_var = self._check_main_file_app_variable()
        if app_var:
            return app_var

        # Strategy 4: Check for common WSGI patterns
        wsgi_pattern = self._check_wsgi_patterns()
        if wsgi_pattern:
            return wsgi_pattern

        # Strategy 5: Deep analysis of Flask instantiation
        deep_pattern = self._deep_flask_analysis()
        if deep_pattern:
            return deep_pattern

        # Fallback: Use filename as module
        module_name = os.path.splitext(self.main_app_file.replace('/', '.').replace('\\', '.'))[0]
        return f"{module_name}:app"

    def _improved_factory_check(self):
        """IMPROVED factory pattern detection"""
        # Look for the main entry point that uses the factory
        main_file_path = os.path.join(self.project_path, self.main_app_file)

        try:
            with open(main_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if this file imports create_app and creates an app instance
            if 'create_app' in content:
                # Look for app variable creation
                app_patterns = [
                    r'(\w+)\s*=\s*create_app\s*\(',
                    r'(\w+)\s*=\s*[\w\.]+\.create_app\s*\(',
                ]

                for pattern in app_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        app_var = matches[0]
                        module_name = os.path.splitext(self.main_app_file.replace('/', '.').replace('\\', '.'))[0]
                        print(f"✓ Found factory usage in main file: {module_name}:{app_var}")
                        return f"{module_name}:{app_var}"

            # If main file doesn't use factory, look for the factory module itself
            factory_info = self._find_app_factories()
            if factory_info:
                # Try to use the factory directly
                factory = factory_info[0]
                print(f"✓ Using factory directly: {factory['module']}")
                return factory['module']  # Just the module name for factory functions

        except Exception as e:
            print(f"Error in improved factory check: {e}")

        return None

    def _check_project_specific_files(self):
        """Check for project-specific app files like projectnameapp.py"""
        if not self.main_app_file:
            return None

        filename = os.path.basename(self.main_app_file)
        filename_no_ext = os.path.splitext(filename)[0]

        # Pattern: projectnameapp.py
        if filename_no_ext.endswith('app') and len(filename_no_ext) > 3:
            try:
                file_path = os.path.join(self.project_path, self.main_app_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for app variable assignments
                app_patterns = [
                    r'(\w+)\s*=\s*Flask\s*\(',
                    r'(\w+)\s*=\s*create_app\s*\(',
                    r'(\w+)\s*=\s*[\w\.]+\.create_app\s*\(',
                ]

                for pattern in app_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        app_var = matches[0]
                        print(f"✓ Found project-specific app file: {filename_no_ext}:{app_var}")
                        return f"{filename_no_ext}:{app_var}"

                # Default app variable for project-specific files
                print(f"✓ Using default app variable for project file: {filename_no_ext}:app")
                return f"{filename_no_ext}:app"

            except Exception as e:
                print(f"Error analyzing project-specific file: {e}")

        return None

    def _check_main_file_app_variable(self):
        """Check if the main file has a direct app variable"""
        if not self.main_app_file:
            return None

        file_path = os.path.join(self.project_path, self.main_app_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for direct app assignments (not function definitions)
            patterns = [
                (r'^(\w+)\s*=\s*Flask\s*\(', 'Flask instantiation'),
                (r'^(\w+)\s*=\s*create_app\s*\(', 'create_app call'),
                (r'^(\w+)\s*=\s*[\w\.]+\.create_app\s*\(', 'module.create_app call'),
                (r'^(\w+)\s*=\s*application', 'application alias'),
            ]

            for pattern, description in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                if matches:
                    var_name = matches[0]
                    module_name = os.path.splitext(self.main_app_file.replace('/', '.').replace('\\', '.'))[0]
                    print(f"✓ Found {description}: {var_name}")
                    return f"{module_name}:{var_name}"

        except Exception as e:
            print(f"Error reading main file: {e}")

        return None

    def _check_wsgi_patterns(self):
        """Check for common WSGI file patterns"""
        wsgi_files = ['wsgi.py', 'application.py', 'app.py']

        for wsgi_file in wsgi_files:
            wsgi_path = os.path.join(self.project_path, wsgi_file)
            if os.path.exists(wsgi_path) and wsgi_file != os.path.basename(self.main_app_file):
                app_var = self._find_app_variable_in_file(wsgi_path)
                if app_var:
                    module_name = os.path.splitext(wsgi_file)[0]
                    print(f"✓ Found WSGI pattern in {wsgi_file}: {app_var}")
                    return f"{module_name}:{app_var}"

        return None

    def _check_factory_patterns(self):
        """Check for app factory patterns and how they're used"""
        factory_info = self._find_app_factories()

        if not factory_info:
            return None

        # Check if the main file imports and exposes the factory
        if self.main_app_file:
            main_file_path = os.path.join(self.project_path, self.main_app_file)
            try:
                with open(main_file_path, 'r', encoding='utf-8') as f:
                    main_content = f.read()

                # Check if main file imports the factory and creates an app
                for factory in factory_info:
                    factory_module = factory['module']
                    factory_func = factory['function']

                    # Look for imports of this factory
                    import_patterns = [
                        f"from {factory_module} import {factory_func}",
                        f"from {factory_module} import create_app",
                        f"import {factory_module}",
                    ]

                    for pattern in import_patterns:
                        if pattern in main_content:
                            # Main file imports the factory, likely creates app variable
                            app_var = self._find_app_variable_in_file(main_file_path)
                            if app_var:
                                module_name = os.path.splitext(self.main_app_file.replace('/', '.').replace('\\', '.'))[
                                    0]
                                print(f"✓ Main file uses factory, exposes as: {app_var}")
                                return f"{module_name}:{app_var}"

            except Exception as e:
                print(f"Error analyzing main file for factory usage: {e}")

        # Use factory directly if no wrapper found
        if factory_info:
            factory = factory_info[0]  # Use first factory found
            print(f"✓ Using factory directly: {factory['module']}:{factory['function']}")
            return f"{factory['module']}:{factory['function']}"

        return None

    def _deep_flask_analysis(self):
        """Deep analysis of all Python files to understand Flask setup"""
        flask_apps = []

        # Scan all Python files for Flask instantiation
        for root, dirs, files in os.walk(self.project_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if
                       not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.venv']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.project_path)

                    apps = self._analyze_file_for_flask_apps(file_path, rel_path)
                    flask_apps.extend(apps)

        if not flask_apps:
            return None

        # Prioritize apps based on likelihood of being the main app
        priority_order = [
            lambda app: app['file'] == self.main_app_file,  # Main file gets highest priority
            lambda app: app['file'] in ['wsgi.py', 'app.py', 'application.py'],  # Common names
            lambda app: app['file'].endswith('app.py'),  # Any file ending with app.py
            lambda app: app['type'] == 'direct',  # Direct instantiation over factories
            lambda app: 'main' in app['file'] or 'run' in app['file'],  # Main/run files
        ]

        for priority_func in priority_order:
            for app in flask_apps:
                if priority_func(app):
                    print(f"✓ Selected app by priority: {app['flask_app']}")
                    return app['flask_app']

        # Fallback to first app found
        if flask_apps:
            print(f"✓ Using first app found: {flask_apps[0]['flask_app']}")
            return flask_apps[0]['flask_app']

        return None

    def _find_app_variable_in_file(self, file_path):
        """Find Flask app variable in a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for app variable assignments
            patterns = [
                r'^(app)\s*=\s*Flask\s*\(',
                r'^(application)\s*=\s*Flask\s*\(',
                r'^(app)\s*=\s*create_app\s*\(',
                r'^(application)\s*=\s*create_app\s*\(',
                r'^(app)\s*=\s*[\w\.]+\s*\(',
                r'^(application)\s*=\s*[\w\.]+\s*\(',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                if matches:
                    return matches[0]

        except Exception:
            pass

        return None

    def _find_app_factories(self):
        """Find app factory functions in the project"""
        factories = []

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if
                       not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.venv']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.project_path)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Look for factory function definitions
                        factory_pattern = r'def\s+(create_app|make_app|app_factory)\s*\([^)]*\):'
                        matches = re.findall(factory_pattern, content)

                        for func_name in matches:
                            module_path = rel_path.replace('\\', '/').replace('.py', '').replace('/', '.')
                            if module_path.endswith('.__init__'):
                                module_path = module_path[:-9]  # Remove .__init__

                            factories.append({
                                'function': func_name,
                                'module': module_path,
                                'file': rel_path
                            })

                    except Exception:
                        continue

        return factories

    def _analyze_file_for_flask_apps(self, file_path, rel_path):
        """Analyze a single file for Flask app definitions"""
        apps = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Direct Flask instantiation
            direct_pattern = r'^(\w+)\s*=\s*Flask\s*\('
            direct_matches = re.findall(direct_pattern, content, re.MULTILINE)

            for var_name in direct_matches:
                module_path = rel_path.replace('\\', '/').replace('.py', '').replace('/', '.')
                apps.append({
                    'type': 'direct',
                    'variable': var_name,
                    'module': module_path,
                    'file': rel_path,
                    'flask_app': f"{module_path}:{var_name}"
                })

            # Factory usage (create_app calls)
            factory_pattern = r'^(\w+)\s*=\s*create_app\s*\('
            factory_matches = re.findall(factory_pattern, content, re.MULTILINE)

            for var_name in factory_matches:
                module_path = rel_path.replace('\\', '/').replace('.py', '').replace('/', '.')
                apps.append({
                    'type': 'factory_call',
                    'variable': var_name,
                    'module': module_path,
                    'file': rel_path,
                    'flask_app': f"{module_path}:{var_name}"
                })

        except Exception:
            pass

        return apps


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

    # Load saved configuration values after widgets are created
    if hasattr(app, '_saved_python_path'):
        app.python_var.set(app._saved_python_path)

    # Load other saved config values
    if os.path.exists(app.config_file):
        try:
            with open(app.config_file, 'r') as f:
                config = json.load(f)

                # Load flask_app_override
                flask_app_override = config.get('flask_app_override', '')
                app.flask_app_var.set(flask_app_override)

                # Load run method
                run_method = config.get('run_method', 'auto')
                app.run_method_var.set(run_method)

                # Load debug mode
                debug_mode = config.get('debug_mode', True)
                app.debug_var.set(debug_mode)

        except Exception as e:
            print(f"Error loading additional config: {e}")

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