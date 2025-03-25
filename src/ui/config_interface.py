import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading
from typing import Optional, Dict, Any, Union, Callable

from src.database.db_manager import DatabaseManager
from src.database.models import Config
from src.device.attendance_processor import AttendanceProcessor
from src.api.api_client import APIClient
from config.config import API_URL

logger = logging.getLogger(__name__)


class ConfigInterface:
    """Interface for configuring the attendance system."""

    def __init__(self, root: Optional[tk.Tk], db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the configuration interface.

        Args:
            db_manager: Database manager instance, creates a new one if None
            root: Tkinter root window, creates a new one if None
        """
        self.db_manager = db_manager or DatabaseManager()
        self.is_main = root is None

        self.root = tk.Toplevel(root)


        self.root.title("Attendance System Configuration")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.status_var = tk.StringVar()
        # Initialize all UI-related variables
        self.company_id_var = tk.StringVar()
        self.api_username_var = tk.StringVar()
        self.api_password_var = tk.StringVar()
        self.device_ip_var = tk.StringVar()
        self.device_port_var = tk.IntVar(value=4370)
        self.collection_interval_var = tk.IntVar(value=60)
        self.upload_interval_var = tk.IntVar(value=1)

        # Create main layout frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_form()
        self.load_config()

    def setup_ui_variables(self):
        """Initialize all UI variables."""
        # These will be fully initialized in create_form
        self.company_id_var = None
        self.api_username_var = None
        self.api_password_var = None
        self.device_ip_var = None
        self.device_port_var = None
        self.collection_interval_var = None
        self.upload_interval_var = None

    def show(self):
        """Display the configuration interface."""
        if self.is_main:
            self.root.mainloop()
        else:
            # For Toplevel windows, make it modal
            self.root.grab_set()

    def create_form(self):
        """Create and arrange the form components."""
        # API Configuration Section
        self.create_section_label("API Configuration", 0)
        self.company_id_var = self.create_entry("Company ID:", 1)
        self.api_username_var = self.create_entry("API Username:", 2)
        self.api_password_var = self.create_entry("API Password:", 3, show="*")

        # Device Configuration Section
        self.create_section_label("Device Configuration", 5)
        self.device_ip_var = self.create_entry("Device IP:", 6)
        self.device_port_var = self.create_entry("Device Port:", 7, 4370, is_int=True)

        # Scheduler Configuration Section
        self.create_section_label("Scheduler Configuration", 9)
        self.collection_interval_var = self.create_entry("Collection Interval (minutes):", 10, 60, is_int=True)
        self.upload_interval_var = self.create_entry("Upload Interval (hours):", 11, 1, is_int=True)

        # Button Panel
        self.create_button_panel(13)

        # Status Label
        status_label = ttk.Label(self.main_frame, textvariable=self.status_var, wraplength=450)
        status_label.grid(column=0, row=14, columnspan=2, sticky=tk.W, pady=10)

    def create_button_panel(self, row: int):
        """Create the panel with action buttons.

        Args:
            row: The grid row to place the button panel
        """
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(column=0, row=row, columnspan=2, pady=20)

        buttons = [
            ("Load Existing Config", self.load_config),
            ("Test Device", self.test_device_connection),
            ("Test API", self.test_api_connection),
            ("Save Configuration", self.save_config)
        ]

        for text, command in buttons:
            ttk.Button(button_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)

    def create_section_label(self, text: str, row: int):
        """Create a section header label.

        Args:
            text: The section title text
            row: The grid row to place the label
        """
        ttk.Label(
            self.main_frame,
            text=text,
            font=("Arial", 12, "bold")
        ).grid(column=0, row=row, columnspan=2, sticky=tk.W, pady=(20, 10))

    def create_entry(self, label_text: str, row: int, default: Union[str, int] = "",
                     is_int: bool = False, show: Optional[str] = None) -> Union[tk.StringVar, tk.IntVar]:
        """Create a labeled input entry.

        Args:
            label_text: The label text for the entry
            row: The grid row to place the entry
            default: Default value for the entry
            is_int: Whether the entry should contain an integer value
            show: Character to show instead of actual input (for passwords)

        Returns:
            The variable bound to the entry
        """
        ttk.Label(self.main_frame, text=label_text).grid(column=0, row=row, sticky=tk.W, pady=5)

        # Convert default value to appropriate type
        default_value = int(default) if is_int else str(default)

        # Create the appropriate variable type with proper default value
        var = tk.IntVar(value=default_value) if is_int else tk.StringVar(value=default_value)

        entry = ttk.Entry(self.main_frame, textvariable=var, width=40, show=show)
        entry.grid(column=1, row=row, sticky=tk.W, pady=5)

        # Ensure the entry shows the default value initially
        if is_int:
            var.set(default_value)
        else:
            var.set(default_value)

        return var

    def get_config_dict(self) -> Config:
        return Config(
            company_id=self.company_id_var.get(),
            api_username=self.api_username_var.get(),
            api_password=self.api_password_var.get(),
            device_ip=self.device_ip_var.get(),
            device_port=int(self.device_port_var.get()),
            collection_interval=int(self.collection_interval_var.get()),
            upload_interval=int(self.upload_interval_var.get())
        )

    def load_config(self):
        try:
            config = self.db_manager.get_config()
            if not config:
                self.status_var.set("No existing configuration found. Please enter configuration details.")
                logger.info("No configuration found in database.")
                return

            # For debugging
            print("Loaded config:", config.__dict__)

            self.company_id_var.set(config.company_id)
            self.api_username_var.set(config.api_username)
            self.api_password_var.set(config.api_password)
            self.device_ip_var.set(config.device_ip)

            self.device_port_var.set(int(config.device_port) if config.device_port is not None else 4370)
            self.collection_interval_var.set(
                int(config.collection_interval) if config.collection_interval is not None else 60)
            self.upload_interval_var.set(int(config.upload_interval) if config.upload_interval is not None else 1)

            self.root.update_idletasks()
            self.root.update()
            # Ensure UI reflects changes
            self.status_var.set("Configuration loaded successfully.")
            logger.info("Configuration loaded from database.")
        except Exception as e:
            self.handle_error("Error loading configuration", e)

    def validate_config(self) -> bool:
        """Validate the configuration data.

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.company_id_var.get() or not self.device_ip_var.get():
            self.show_validation_error("Company ID and Device IP are required fields.")
            return False
        return True

    def save_config(self):
        """Save configuration to database."""
        try:
            if not self.validate_config():
                return

            self.db_manager.save_config(self.get_config_dict())
            self.show_success("Configuration saved successfully.")

        except Exception as e:
            self.handle_error("Error saving configuration", e)

    def test_device_connection(self):
        """Test connection to the device asynchronously."""
        self.status_var.set("Testing device connection...")
        self.run_async(self.device_connection_logic)

    def test_api_connection(self):
        """Test API connection asynchronously."""
        self.status_var.set("Testing API connection...")
        self.run_async(self.api_connection_logic)

    def device_connection_logic(self):
        """Logic to test device connection."""
        try:
            processor = AttendanceProcessor(
                ip=self.device_ip_var.get(),
                port=self.device_port_var.get()
            )

            if not processor.connect():
                self.show_error(
                    f"Could not connect to device at {self.device_ip_var.get()}:{self.device_port_var.get()}"
                )
                return

            attendance_records = processor.get_attendance() or []
            count = len(attendance_records)
            processor.disconnect()
            self.show_success(f"Device connected. Found {count} attendance records.")

        except Exception as e:
            self.handle_error("Error testing device connection", e)

    def api_connection_logic(self):
        """Logic to test API connection."""
        try:
            api_client = APIClient(
                api_url=API_URL,
                company_id=self.company_id_var.get(),
                username=self.api_username_var.get(),
                password=self.api_password_var.get()
            )

            if api_client.authenticate():
                self.show_success(f"Authenticated with API at {API_URL}")
            else:
                self.show_error(f"Failed to authenticate with API at {API_URL}")

        except Exception as e:
            self.handle_error("Error testing API connection", e)

    def run_async(self, target: Callable):
        """Run a task asynchronously to prevent UI freezing.

        Args:
            target: Function to run in a separate thread
        """
        threading.Thread(target=target, daemon=True).start()

    def show_validation_error(self, message: str):
        """Show a validation error message.

        Args:
            message: Error message to display
        """
        messagebox.showerror("Validation Error", message)

    def show_error(self, message: str):
        """Show an error message.

        Args:
            message: Error message to display
        """
        self.status_var.set(message)
        messagebox.showerror("Error", message, parent=self.root)

    def show_success(self, message: str):
        """Show a success message.

        Args:
            message: Success message to display
        """
        self.status_var.set(message)
        messagebox.showinfo("Success", message, parent=self.root)

    def handle_error(self, message: str, exception: Exception):
        """Log and display errors.

        Args:
            message: Error context message
            exception: The exception that occurred
        """
        error_msg = f"{message}: {exception}"
        self.show_error(error_msg)
        logger.error(error_msg)