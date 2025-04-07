import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional

from src.database.db_manager import DatabaseManager
from src.device.attendance_processor import AttendanceProcessor
from src.scheduler.user_importer import UserImporter

logger = logging.getLogger(__name__)


class UsersInterface:
    def __init__(self, root: Optional[tk.Tk], users=None, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager()
        self.processor = None
        self.user_importer = UserImporter(self.db_manager)
        self.root = tk.Toplevel(root)
        self.users = users

        self.root.title("User List")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.status_var = tk.StringVar()

        # Create main layout frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        if not self.users:
            self.load_users()
        self.display_list()

    def show(self):
        self.root.grab_set()

    def initialize(self):
        """Initialize the attendance processor with config from the database."""
        config = self.db_manager.get_config()
        if not config:
            logger.error("No configuration found in database")
            return False

        self.processor = AttendanceProcessor(
            ip=config.device_ip,
            port=config.device_port
        )

        return self.processor.connect()

    def load_users(self):
        # Ensure the processor is initialized.
        if not self.processor:
            if not self.initialize():
                logger.error("Failed to initialize attendance processor")
                return

        try:
            # Retrieve users only from the attendance processor.
            users = self.processor.get_users()
            if not users:
                logger.info("No users found from attendance processor.")
                self.users = []
                return

            print("Loaded users from attendance processor:", users)
            self.users = users

        except Exception as e:
            self.handle_error("Error loading users from attendance processor", e)

    def import_users(self):
        try:
            imported = self.user_importer.import_users()
            self.show_success(f" {imported} users imported successfully")
            self.load_users()  # Reload the user list after import
            self.display_list()  # Refresh the display
        except Exception as e:
            self.handle_error("Error importing users", e)

    def display_list(self):
        # Clear previous widgets in the main frame if any
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Create a button frame for actions
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        # Add the Import Users button
        import_button = ttk.Button(button_frame, text="Import Users", command=self.import_users)
        import_button.pack(side=tk.LEFT, padx=(0, 10))

        # Title label for the user list section
        title_label = ttk.Label(self.main_frame, text="User List", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))

        # If no users are loaded, display a simple message.
        if not self.users or len(self.users) == 0:
            no_user_label = ttk.Label(self.main_frame, text="No users to display.", foreground="red")
            no_user_label.pack(pady=20)
        else:
            # Create a Treeview widget to display users in a table-like view.
            columns = ("id", "name")
            tree = ttk.Treeview(self.main_frame, columns=columns, show="headings", selectmode="browse")

            # Define headings for each column.
            tree.heading("id", text="ID")
            tree.heading("name", text="Name")

            # Optionally, set the width for each column.
            tree.column("id", width=50, anchor=tk.CENTER)
            tree.column("name", width=50, anchor=tk.W)

            # Insert user data into the Treeview.
            for user in self.users:
                user_id = user.get("id", "N/A") if isinstance(user, dict) else getattr(user, "user_id", "N/A")
                name = user.get("name", "N/A") if isinstance(user, dict) else getattr(user, "name", "N/A")
                tree.insert("", tk.END, values=(user_id, name))

            # Add a vertical scrollbar
            scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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