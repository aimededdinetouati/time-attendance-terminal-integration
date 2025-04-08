import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
from typing import Optional, List

from src.database.db_manager import DatabaseManager
from src.database.models import AttendanceRecord
from src.device.attendance_processor import AttendanceProcessor
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
        self.root.geometry("1000x800")
        self.root.resizable(True, True)

        self.status_var = tk.StringVar()
        self.records: List[AttendanceRecord] = []

        # Filter variables
        self.filter_var = tk.StringVar(value="all")  # Default to showing all records
        self.sort_var = tk.StringVar(value="timestamp")  # Default sorting

        # Create main layout frame.
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Load records from the database and display them.
        self.load_records()
        self.display_records()

    def show(self):
        """Display the records window as a modal dialog."""
        self.root.grab_set()

    def load_records(self):
        """
        Load attendance records from the database based on current filter.
        """
        try:
            filter_value = self.filter_var.get()
            order_by = self.sort_var.get()

            # Convert filter value to the appropriate parameter
            filter_processed = None  # Default to all records
            if filter_value == "processed":
                filter_processed = 1
            elif filter_value == "unprocessed":
                filter_processed = 0

            records = self.db_manager.get_attendance_records(filter_processed=filter_processed, order_by=order_by)
            if not records:
                logger.info(f"No {filter_value} attendance records found in the database.")
                self.records = []
                return

            self.records = records  # Expecting a list of AttendanceRecord instances
            logger.info(f"Loaded {len(records)} {filter_value} attendance records successfully.")

        except Exception as e:
            self.handle_error("Error loading attendance records", e)

    def display_records(self):
        """
        Display the attendance records in the main frame.
        """
        # Clear previous widgets.
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        title_label = ttk.Label(self.main_frame, text="Attendance Records", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))

        # Add filter controls
        filter_frame = ttk.Frame(self.main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # Filter radio buttons
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(filter_frame, text="All", variable=self.filter_var, value="all").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="Processed", variable=self.filter_var, value="processed").pack(side=tk.LEFT,
                                                                                                          padx=5)
        ttk.Radiobutton(filter_frame, text="Unprocessed", variable=self.filter_var, value="unprocessed").pack(
            side=tk.LEFT, padx=5)

        # Sort options
        ttk.Label(filter_frame, text="Sort by:").pack(side=tk.LEFT, padx=(20, 10))
        sort_combo = ttk.Combobox(filter_frame, textvariable=self.sort_var,
                                  values=["timestamp", "username", "id", "punch_type"])
        sort_combo.pack(side=tk.LEFT, padx=5)

        # Apply button
        apply_btn = ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filter)
        apply_btn.pack(side=tk.LEFT, padx=(20, 0))

        # Create the Treeview.
        columns = ("id", "username", "timestamp", "punch_type", "processed")
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show="headings", selectmode="browse")

        # Define headings.
        self.tree.heading("id", text="ID")
        self.tree.heading("username", text="Employee Code")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("punch_type", text="Punch Type")
        self.tree.heading("processed", text="Processed")

        # Define columns.
        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("username", width=150, anchor=tk.CENTER)
        self.tree.column("timestamp", width=220, anchor=tk.CENTER)
        self.tree.column("punch_type", width=100, anchor=tk.CENTER)
        self.tree.column("processed", width=100, anchor=tk.CENTER)

        # Insert records into the Treeview.
        for record in self.records:
            processed_text = "Yes" if record.processed == 1 else "No"
            self.tree.insert("", tk.END, values=(
                record.id,
                record.username,
                record.timestamp if record.timestamp else "N/A",
                record.punch_type,
                processed_text
            ))

        # Add record count label
        count_label = ttk.Label(self.main_frame, text=f"Showing {len(self.records)} records")
        count_label.pack(anchor=tk.W, padx=10, pady=(5, 0))

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add vertical scrollbar.
        scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add CRUD buttons.
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        add_btn = ttk.Button(btn_frame, text="Add Record", command=self.add_record)
        add_btn.pack(side=tk.LEFT, padx=5)

        update_btn = ttk.Button(btn_frame, text="Update Record", command=self.update_record)
        update_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(btn_frame, text="Delete Record", command=self.delete_record)
        delete_btn.pack(side=tk.LEFT, padx=5)

        # SYNCHRONIZE button remains at the bottom.
        sync_btn = ttk.Button(self.main_frame, text="SYNCHRONIZE", command=self.synchronize_records)
        sync_btn.pack(side=tk.BOTTOM, pady=10)

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

        fields = ("username", "timestamp", "punch_type", "processed")
        entries = {}

        for idx, field in enumerate(fields):
            ttk.Label(form, text=field.capitalize() + ":").grid(row=idx, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(form)
            entry.grid(row=idx, column=1, padx=5, pady=5)
            entries[field] = entry

        def submit():
            try:
                # Create a dictionary from form entries.
                record_data = {field: entries[field].get() for field in fields}
                # Optionally convert types as needed, e.g. processed to boolean.

                users_map = {user.name: user.user_id for user in self.users} if self.users else {}
                record_data['user_id'] = users_map[record_data['username']]
                record_data['processed'] = bool(int(record_data.get('processed', 0)))
                self.db_manager.save_attendance_record(record_data)
                self.show_success("Record added successfully.")
                form.destroy()
                self.load_records()
                self.display_records()
            except Exception as e:
                self.handle_error("Error adding record", e)

        submit_btn = ttk.Button(form, text="Submit", command=submit)
        submit_btn.grid(row=len(fields), column=0, columnspan=2, pady=10)

    def update_record(self):
        """
        Update the selected attendance record.
        """
        selected_item = self.tree.selection()
        if not selected_item:
            self.show_error("Please select a record to update.")
            return

        # Get the selected record's values.
        record_values = self.tree.item(selected_item, "values")
        # Assuming the first column is the id.
        record_id = record_values[0]

        # Retrieve the full record from self.records.
        record = next((r for r in self.records if str(r.id) == str(record_id)), None)
        if not record:
            self.show_error("Record not found.")
            return

        form = tk.Toplevel(self.root)
        form.title("Update Attendance Record")
        fields = ("username", "timestamp", "status", "punch_type", "processed")
        entries = {}

        # Pre-populate form with current values.
        initial_values = {
            "username": record.username,
            "timestamp": record.timestamp,
            "status": record.status,
            "punch_type": record.punch_type,
            "processed": "1" if record.processed else "0"
        }

        for idx, field in enumerate(fields):
            ttk.Label(form, text=field.capitalize() + ":").grid(row=idx, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(form)
            entry.insert(0, initial_values[field])
            entry.grid(row=idx, column=1, padx=5, pady=5)
            entries[field] = entry

        def submit():
            try:
                # Update record with form values.
                record.username = entries["username"].get()
                record.timestamp = entries["timestamp"].get()
                record.status = entries["status"].get()
                record.punch_type = entries["punch_type"].get()
                record.processed = bool(int(entries["processed"].get()))
                # Call update in the database.
                self.db_manager.update_attendance_record(record)
                self.show_success("Record updated successfully.")
                form.destroy()
                self.load_records()
                self.display_records()
            except Exception as e:
                self.handle_error("Error updating record", e)

        submit_btn = ttk.Button(form, text="Submit", command=submit)
        submit_btn.grid(row=len(fields), column=0, columnspan=2, pady=10)

    def delete_record(self):
        """
        Delete the selected attendance record.
        """
        selected_item = self.tree.selection()
        if not selected_item:
            self.show_error("Please select a record to delete.")
            return

        # Confirm deletion.
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected record?",
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
            self.uploader.upload_data()
            self.load_records()
            self.display_records()
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