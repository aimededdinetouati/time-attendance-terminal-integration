import logging
import schedule
import time
import os
import uuid
from datetime import datetime, timedelta
import pandas as pd

from src.database.db_manager import DatabaseManager
from src.api.api_client import APIClient
from config.config import API_URL
from src.database.models import APIUploadLog
from src.device.attendance_processor import AttendanceProcessor

logger = logging.getLogger(__name__)

class UserImporter:

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or DatabaseManager()
        self.api_client = None
        self.processor = None
        self.running = False

    def initialize(self):
        config = self.db_manager.get_config()
        if not config:
            logger.error("No configuration found in database")
            return False

        self.api_client = APIClient(
            api_url=API_URL,
            company_id=config.company_id,
            username=config.api_username,
            password=config.api_password
        )

        self.processor = AttendanceProcessor(
            ip=config.device_ip,
            port=config.device_port
        )

        return self.api_client.authenticate() and self.processor.connect()

    def import_users(self):
        if not self.api_client or not self.processor:
            if not self.initialize():
                logger.error("Failed to initialize API client or attendance processor")
                return {'success': False, 'message': 'Initialization failed'}

        employees = self.api_client.get_employees()
        saved_users = {user.name for user in self.processor.get_users()}

        imported = 0
        for employee in employees:
            emp_id = employee.get('id')
            code = employee.get('code')

            if not emp_id or not code:
                logger.warning(f"Skipping employee due to missing data: {employee}")
                continue
            if code in saved_users:
                logger.warning(f"Skipping employee: {employee}, already saved")
                continue

            try:
                self.processor.set_user(emp_id=emp_id, code=code)
                imported += 1
            except Exception as e:
                logger.error(f"Error setting user: {code} - error: {e}")

        return imported

    def start_scheduler(self, interval_hours=12):
        """Start the User Importer scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        # Schedule regular runs
        schedule.every(interval_hours).hours.do(self.import_users)

        self.running = True
        logger.info(f"User Importer scheduled to run every {interval_hours} hours")

        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop_scheduler(self):
        """Stop the User Import scheduler."""
        self.running = False
        schedule.clear()
        logger.info("User Importer scheduler stopped")
