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
from src.ui.config_interface import ConfigInterface
from src.scheduler.attendance_collector import AttendanceCollector
from src.scheduler.api_uploader import APIUploader
from src.ui.records_interface import RecordsInterface
from src.ui.users_interface import UsersInterface


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
        self.collector = AttendanceCollector(self.db_manager)
        self.uploader = APIUploader(self.db_manager)
        self.root = tk.Tk()
        self.root.withdraw()

        # UI instance variables for status labels
        self.status_label = None
        self.collector_status_label = None
        self.uploader_status_label = None

        # Test status variables
        self.device_test_var = tk.StringVar(value="Device: Not Tested")
        self.api_test_var = tk.StringVar(value="API: Not Tested")
        self.logger.info("Attendance System initializing")

    def run_connection_tests(self):
        """Run device and API connection tests and return True if both pass."""
        success = True
        try:
            # Get configuration
            self.config = self.db_manager.get_config()
            if not self.config:
                self.logger.error("No configuration found. Skipping connection tests.")
                self.device_test_var.set("Device: Test Skipped (No Config)")
                self.api_test_var.set("API: Test Skipped (No Config)")
                return False

            # Test device connection
            try:
                processor = AttendanceProcessor(
                    ip=self.config.device_ip,
                    port=self.config.device_port
                )

                if processor.connect():
                    users = processor.get_users() or []
                    count = len(users)
                    self.users = users
                    processor.disconnect()
                    self.device_test_var.set(f"Device: Connected (Users: {count})")
                    self.logger.info(f"Device connection successful. Found {count} users.")
                else:
                    self.device_test_var.set("Device: Connection Failed")
                    self.logger.warning("Device connection test failed.")
                    success = False
            except Exception as e:
                self.device_test_var.set("Device: Test Error")
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
                    self.api_test_var.set("API: Authentication Successful")
                    self.logger.info("API authentication successful.")
                else:
                    self.api_test_var.set("API: Authentication Failed")
                    self.logger.warning("API authentication test failed.")
                    success = False
            except Exception as e:
                self.api_test_var.set("API: Test Error")
                self.logger.error(f"API connection test error: {e}")
                success = False

        except Exception as e:
            self.logger.error(f"Unexpected error in connection tests: {e}")
            self.device_test_var.set("Device: Test Error")
            self.api_test_var.set("API: Test Error")
            success = False

        return success

    def show_control_interface(self):
        """Show the modernized control interface for managing the collectors."""
        # Set up the window
        self.root.title("Attendance System Control Panel")
        self.root.geometry("750x600")
        self.root.minsize(500, 400)
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Arial', 10), padding=10)
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TFrame', background='lightgray')

        main_frame = ttk.Frame(self.root, padding="20", style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Attendance System", font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)

        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=10)
        ttk.Label(status_frame, text="Status:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="System stopped")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=10)

        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        self.start_button = ttk.Button(button_frame, text="Start System", command=self.start_system)
        self.start_button.pack(side=tk.LEFT, padx=10)
        self.stop_button = ttk.Button(button_frame, text="Stop System", command=self.stop_system, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Configure", command=self.open_config).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Users", command=self.open_list_users).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Records", command=self.open_list_records).pack(side=tk.LEFT, padx=10)

        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)

        test_frame = ttk.LabelFrame(main_frame, text="Connection Tests", padding="10")
        test_frame.pack(fill=tk.X, pady=10)
        device_test_label = ttk.Label(test_frame, textvariable=self.device_test_var)
        device_test_label.pack(anchor=tk.W, pady=2)
        api_test_label = ttk.Label(test_frame, textvariable=self.api_test_var)
        api_test_label.pack(anchor=tk.W, pady=2)
        ttk.Button(test_frame, text="Run Connection Tests", command=self.run_connection_tests).pack(side=tk.LEFT,
                                                                                                    padx=10, pady=5)

        info_frame = ttk.LabelFrame(main_frame, text="System Information", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.collector_status_var = tk.StringVar(value="Collector: Stopped")
        self.collector_status_label = ttk.Label(info_frame, textvariable=self.collector_status_var)
        self.collector_status_label.pack(anchor=tk.W, pady=2)
        self.uploader_status_var = tk.StringVar(value="Uploader: Stopped")
        self.uploader_status_label = ttk.Label(info_frame, textvariable=self.uploader_status_var)
        self.uploader_status_label.pack(anchor=tk.W, pady=2)
        self.last_collection_var = tk.StringVar(value="Last collection: Never")
        ttk.Label(info_frame, textvariable=self.last_collection_var).pack(anchor=tk.W, pady=2)
        self.last_upload_var = tk.StringVar(value="Last upload: Never")
        ttk.Label(info_frame, textvariable=self.last_upload_var).pack(anchor=tk.W, pady=2)

        # Initial status configuration
        if self.db_manager.get_config():
            self.status_var.set("System ready to start")
            self.status_label.config(foreground='red')
            # Automatically run connection tests on startup
            if self.run_connection_tests():
                self.start_system()
        else:
            self.status_var.set("System not configured")
            self.status_label.config(foreground='red')
            self.start_button.config(state=tk.DISABLED)

        self.collector_status_label.config(foreground='red')
        self.uploader_status_label.config(foreground='red')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.deiconify()
        self.root.mainloop()

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

        self.logger.info(f"Attendance collector started with interval of {collection_interval} minutes")
        self.logger.info(f"API uploader started with interval of {upload_interval} hours")
        return True

    def stop_collectors(self):
        """Stop the attendance collectors."""
        if self.collector:
            self.collector.stop_scheduler()

        if self.uploader:
            self.uploader.stop_scheduler()

        self.logger.info("Attendance collectors stopped")

    def start_system(self):
        """Start the attendance system with UI updates."""
        if self.start_collectors():
            self.status_var.set("System running")
            self.status_label.config(foreground='green')  # Running
            self.collector_status_var.set("Collector: Running")
            self.collector_status_label.config(foreground='green')  # Running
            self.uploader_status_var.set("Uploader: Running")
            self.uploader_status_label.config(foreground='green')  # Running
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Error", "Failed to start the system. Check logs for details.")

    def stop_system(self):
        """Stop the attendance system with UI updates."""
        self.stop_collectors()
        self.status_var.set("System stopped")
        self.status_label.config(foreground='red')  # Stopped
        self.collector_status_var.set("Collector: Stopped")
        self.collector_status_label.config(foreground='red')  # Stopped
        self.uploader_status_var.set("Uploader: Stopped")
        self.uploader_status_label.config(foreground='red')  # Stopped
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def open_config(self):
        """Open the configuration window (unchanged logic, ensure styling consistency)."""
        config_interface = ConfigInterface(self.root, self.db_manager)
        orig_show = config_interface.show
        config_interface.show = lambda: None
        orig_show()

    def open_list_users(self):
        """Open the users window (unchanged logic, ensure styling consistency)."""
        users_interface = UsersInterface(self.root, self.users, self.db_manager)
        orig_show = users_interface.show
        users_interface.show = lambda: None
        orig_show()

    def open_list_records(self):
        """Open the records window (unchanged logic, ensure styling consistency)."""
        self.collector.collect_attendance(self.users)
        records_interface = RecordsInterface(self.root, self.users, self.db_manager)
        orig_show = records_interface.show
        records_interface.show = lambda: None
        orig_show()

    def on_close(self):
        """Handle window closing (unchanged)."""
        if messagebox.askokcancel("Quit", "Do you want to quit? This will stop the attendance collection."):
            self.stop_collectors()
            self.root.destroy()

    def run_cmd(self):
        """Run the application in command line mode (unchanged)."""
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