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

logger = logging.getLogger(__name__)


class APIUploader:
    def __init__(self, db_manager=None):
        """Initialize the API uploader with a database manager."""
        self.db_manager = db_manager or DatabaseManager()
        self.api_client = None
        self.running = False

        # Ensure exports directory exists
        os.makedirs('exports', exist_ok=True)

    def initialize(self):
        """Initialize the API client with config from the database."""
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

        return self.api_client.authenticate()

    def create_excel_report(self, records):
        """Create an Excel report from attendance records."""
        if not records:
            logger.info("No records to export")
            return None

        # Create a unique filename
        batch_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"exports/attendance_{timestamp}_{batch_id}.xlsx"

        # Create DataFrame from records
        df = pd.DataFrame(records)

        punch_mapping = {
            0: 'entree',
            1: 'sortie'
        }

        # Format the DataFrame for export
        # You might need to adjust this based on your exact API requirements
        export_df = pd.DataFrame({
            'code': df['username'],
            'Nom': None,
            'time': df['timestamp'],
            'type': df['punch_type'].map(punch_mapping)  # Map 0 to 'entree' and 1 to 'sortie'
        })

        # Save to Excel
        export_df.to_excel(filename, index=False)
        logger.info(f"Created Excel report with {len(records)} records at {filename}")

        return {
            'batch_id': batch_id,
            'file_path': filename,
            'records_count': len(records)
        }

    def upload_data(self):
        """Process unprocessed attendance records and upload to API."""
        if not self.api_client:
            if not self.initialize():
                logger.error("Failed to initialize API client")
                return

        # Get unprocessed records
        records = self.db_manager.get_attendance_records()
        if not records:
            logger.info("No unprocessed attendance records to upload")
            return

        # Create Excel report
        export_info = self.create_excel_report(records)
        if not export_info:
            return

        # Upload to API
        try:
            response = self.api_client.upload_attendance(export_info['file_path'])

            if response.get('success', False):
                job_execution_id = response.get('jobExecutionId')
                end_time = datetime.now() + timedelta(seconds=30)
                while end_time > datetime.now() :
                    pointing_import = self.api_client.get_pointing_import()
                    import_status = pointing_import['status']
                    if import_status == "COMPLETED":
                        logger.info("Pointing import completed successfully.")
                        job_execution_id = pointing_import['jobExecutionId']
                        attendance_records = self.api_client.get_pointings_with_job_id(job_execution_id)
                        if len(attendance_records) > 0:
                            self.db_manager.mark_records_processed(attendance_records)
                        return
                    elif import_status == "STARTED" or import_status == "STARTING":
                        logger.warning("The import pointing request didn't complete yet")
                        time.sleep(2)
                    elif import_status == "FAILED" or import_status == "STOPPED":
                        logger.error("Pointing import failed. Please check the API logs or error details.")

                        self.db_manager.log_api_upload(
                            APIUploadLog(
                                batch_id=export_info['batch_id'],
                                file_path=export_info['file_path'],
                                records_count=export_info['records_count'],
                                status="FAILED",
                                response_data=pointing_import
                            )
                        )
                        return
                    else:
                        raise Exception("Pointing Import with unknown status")


                # self.db_manager.delete_processed_records(saved_timestamps)

                # Log successful upload
                self.db_manager.log_api_upload(
                    APIUploadLog(
                        batch_id=export_info['batch_id'],
                        file_path=export_info['file_path'],
                        records_count=export_info['records_count'],
                        status="SUCCESS",
                        response_data=response
                    )
                )

                logger.info(f"Successfully uploaded {len(records)} attendance records to API")
            else:
                # Log failed upload
                self.db_manager.log_api_upload(
                    APIUploadLog(
                        batch_id=export_info['batch_id'],
                        file_path=export_info['file_path'],
                        records_count=export_info['records_count'],
                        status="FAILED",
                        response_data=response
                    )
                )

                logger.error(f"Failed to upload attendance records: {response.get('message', 'Unknown error')}")

        except Exception as e:
            # Log exception
            self.db_manager.log_api_upload(
                APIUploadLog(
                    batch_id=export_info['batch_id'],
                    file_path=export_info['file_path'],
                    records_count=export_info['records_count'],
                    status="ERROR",
                    response_data=str(e)
                )
            )

            logger.error(f"Error uploading attendance records: {e}")

    def start_scheduler(self, interval_hours=1):
        """Start the API upload scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        # Schedule regular runs
        schedule.every(interval_hours).hours.do(self.upload_data)

        self.running = True
        logger.info(f"API uploader scheduled to run every {interval_hours} hours")

        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop_scheduler(self):
        """Stop the API upload scheduler."""
        self.running = False
        schedule.clear()
        logger.info("API uploader scheduler stopped")