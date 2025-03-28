import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, List

from src.database.db_manager import DatabaseManager
from src.database.models import AttendanceRecord
from src.device.attendance_processor import AttendanceProcessor
from src.scheduler.api_uploader import APIUploader

logger = logging.getLogger(__name__)


class RecordsInterface:
    """
    A GUI interface for displaying attendance records from the database.
    """

    def __init__(self, root: Optional[tk.Tk], db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the RecordsInterface.

        Args:
            root: The parent Tkinter window.
            db_manager: Optional database manager instance; if not provided, a new instance is created.
        """
        self.db_manager = db_manager or DatabaseManager()
        self.uploader = APIUploader(self.db_manager)
        self.root = tk.Toplevel(root)
        self.root.title("Attendance Records")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.status_var = tk.StringVar()
        self.records: List[AttendanceRecord] = []

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
        Load attendance records from the database.
        Sets self.records to an empty list if no records are found.
        """
        try:
            records = self.db_manager.get_attendance_records()
            if not records:
                logger.info("No attendance records found in the database.")
                self.records = []
                return

            self.records = records  # Expecting a list of AttendanceRecord instances
            logger.info("Attendance records loaded successfully.")

        except Exception as e:
            self.handle_error("Error loading attendance records", e)

    def display_records(self):
        """
        Display the attendance records in the main frame.
        If there are no records, shows a message.
        """
        # Clear previous widgets in the main frame if any.
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Title label for the records section.
        title_label = ttk.Label(self.main_frame, text="Attendance Records", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))

        # If no records exist, display a message.
        if not self.records:
            no_record_label = ttk.Label(self.main_frame, text="No attendance records to display.", foreground="red")
            no_record_label.pack(pady=20)
        else:
            # Create a Treeview widget to display records in a table.
            # Added new column "processed"
            columns = ("user_id", "timestamp", "status", "punch_type", "processed")
            tree = ttk.Treeview(self.main_frame, columns=columns, show="headings", selectmode="browse")

            # Define headings for each column.
            tree.heading("user_id", text="User ID")
            tree.heading("timestamp", text="Timestamp")
            tree.heading("status", text="Status")
            tree.heading("punch_type", text="Punch Type")
            tree.heading("processed", text="Processed")

            # Set the width for each column.
            tree.column("user_id", width=100, anchor=tk.CENTER)
            tree.column("timestamp", width=200, anchor=tk.CENTER)
            tree.column("status", width=100, anchor=tk.CENTER)
            tree.column("punch_type", width=100, anchor=tk.CENTER)
            tree.column("processed", width=100, anchor=tk.CENTER)

            # Insert each AttendanceRecord instance into the Treeview.
            for record in self.records:
                user_id = record.user_id
                timestamp = record.timestamp if record.timestamp else "N/A"
                status = record.status
                punch_type = record.punch_type
                processed = "Yes" if record.processed else "No"  # New column based on processed boolean

                tree.insert("", tk.END, values=(user_id, timestamp, status, punch_type, processed))

            # Add a vertical scrollbar for the Treeview.
            scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Re-add the "SYNCHRONIZE" button after clearing and rebuilding widgets.
        synchronize_button = ttk.Button(self.main_frame, text="SYNCHRONIZE", command=self.synchronize_records)
        synchronize_button.pack(side=tk.BOTTOM, pady=10)

    def synchronize_records(self):
        """
        Call the APIClient.upload_attendance function to synchronize attendance records.
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

        Args:
            message: The error message to display.
        """
        self.status_var.set(message)
        messagebox.showerror("Error", message, parent=self.root)

    def show_success(self, message: str):
        """
        Display a success message to the user.

        Args:
            message: The success message to display.
        """
        self.status_var.set(message)
        messagebox.showinfo("Success", message, parent=self.root)

    def handle_error(self, message: str, exception: Exception):
        """
        Log and display an error message.

        Args:
            message: Contextual message for the error.
            exception: The exception that occurred.
        """
        error_msg = f"{message}: {exception}"
        logger.error(error_msg)
        self.show_error(error_msg)
