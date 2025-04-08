import os
import sys
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import argparse
from datetime import datetime

from config.config import API_URL
from src.api.api_client import APIClient
from src.database.db_manager import DatabaseManager
from src.device.attendance_processor import AttendanceProcessor
from src.scheduler.user_importer import UserImporter
from src.ui.config_interface import ConfigInterface
from src.scheduler.attendance_collector import AttendanceCollector
from src.scheduler.api_uploader import APIUploader
from src.ui.records_interface import RecordsInterface
from src.ui.users_interface import UsersInterface

# Define color constants
COLOR_SUCCESS = "#4CAF50"  # Green for success states
COLOR_ERROR = "#F44336"  # Red for error/stopped states
COLOR_WARNING = "#FF9800"  # Orange for warning states
COLOR_NEUTRAL = "#757575"  # Gray for neutral states


# Configure logging
def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Create a unique log filename based on timestamp
    log_filename = f'logs/attendance_system_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger('attendance_system')


class AttendanceSystemApp:
    def __init__(self):
        """Initialize the main application."""
        self.logger = setup_logging()
        self.db_manager = DatabaseManager()
        self.config = None
        self.users = None
        self.collector_thread = None
        self.uploader_thread = None
        self.user_importer_thread = None
        self.collector = AttendanceCollector(self.db_manager)
        self.uploader = APIUploader(self.db_manager)
        self.user_importer = UserImporter(self.db_manager)
        self.root = tk.Tk()
        self.root.withdraw()

        self.logo_img = None

        # UI instance variables for status labels
        self.status_label = None
        self.collector_status_label = None
        self.uploader_status_label = None
        self.user_importer_status_label = None

        # Test status variables with custom formatting
        self.device_test_var = tk.StringVar(value="● Device Connection: Not Tested")
        self.api_test_var = tk.StringVar(value="● API Connection: Not Tested")
        self.connectivity_success = False
        self.logger.info("Attendance System initializing")

    def run_connection_tests(self):
        """Run device and API connection tests and return True if both pass."""
        success = True
        try:
            # Get configuration
            self.config = self.db_manager.get_config()
            if not self.config:
                self.logger.error("No configuration found. Skipping connection tests.")
                self.update_status(self.device_test_var, "Device Connection", "Not Configured", "error")
                self.update_status(self.api_test_var, "API Connection", "Not Configured", "error")
                return False

            # Test device connection
            try:
                processor = AttendanceProcessor(
                    ip=self.config.device_ip,
                    port=self.config.device_port
                )

                if processor.connect():
                    self.users = processor.get_users() or []
                    processor.disconnect()
                    self.update_status(self.device_test_var, "Device Connection", "Connected", "success")
                    self.logger.info(f"Device connection successful.")
                else:
                    self.update_status(self.device_test_var, "Device Connection", "Failed", "error")
                    self.logger.warning("Device connection test failed.")
                    success = False
            except Exception as e:
                self.update_status(self.device_test_var, "Device Connection", "Error", "error")
                self.logger.error(f"Device connection test error: {e}")
                success = False

            # Test API connection
            try:
                api_client = APIClient(
                    api_url=API_URL,
                    company_id=self.config.company_id,
                    username=self.config.api_username,
                    password=self.config.api_password
                )

                if api_client.authenticate():
                    self.update_status(self.api_test_var, "API Connection", "Connected", "success")
                    self.logger.info("API authentication successful.")
                else:
                    self.update_status(self.api_test_var, "API Connection", "Failed", "error")
                    self.logger.warning("API authentication test failed.")
                    success = False
            except Exception as e:
                self.update_status(self.api_test_var, "API Connection", "Error", "error")
                self.logger.error(f"API connection test error: {e}")
                success = False

        except Exception as e:
            self.logger.error(f"Unexpected error in connection tests: {e}")
            self.update_status(self.device_test_var, "Device Connection", "Error", "error")
            self.update_status(self.api_test_var, "API Connection", "Error", "error")
            success = False

        self.connectivity_success = success
        # Update test button text based on results
        if hasattr(self, 'test_button'):
            self.test_button.config(
                text="Re-run Connection Tests" if self.connectivity_success else "Retry Connection Tests")

        return success

    def update_status(self, var, component, status, status_type):
        """Update a status variable with formatted text and color."""
        # Status type can be: 'success', 'warning', 'error', or 'neutral'
        icon = "✓" if status_type == "success" else "✗" if status_type == "error" else "●"
        var.set(f"{icon} {component}: {status}")

    def show_control_interface(self):
        # Configure window basics
        self.root.title("Attendance System Control Panel")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use('clam')

        # Define a new main background color
        main_bg_color = '#F0F0F0'  # Slightly lighter gray for better contrast

        # Load Logo
        self.load_logo()

        # Set styles with the new background color
        style.configure('TFrame', background=main_bg_color)
        style.configure('TLabel', background=main_bg_color, font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'))
        style.configure('Section.TLabelframe', font=('Segoe UI', 10, 'bold'), background=main_bg_color)
        style.configure('TLabelframe.Label', background=main_bg_color)
        style.configure('TButton', font=('Segoe UI', 10), padding=6)

        # Style for status labels
        style.configure('Success.TLabel', foreground=COLOR_SUCCESS)
        style.configure('Error.TLabel', foreground=COLOR_ERROR)
        style.configure('Warning.TLabel', foreground=COLOR_WARNING)
        style.configure('Neutral.TLabel', foreground=COLOR_NEUTRAL)

        main_frame = ttk.Frame(self.root, padding="15", style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title Label at the top with logo
        title_frame = ttk.Frame(main_frame, style='TFrame')
        title_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        # Add logo image if available
        if hasattr(self, 'logo_img'):
            logo_label = ttk.Label(title_frame, image=self.logo_img, background=main_bg_color)
            logo_label.pack(side=tk.LEFT, padx=(0, 10))

        # Title next to logo
        title_label = ttk.Label(title_frame, text="Attendance System", style='Header.TLabel')
        title_label.pack(side=tk.LEFT)

        # Left Panel: System Controls and Connection Tests
        controls_frame = ttk.Frame(main_frame, style='TFrame')
        controls_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        main_frame.columnconfigure(0, weight=1)

        # System Status & Start/Stop Controls
        status_controls = ttk.LabelFrame(controls_frame, text="System Controls", style='Section.TLabelframe',
                                         padding="10")
        status_controls.pack(fill=tk.X, pady=(0, 15))

        status_row = ttk.Frame(status_controls, style='TFrame')
        status_row.pack(fill=tk.X, pady=5)
        ttk.Label(status_row, text="Status:", font=('Segoe UI', 10, 'bold'), background=main_bg_color).pack(
            side=tk.LEFT)
        self.status_var = tk.StringVar(value="System stopped")
        self.status_label = ttk.Label(status_row, textvariable=self.status_var, style='Error.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=10)

        buttons_row = ttk.Frame(status_controls, style='TFrame')
        buttons_row.pack(fill=tk.X, pady=5)
        self.start_button = ttk.Button(buttons_row, text="▶ Start System", command=self.start_system)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(buttons_row, text="■ Stop System", command=self.stop_system, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Connection Tests Section - Redesigned for better visual feedback
        connection_frame = ttk.LabelFrame(controls_frame, text="Connection Tests", style='Section.TLabelframe',
                                          padding="10")
        connection_frame.pack(fill=tk.X, pady=(0, 15))

        # Status indicators with icons
        self.device_status_label = ttk.Label(connection_frame, textvariable=self.device_test_var,
                                             style='Neutral.TLabel')
        self.device_status_label.pack(anchor=tk.W, pady=5)

        self.api_status_label = ttk.Label(connection_frame, textvariable=self.api_test_var, style='Neutral.TLabel')
        self.api_status_label.pack(anchor=tk.W, pady=5)

        # Test button with visual feedback
        test_button_frame = ttk.Frame(connection_frame, style='TFrame')
        test_button_frame.pack(fill=tk.X, pady=5)
        self.test_button = ttk.Button(test_button_frame, text="Run Connection Tests",
                                      command=self.test_connections_with_feedback)
        self.test_button.pack(pady=5)

        # Results summary
        self.test_results_var = tk.StringVar(value="")
        self.test_results_label = ttk.Label(connection_frame, textvariable=self.test_results_var,
                                            background=main_bg_color)
        self.test_results_label.pack(anchor=tk.W, pady=5)

        # Right Panel: System Information
        info_frame = ttk.LabelFrame(main_frame, text="System Information", style='Section.TLabelframe', padding="10")
        info_frame.grid(row=1, column=1, sticky="nsew")
        main_frame.columnconfigure(1, weight=1)

        # Status variables with consistent formatting
        self.collector_status_var = tk.StringVar(value="● Collector: Stopped")
        self.collector_status_label = ttk.Label(info_frame, textvariable=self.collector_status_var,
                                                style='Error.TLabel')
        self.collector_status_label.pack(anchor=tk.W, pady=5)

        self.uploader_status_var = tk.StringVar(value="● Uploader: Stopped")
        self.uploader_status_label = ttk.Label(info_frame, textvariable=self.uploader_status_var, style='Error.TLabel')
        self.uploader_status_label.pack(anchor=tk.W, pady=5)

        self.user_importer_status_var = tk.StringVar(value="● User Importer: Stopped")
        self.user_importer_status_label = ttk.Label(info_frame, textvariable=self.user_importer_status_var,
                                                    style='Error.TLabel')
        self.user_importer_status_label.pack(anchor=tk.W, pady=5)

        # Information with timestamps
        ttk.Separator(info_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        self.last_collection_var = tk.StringVar(value="Last collection: Never")
        ttk.Label(info_frame, textvariable=self.last_collection_var, style='TLabel').pack(anchor=tk.W, pady=3)

        self.last_upload_var = tk.StringVar(value="Last upload: Never")
        ttk.Label(info_frame, textvariable=self.last_upload_var, style='TLabel').pack(anchor=tk.W, pady=3)

        self.last_import_var = tk.StringVar(value="Last user import: Never")
        ttk.Label(info_frame, textvariable=self.last_import_var, style='TLabel').pack(anchor=tk.W, pady=3)

        # Bottom Toolbar with Configure, Users, and Records buttons
        bottom_toolbar = ttk.Frame(main_frame, style='TFrame')
        bottom_toolbar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        ttk.Button(bottom_toolbar, text="⚙ Configure", command=self.open_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_toolbar, text="👥 Users", command=self.open_list_users).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_toolbar, text="📋 Records", command=self.open_list_records).pack(side=tk.LEFT, padx=5)

        # Initial status configuration based on configuration existence
        if self.db_manager.get_config():
            self.status_var.set("System ready to start")
            self.status_label.config(style='Warning.TLabel')
            # Automatically run connection tests on startup and start system if tests pass
            self.run_connection_tests()
            if self.connectivity_success:
                self.start_system()
        else:
            self.status_var.set("System not configured")
            self.status_label.config(style='Error.TLabel')
            self.start_button.config(state=tk.DISABLED)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.deiconify()
        self.root.mainloop()

    def test_connections_with_feedback(self):
        """Run connection tests with visual feedback during the process."""
        # Update button to show testing in progress
        self.test_button.config(text="Testing...", state=tk.DISABLED)
        self.test_results_var.set("Running connection tests...")
        self.test_results_label.config(style='Warning.TLabel')

        # Update device and API status to "Testing"
        self.update_status(self.device_test_var, "Device Connection", "Testing...", "warning")
        self.device_status_label.config(style='Warning.TLabel')
        self.update_status(self.api_test_var, "API Connection", "Testing...", "warning")
        self.api_status_label.config(style='Warning.TLabel')

        # Allow the UI to update before starting tests
        self.root.update_idletasks()

        # Run the actual tests
        result = self.run_connection_tests()

        # Update the results summary
        if result:
            self.test_results_var.set("✓ All connections successful")
            self.test_results_label.config(style='Success.TLabel')
            self.device_status_label.config(style='Success.TLabel')
            self.api_status_label.config(style='Success.TLabel')
        else:
            self.test_results_var.set("✗ Connection test failed")
            self.test_results_label.config(style='Error.TLabel')

            # Update individual label styles based on their values
            if "Connected" in self.device_test_var.get():
                self.device_status_label.config(style='Success.TLabel')
            else:
                self.device_status_label.config(style='Error.TLabel')

            if "Connected" in self.api_test_var.get():
                self.api_status_label.config(style='Success.TLabel')
            else:
                self.api_status_label.config(style='Error.TLabel')

        # Re-enable the test button
        self.test_button.config(state=tk.NORMAL)

        # Update start button state based on test results
        if result and self.db_manager.get_config():
            self.start_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.DISABLED)

    def load_logo(self):
        try:
            logo_img = tk.PhotoImage(file="assets/logo.png")
            logo_img = logo_img.subsample(20, 20)
            self.root.iconphoto(True, logo_img)
            self.logo_img = logo_img
        except Exception as e:
            self.logger.error(f"Failed to load logo: {e}")

    def show_config_interface(self):
        """Show the configuration interface."""
        config_interface = ConfigInterface(self.root, self.db_manager)
        config_interface.show()

    def start_collectors(self):
        """Start the attendance collectors in background threads."""
        self.config = self.db_manager.get_config()
        if not self.config:
            self.logger.error("No configuration found. Please configure the system first.")
            return False

        collection_interval = self.config.collection_interval
        upload_interval = self.config.upload_interval
        import_interval = self.config.import_interval

        # Start attendance collector
        self.collector_thread = threading.Thread(
            target=self.collector.start_scheduler,
            args=(self.users, collection_interval,),
            daemon=True
        )
        self.collector_thread.start()

        # Start API uploader
        self.uploader_thread = threading.Thread(
            target=self.uploader.start_scheduler,
            args=(upload_interval,),
            daemon=True
        )
        self.uploader_thread.start()

        # Start User Importer
        self.user_importer_thread = threading.Thread(
            target=self.user_importer.start_scheduler,
            args=(import_interval,),
            daemon=True
        )
        self.user_importer_thread.start()

        self.logger.info(f"Attendance collector started with interval of {collection_interval} minutes")
        self.logger.info(f"API uploader started with interval of {upload_interval} hours")
        self.logger.info(f"User Importer started with interval of {import_interval} hours")
        return True

    def stop_collectors(self):
        """Stop the attendance collectors."""
        if self.collector:
            self.collector.stop_scheduler()

        if self.uploader:
            self.uploader.stop_scheduler()

        if self.user_importer:
            self.user_importer.stop_scheduler()

        self.logger.info("Attendance collectors stopped")

    def start_system(self):
        """Start the attendance system with UI updates."""
        if not self.connectivity_success:
            messagebox.showerror("Connection Error",
                                 "Failed to start the system. Please check device and API connections.")
            return
        if self.start_collectors():
            # Update main status
            self.status_var.set("System running")
            self.status_label.config(style='Success.TLabel')

            # Update component statuses with consistent formatting
            self.collector_status_var.set("✓ Collector: Running")
            self.collector_status_label.config(style='Success.TLabel')

            self.uploader_status_var.set("✓ Uploader: Running")
            self.uploader_status_label.config(style='Success.TLabel')

            self.user_importer_status_var.set("✓ User Importer: Running")
            self.user_importer_status_label.config(style='Success.TLabel')

            # Update button states
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            # Show current time as start time
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.last_collection_var.set(f"Last collection: Scheduled")
            self.last_upload_var.set(f"Last upload: Scheduled")
            self.last_import_var.set(f"Last user import: Scheduled")
        else:
            messagebox.showerror("System Error", "Failed to start the system. Check logs for details.")

    def stop_system(self):
        """Stop the attendance system with UI updates."""
        self.stop_collectors()

        # Update main status
        self.status_var.set("System stopped")
        self.status_label.config(style='Error.TLabel')

        # Update component statuses with consistent formatting
        self.collector_status_var.set("✗ Collector: Stopped")
        self.collector_status_label.config(style='Error.TLabel')

        self.uploader_status_var.set("✗ Uploader: Stopped")
        self.uploader_status_label.config(style='Error.TLabel')

        self.user_importer_status_var.set("✗ User Importer: Stopped")
        self.user_importer_status_label.config(style='Error.TLabel')

        # Update button states
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def open_config(self):
        """Open the configuration window (ensuring styling consistency)."""
        config_interface = ConfigInterface(self.root, self.db_manager)
        orig_show = config_interface.show
        config_interface.show = lambda: None
        orig_show()

    def open_list_users(self):
        """Open the users window (ensuring styling consistency)."""
        users_interface = UsersInterface(self.root, self.users, self.db_manager)
        orig_show = users_interface.show
        users_interface.show = lambda: None
        orig_show()

    def open_list_records(self):
        """Open the records window (ensuring styling consistency)."""
        self.collector.collect_attendance(self.users)
        records_interface = RecordsInterface(self.root, self.users, self.db_manager)
        orig_show = records_interface.show
        records_interface.show = lambda: None
        orig_show()

    def on_close(self):
        """Handle window closing."""
        if messagebox.askokcancel("Quit", "Do you want to quit? This will stop the attendance collection."):
            self.stop_collectors()
            self.root.destroy()

    def run_cmd(self):
        """Run the application in command line mode."""
        parser = argparse.ArgumentParser(description='Attendance System')
        parser.add_argument('--config', action='store_true', help='Show configuration interface')
        parser.add_argument('--start', action='store_true', help='Start the collectors')
        parser.add_argument('--stop', action='store_true', help='Stop the collectors')
        args = parser.parse_args()

        if args.config:
            self.show_config_interface()
        elif args.start:
            if self.start_collectors():
                print("Attendance system started successfully")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("Stopping attendance system...")
                    self.stop_collectors()
            else:
                print("Failed to start the attendance system")
        elif args.stop:
            self.stop_collectors()
            print("Attendance system stopped")
        else:
            # Default to showing the control interface
            self.show_control_interface()


# Main entry point
if __name__ == "__main__":
    app = AttendanceSystemApp()
    app.run_cmd()