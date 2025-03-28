import logging
import time
import schedule
from datetime import datetime

from src.device.attendance_processor import AttendanceProcessor
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AttendanceCollector:
    def __init__(self, db_manager=None):
        """Initialize the attendance collector with a database manager."""
        self.db_manager = db_manager or DatabaseManager()
        self.processor = None
        self.running = False

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

    def collect_attendance(self, users):
        """Collect attendance data and save to database."""
        if not self.processor:
            if not self.initialize():
                logger.error("Failed to initialize attendance processor")
                return

        logger.info("Collecting attendance data...")
        attendance_records = self.processor.get_attendance(users)

        if attendance_records and len(attendance_records) > 0:
            self.db_manager.save_attendance_records(attendance_records)
            logger.info(f"Collected and saved {len(attendance_records)} attendance records")
        else:
            logger.info("No new attendance records to collect")

    def start_scheduler(self, users, interval_minutes=60):
        """Start the attendance collection scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        # First run immediately
        self.collect_attendance(users)

        # Schedule regular runs
        schedule.every(interval_minutes).minutes.do(self.collect_attendance)

        self.running = True
        logger.info(f"Attendance collector scheduled to run every {interval_minutes} minutes")

        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop_scheduler(self):
        """Stop the attendance collection scheduler."""
        self.running = False
        schedule.clear()

        logger.info("Attendance collector scheduler stopped")