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

        # Configure window properties
        self.root.title("User Management")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        self.root.resizable(True, True)

        # Status variable for displaying messages
        self.status_var = tk.StringVar()

        # Create and configure the main layout
        self.setup_ui()

        # Load data if not provided
        if not self.users:
            self.load_users()

        # Populate the user list
        self.refresh_user_list()

    def setup_ui(self):
        """Create and configure all UI elements"""
        # Main container with padding
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Header section
        self.create_header_section()

        # User list section with frame
        self.create_user_list_section()

        # Status bar at the bottom
        self.create_status_bar()

    def create_header_section(self):
        """Create the header section with title and action buttons"""
        # Header frame
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        # Title
        title_label = ttk.Label(header_frame, text="User Management", font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)

        # Action buttons frame (right-aligned)
        action_frame = ttk.Frame(header_frame)
        action_frame.pack(side=tk.RIGHT)

        # Import button with icon indicator
        self.import_button = ttk.Button(
            action_frame,
            text="Import Users",
            command=self.import_users,
            style="Action.TButton"
        )
        self.import_button.pack(side=tk.RIGHT, padx=5)

        # Refresh button
        refresh_button = ttk.Button(
            action_frame,
            text="Refresh List",
            command=self.refresh_data
        )
        refresh_button.pack(side=tk.RIGHT, padx=5)

    def create_user_list_section(self):
        """Create the user list section with a frame and treeview"""
        # Container frame for user list
        self.list_container = ttk.LabelFrame(self.main_frame, text="User List")
        self.list_container.pack(fill=tk.BOTH, expand=True, pady=10)

        # Create Treeview with scrollbars
        self.create_user_treeview()

    def create_user_treeview(self):
        """Create and configure the treeview for displaying users"""
        # Frame to contain treeview and scrollbars
        tree_frame = ttk.Frame(self.list_container)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Define columns
        columns = ("id", "name")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        # Configure column headings
        self.tree.heading("id", text="User ID")
        self.tree.heading("name", text="Employee Code")

        # Configure column widths and alignment
        self.tree.column("id", width=100, anchor=tk.CENTER)
        self.tree.column("name", width=300, anchor=tk.W)

        # Add vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        # Add horizontal scrollbar
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscroll=hsb.set)

        # Position scrollbars and treeview using grid
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Configure grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Double-click event (optional for future user detail view)
        self.tree.bind("<Double-1>", self.on_user_double_click)

    def create_status_bar(self):
        """Create status bar at the bottom of the window"""
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        # Status label with status_var
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)

        # Default status message
        self.status_var.set("Ready")

    def show(self):
        """Make the window visible and set focus"""
        self.root.grab_set()  # Make this window modal
        self.root.focus_set()  # Set keyboard focus

    def initialize(self):
        """Initialize the attendance processor with config from the database."""
        # Set status message
        self.status_var.set("Initializing connection...")
        self.root.update()  # Force UI update

        config = self.db_manager.get_config()
        if not config:
            logger.error("No configuration found in database")
            self.status_var.set("Error: No configuration found")
            return False

        self.processor = AttendanceProcessor(
            ip=config.device_ip,
            port=config.device_port
        )

        success = self.processor.connect()
        if success:
            self.status_var.set("Connection established")
        else:
            self.status_var.set("Connection failed")

        return success

    def load_users(self):
        """Load users from the attendance processor"""
        # Ensure the processor is initialized
        if not self.processor:
            if not self.initialize():
                logger.error("Failed to initialize attendance processor")
                return

        try:
            # Update status
            self.status_var.set("Loading users...")
            self.root.update()  # Force UI update

            # Retrieve users from the attendance processor
            users = self.processor.get_users()
            if not users:
                logger.info("No users found from attendance processor.")
                self.users = []
                self.status_var.set("No users found")
                return

            logger.info(f"Loaded {len(users)} users from attendance processor")
            self.users = users
            self.status_var.set(f"{len(users)} users loaded")

        except Exception as e:
            self.handle_error("Error loading users from attendance processor", e)

    def refresh_data(self):
        """Refresh the user data and update the display"""
        self.load_users()
        self.refresh_user_list()

    def import_users(self):
        """Import users using the UserImporter and refresh the display"""
        try:
            self.status_var.set("Importing users...")
            self.root.update()  # Force UI update

            imported = self.user_importer.import_users()
            self.show_success(f"{imported} users imported successfully")
            self.load_users()  # Reload the user list after import
            self.refresh_user_list()  # Refresh the display
        except Exception as e:
            self.handle_error("Error importing users", e)

    def refresh_user_list(self):
        """Update the treeview with current user data"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # If no users, display a message in the status bar
        if not self.users or len(self.users) == 0:
            self.status_var.set("No users to display")
            return

        # Insert user data into the treeview
        for user in self.users:
            user_id = user.get("id", "N/A") if isinstance(user, dict) else getattr(user, "user_id", "N/A")
            name = user.get("name", "N/A") if isinstance(user, dict) else getattr(user, "name", "N/A")
            self.tree.insert("", tk.END, values=(user_id, name))

        # Update status message
        self.status_var.set(f"Displaying {len(self.users)} users")

    def on_user_double_click(self, event):
        """Handle double-click on a user row (placeholder for future functionality)"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            values = self.tree.item(item, "values")
            user_id = values[0]
            # Placeholder for future user detail view
            self.status_var.set(f"Selected user ID: {user_id}")

    def show_error(self, message: str):
        """Show an error message dialog and update status bar"""
        self.status_var.set(f"Error: {message}")
        messagebox.showerror("Error", message, parent=self.root)

    def show_success(self, message: str):
        """Show a success message dialog and update status bar"""
        self.status_var.set(message)
        messagebox.showinfo("Success", message, parent=self.root)

    def handle_error(self, message: str, exception: Exception):
        """Log and display errors with context"""
        error_msg = f"{message}: {exception}"
        logger.error(error_msg)
        self.show_error(error_msg)