import os
import sys
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import argparse
from datetime import datetime

from src.database.db_manager import DatabaseManager
from src.ui.config_interface import ConfigInterface
from src.scheduler.attendance_collector import AttendanceCollector
from src.scheduler.api_uploader import APIUploader


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


# Main application class
class AttendanceSystemApp:
    def __init__(self):
        """Initialize the main application."""
        self.logger = setup_logging()
        self.db_manager = DatabaseManager()
        self.collector_thread = None
        self.uploader_thread = None
        self.collector = None
        self.uploader = None
        self.root = tk.Tk()
        self.root.withdraw()

        self.logger.info("Attendance System initializing")

    def show_config_interface(self):
        """Show the configuration interface."""
        config_interface = ConfigInterface(self.root, self.db_manager)
        config_interface.show()

    def start_collectors(self):
        """Start the attendance collectors in background threads."""
        config = self.db_manager.get_config()
        if not config:
            self.logger.error("No configuration found. Please configure the system first.")
            return False

        collection_interval = config.collection_interval
        upload_interval = config.upload_interval

        # Start attendance collector
        self.collector = AttendanceCollector(self.db_manager)
        self.collector_thread = threading.Thread(
            target=self.collector.start_scheduler,
            args=(collection_interval,),
            daemon=True
        )
        self.collector_thread.start()

        # Start API uploader
        self.uploader = APIUploader(self.db_manager)
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

    def show_control_interface(self):
        """Show the control interface for managing the collectors."""
        self.root.title("Attendance System Control Panel")
        self.root.geometry("400x300")

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status section
        ttk.Label(main_frame, text="System Status", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        self.status_var = tk.StringVar(value="System stopped")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(anchor=tk.W, pady=(0, 20))

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.start_button = ttk.Button(button_frame, text="Start System", command=self.start_system)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop System", command=self.stop_system, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Configure", command=self.open_config).pack(side=tk.LEFT, padx=5)

        # System info section
        info_frame = ttk.LabelFrame(main_frame, text="System Information")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.collector_status_var = tk.StringVar(value="Collector: Stopped")
        ttk.Label(info_frame, textvariable=self.collector_status_var).pack(anchor=tk.W, pady=2)

        self.uploader_status_var = tk.StringVar(value="Uploader: Stopped")
        ttk.Label(info_frame, textvariable=self.uploader_status_var).pack(anchor=tk.W, pady=2)

        self.last_collection_var = tk.StringVar(value="Last collection: Never")
        ttk.Label(info_frame, textvariable=self.last_collection_var).pack(anchor=tk.W, pady=2)

        self.last_upload_var = tk.StringVar(value="Last upload: Never")
        ttk.Label(info_frame, textvariable=self.last_upload_var).pack(anchor=tk.W, pady=2)

        # Check for config and update UI accordingly
        if self.db_manager.get_config():
            self.status_var.set("System ready to start")
        else:
            self.status_var.set("System not configured")
            self.start_button.config(state=tk.DISABLED)

        # Set up clean exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start UI
        self.root.deiconify()
        self.root.mainloop()

    def start_system(self):
        """Start the attendance system."""
        if self.start_collectors():
            self.status_var.set("System running")
            self.collector_status_var.set("Collector: Running")
            self.uploader_status_var.set("Uploader: Running")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Error", "Failed to start the system. Check logs for details.")

    def stop_system(self):
        """Stop the attendance system."""
        self.stop_collectors()
        self.status_var.set("System stopped")
        self.collector_status_var.set("Collector: Stopped")
        self.uploader_status_var.set("Uploader: Stopped")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def open_config(self):
        """Open the configuration window."""
        # Create a new window for configuration

        config_interface = ConfigInterface(self.root, self.db_manager)

        # Override the show method to reuse the existing window
        orig_show = config_interface.show
        config_interface.show = lambda: None
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
                # Keep the main thread alive
                try:
                    while True:
                        # Sleep to prevent CPU hogging
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