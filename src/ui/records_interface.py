import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
from typing import Optional, List

from src.database.db_manager import DatabaseManager
from src.database.models import AttendanceRecord
from src.scheduler.api_uploader import APIUploader

logger = logging.getLogger(__name__)


class RecordsInterface:
    """
    A GUI interface for displaying and managing attendance records from the database.
    """

    def __init__(self, root: Optional[tk.Tk], users=None, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the RecordsInterface.
        """
        self.db_manager = db_manager or DatabaseManager()
        self.uploader = APIUploader(self.db_manager)
        self.root = tk.Toplevel(root)
        self.users = users

        self.root.title("Attendance Records")
        self.root.geometry("1100x800")
        self.root.resizable(True, True)

        self.status_var = tk.StringVar()
        self.records: List[AttendanceRecord] = []

        # Filter variables
        self.filter_var = tk.StringVar(value="all")  # Default to showing all records
        self.sort_var = tk.StringVar(value="timestamp")  # Default sorting
        self.search_var = tk.StringVar()  # For search functionality

        # Create main layout frames
        self.create_layout()

        # Load records from the database and display them.
        self.load_records()
        self.display_records()

    def create_layout(self):
        """Create the main application layout with distinct sections"""
        # Main container
        self.container = ttk.Frame(self.root, padding="10")
        self.container.pack(fill=tk.BOTH, expand=True)

        # Header section
        self.header_frame = ttk.Frame(self.container)
        self.header_frame.pack(fill=tk.X, pady=(0, 10))

        # Control panel section (contains search and filters)
        self.control_panel = ttk.LabelFrame(self.container, text="Search & Filters")
        self.control_panel.pack(fill=tk.X, pady=(0, 10))

        # Records section
        self.records_frame = ttk.LabelFrame(self.container, text="Attendance Records")
        self.records_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Action buttons section
        self.action_frame = ttk.Frame(self.container)
        self.action_frame.pack(fill=tk.X, pady=(0, 10))

        # Status bar section
        self.status_frame = ttk.Frame(self.container)
        self.status_frame.pack(fill=tk.X)

        # Setup individual sections
        self.setup_header()
        self.setup_control_panel()
        self.setup_status_bar()
        self.setup_action_buttons()

    def setup_header(self):
        """Setup the header section"""
        title_label = ttk.Label(self.header_frame, text="Attendance Records", font=("Arial", 14, "bold"))
        title_label.pack(side=tk.LEFT, pady=5)

        # Record count label
        self.record_count_var = tk.StringVar(value="No records")
        count_label = ttk.Label(self.header_frame, textvariable=self.record_count_var)
        count_label.pack(side=tk.RIGHT, pady=5)

    def setup_control_panel(self):
        """Setup the search and filter controls"""
        # Create two frames side by side
        left_frame = ttk.Frame(self.control_panel)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        right_frame = ttk.Frame(self.control_panel)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Search controls in left frame
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="Search", command=self.apply_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Reset", command=self.reset_search).pack(side=tk.LEFT, padx=5)

        # Filter controls in right frame
        filter_frame = ttk.Frame(right_frame)
        filter_frame.pack(fill=tk.X, pady=5)

        # Filter radio buttons
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(filter_frame, text="All", variable=self.filter_var, value="all").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="Processed", variable=self.filter_var, value="processed").pack(side=tk.LEFT,
                                                                                                          padx=5)
        ttk.Radiobutton(filter_frame, text="Unprocessed", variable=self.filter_var, value="unprocessed").pack(
            side=tk.LEFT, padx=5)

        # Sort options
        sort_frame = ttk.Frame(right_frame)
        sort_frame.pack(fill=tk.X, pady=5)

        ttk.Label(sort_frame, text="Sort by:").pack(side=tk.LEFT, padx=(0, 10))
        sort_combo = ttk.Combobox(sort_frame, textvariable=self.sort_var, width=15,
                                  values=["timestamp", "username", "id", "punch_type"])
        sort_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(sort_frame, text="Apply Filter", command=self.apply_filter).pack(side=tk.LEFT, padx=(20, 0))

    def setup_status_bar(self):
        """Setup the status bar at the bottom"""
        status_label = ttk.Label(self.status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5, pady=5)

    def setup_action_buttons(self):
        """Setup the action buttons section"""
        # Left side - CRUD operations
        crud_frame = ttk.Frame(self.action_frame)
        crud_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(crud_frame, text="Add Record", command=self.add_record).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(crud_frame, text="Update Record", command=self.update_record).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(crud_frame, text="Delete Record", command=self.delete_record).pack(side=tk.LEFT, padx=5, pady=5)

        # Right side - Synchronize button
        sync_frame = ttk.Frame(self.action_frame)
        sync_frame.pack(side=tk.RIGHT, fill=tk.X)

        sync_btn = ttk.Button(sync_frame, text="SYNCHRONIZE", command=self.synchronize_records)
        sync_btn.pack(side=tk.RIGHT, padx=5, pady=5)

    def show(self):
        """Display the records window as a modal dialog."""
        self.root.grab_set()

    def reset_search(self):
        """Reset search field and reload records"""
        self.search_var.set("")
        self.apply_filter()

    def load_records(self):
        """
        Load attendance records from the database based on current filter.
        """
        try:
            filter_value = self.filter_var.get()
            order_by = self.sort_var.get()
            search_term = self.search_var.get()

            # Convert filter value to the appropriate parameter
            filter_processed = None  # Default to all records
            if filter_value == "processed":
                filter_processed = 1
            elif filter_value == "unprocessed":
                filter_processed = 0

            records = self.db_manager.get_attendance_records(filter_processed=filter_processed, order_by=order_by)

            # Apply search filter if provided
            if search_term:
                records = [r for r in records if search_term.lower() in str(r.username).lower() or
                           search_term.lower() in str(r.timestamp).lower()]

            if not records:
                logger.info(f"No {filter_value} attendance records found in the database.")
                self.records = []
                self.record_count_var.set("0 records found")
                return

            self.records = records  # Expecting a list of AttendanceRecord instances
            self.record_count_var.set(f"{len(records)} records found")
            logger.info(f"Loaded {len(records)} {filter_value} attendance records successfully.")

        except Exception as e:
            self.handle_error("Error loading attendance records", e)

    def display_records(self):
        """
        Display the attendance records in the main frame.
        """
        # Clear previous records display
        for widget in self.records_frame.winfo_children():
            widget.destroy()

        # Create a frame for the treeview and scrollbars
        tree_container = ttk.Frame(self.records_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create the Treeview
        columns = ("id", "username", "timestamp", "punch_type", "processed")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="browse")

        # Define headings
        self.tree.heading("id", text="ID", command=lambda: self.sort_treeview("id"))
        self.tree.heading("username", text="Employee Code", command=lambda: self.sort_treeview("username"))
        self.tree.heading("timestamp", text="Timestamp", command=lambda: self.sort_treeview("timestamp"))
        self.tree.heading("punch_type", text="Punch Type", command=lambda: self.sort_treeview("punch_type"))
        self.tree.heading("processed", text="Processed", command=lambda: self.sort_treeview("processed"))

        # Define columns
        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("username", width=150, anchor=tk.CENTER)
        self.tree.column("timestamp", width=220, anchor=tk.CENTER)
        self.tree.column("punch_type", width=100, anchor=tk.CENTER)
        self.tree.column("processed", width=100, anchor=tk.CENTER)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Insert records into the Treeview
        for record in self.records:
            processed_text = "Yes" if record.processed == 1 else "No"
            self.tree.insert("", tk.END, values=(
                record.id,
                record.username,
                record.timestamp if record.timestamp else "N/A",
                record.punch_type,
                processed_text
            ))

        # Add right-click menu
        self.create_context_menu()

    def create_context_menu(self):
        """Create a right-click context menu for the treeview"""
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Edit Record", command=self.update_record)
        self.context_menu.add_command(label="Delete Record", command=self.delete_record)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Mark as Processed", command=lambda: self.toggle_processed_status(True))
        self.context_menu.add_command(label="Mark as Unprocessed", command=lambda: self.toggle_processed_status(False))

        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show the context menu on right-click"""
        # Select row under mouse
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.context_menu.post(event.x_root, event.y_root)

    def toggle_processed_status(self, processed):
        """Toggle the processed status of a record"""
        selected_item = self.tree.selection()
        if not selected_item:
            self.show_error("Please select a record.")
            return

        record_values = self.tree.item(selected_item, "values")
        record_id = record_values[0]

        record = next((r for r in self.records if str(r.id) == str(record_id)), None)
        if not record:
            self.show_error("Record not found.")
            return

        try:
            record.processed = processed
            self.db_manager.update_attendance_record(record)
            status = "processed" if processed else "unprocessed"
            self.show_success(f"Record marked as {status} successfully.")
            self.load_records()
            self.display_records()
        except Exception as e:
            self.handle_error(f"Error updating record", e)

    def sort_treeview(self, column):
        """Set the sort column and refresh the display"""
        self.sort_var.set(column)
        self.apply_filter()

    def apply_filter(self):
        """Apply the selected filter and sort options"""
        self.load_records()
        self.display_records()

    def add_record(self):
        """
        Open a form to add a new attendance record.
        """
        form = tk.Toplevel(self.root)
        form.title("Add Attendance Record")
        form.transient(self.root)
        form.grab_set()

        # Create a frame with padding
        main_frame = ttk.Frame(form, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Add New Record", font=("Arial", 12))
        title_label.pack(pady=(0, 10))

        # Form fields in a grid layout
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.BOTH, padx=5, pady=5)

        fields = ("username", "timestamp", "punch_type", "processed")
        entries = {}

        # Create labeled form fields
        for idx, field in enumerate(fields):
            ttk.Label(form_frame, text=field.capitalize() + ":").grid(row=idx, column=0, sticky=tk.W, padx=5, pady=5)

            if field == "punch_type":
                var = tk.StringVar()
                entry = ttk.Combobox(form_frame, textvariable=var, values=["IN", "OUT"])
                entry.grid(row=idx, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
                entries[field] = var
            elif field == "processed":
                var = tk.StringVar(value="0")
                entry = ttk.Combobox(form_frame, textvariable=var, values=["0", "1"])
                entry.grid(row=idx, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
                entries[field] = var
            else:
                var = tk.StringVar()
                entry = ttk.Entry(form_frame, textvariable=var)
                entry.grid(row=idx, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
                entries[field] = var

        def submit():
            try:
                # Create a dictionary from form entries
                record_data = {field: entries[field].get() for field in fields}

                # Validate fields
                if not record_data['username'] or not record_data['timestamp']:
                    self.show_error("Username and timestamp are required fields.")
                    return

                # Optionally convert types as needed
                users_map = {user.name: user.user_id for user in self.users} if self.users else {}
                record_data['user_id'] = users_map.get(record_data['username'], "")
                record_data['processed'] = bool(int(record_data.get('processed', 0)))

                self.db_manager.save_attendance_record(record_data)
                self.show_success("Record added successfully.")
                form.destroy()
                self.load_records()
                self.display_records()
            except Exception as e:
                self.handle_error("Error adding record", e)

        # Button frame at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Cancel", command=form.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Submit", command=submit).pack(side=tk.RIGHT, padx=5)

    def update_record(self):
        """
        Update the selected attendance record.
        """
        selected_item = self.tree.selection()
        if not selected_item:
            self.show_error("Please select a record to update.")
            return

        # Get the selected record's values
        record_values = self.tree.item(selected_item, "values")
        record_id = record_values[0]

        # Retrieve the full record
        record = next((r for r in self.records if str(r.id) == str(record_id)), None)
        if not record:
            self.show_error("Record not found.")
            return

        form = tk.Toplevel(self.root)
        form.title("Update Attendance Record")
        form.transient(self.root)
        form.grab_set()

        # Create a frame with padding
        main_frame = ttk.Frame(form, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title with record ID
        title_label = ttk.Label(main_frame, text=f"Update Record #{record_id}", font=("Arial", 12))
        title_label.pack(pady=(0, 10))

        # Form fields in a grid layout
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.BOTH, padx=5, pady=5)

        fields = ("username", "timestamp", "status", "punch_type", "processed")
        entries = {}

        # Pre-populate form with current values
        initial_values = {
            "username": record.username,
            "timestamp": record.timestamp,
            "status": record.status if hasattr(record, "status") else "",
            "punch_type": record.punch_type,
            "processed": "1" if record.processed else "0"
        }

        # Create labeled form fields
        for idx, field in enumerate(fields):
            ttk.Label(form_frame, text=field.capitalize() + ":").grid(row=idx, column=0, sticky=tk.W, padx=5, pady=5)

            if field == "punch_type":
                var = tk.StringVar(value=initial_values[field])
                entry = ttk.Combobox(form_frame, textvariable=var, values=["IN", "OUT"])
                entry.grid(row=idx, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
                entries[field] = var
            elif field == "processed":
                var = tk.StringVar(value=initial_values[field])
                entry = ttk.Combobox(form_frame, textvariable=var, values=["0", "1"])
                entry.grid(row=idx, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
                entries[field] = var
            else:
                var = tk.StringVar(value=initial_values[field])
                entry = ttk.Entry(form_frame, textvariable=var)
                entry.grid(row=idx, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
                entries[field] = var

        def submit():
            try:
                # Update record with form values
                record.username = entries["username"].get()
                record.timestamp = entries["timestamp"].get()
                record.status = entries["status"].get()
                record.punch_type = entries["punch_type"].get()
                record.processed = bool(int(entries["processed"].get()))

                # Call update in the database
                self.db_manager.update_attendance_record(record)
                self.show_success("Record updated successfully.")
                form.destroy()
                self.load_records()
                self.display_records()
            except Exception as e:
                self.handle_error("Error updating record", e)

        # Button frame at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Cancel", command=form.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Changes", command=submit).pack(side=tk.RIGHT, padx=5)

    def delete_record(self):
        """
        Delete the selected attendance record.
        """
        selected_item = self.tree.selection()
        if not selected_item:
            self.show_error("Please select a record to delete.")
            return

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete",
                                   "Are you sure you want to delete the selected record?",
                                   parent=self.root):
            return

        record_values = self.tree.item(selected_item, "values")
        record_id = record_values[0]

        record = next((r for r in self.records if str(r.id) == str(record_id)), None)
        if not record:
            self.show_error("Record not found.")
            return

        try:
            self.db_manager.delete_attendance_record(record)
            self.show_success("Record deleted successfully.")
            self.load_records()
            self.display_records()
        except Exception as e:
            self.handle_error("Error deleting record", e)

    def synchronize_records(self):
        """
        Call the uploader to synchronize attendance records.
        """
        try:
            # Show synchronizing status
            self.status_var.set("Synchronizing records...")
            self.root.update()

            # Perform synchronization
            self.uploader.upload_data()

            # Refresh display
            self.load_records()
            self.display_records()

            # Update status
            self.status_var.set("Records synchronized successfully.")
            logger.info("Records synchronized successfully.")
        except Exception as e:
            self.handle_error("Error synchronizing records", e)

    def show_error(self, message: str):
        """
        Display an error message to the user.
        """
        self.status_var.set(message)
        messagebox.showerror("Error", message, parent=self.root)

    def show_success(self, message: str):
        """
        Display a success message to the user.
        """
        self.status_var.set(message)
        messagebox.showinfo("Success", message, parent=self.root)

    def handle_error(self, message: str, exception: Exception):
        """
        Log and display an error message.
        """
        error_msg = f"{message}: {exception}"
        logger.error(error_msg)
        self.show_error(error_msg)