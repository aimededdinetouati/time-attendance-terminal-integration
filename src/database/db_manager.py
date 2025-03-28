import sqlite3
import os
import logging
from datetime import datetime
import json
from src.database.models import Config, User, AttendanceRecord, APIUploadLog

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path='data/attendance.db'):
        """Initialize the database manager with path to SQLite database."""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.initialize_db()

    def get_connection(self):
        """Create and return a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_db(self):
        """Initialize database tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY,
            company_id TEXT NOT NULL,
            api_username TEXT NOT NULL,
            api_password TEXT NOT NULL,
            device_ip TEXT NOT NULL,
            device_port INTEGER NOT NULL,
            collection_interval INTEGER NOT NULL,
            upload_interval INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT,  
            timestamp TEXT NOT NULL UNIQUE,
            status INTEGER NOT NULL,
            punch_type INTEGER NOT NULL,
            processed BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_upload_logs (
            id INTEGER PRIMARY KEY,
            batch_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            records_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            response_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def save_config(self, config):
        """Save or update a Config object."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM config LIMIT 1")
        existing_config = cursor.fetchone()

        if existing_config:
            cursor.execute('''
            UPDATE config SET 
                company_id = ?, api_username = ?, api_password = ?, 
                device_ip = ?, device_port = ?, collection_interval = ?, upload_interval = ?, updated_at = ? 
            WHERE id = ?
            ''', (
                config.company_id, config.api_username, config.api_password,
                config.device_ip, config.device_port, config.collection_interval,
                config.upload_interval, datetime.now(), existing_config['id']
            ))
        else:
            cursor.execute('''
            INSERT INTO config (
                company_id, api_username, api_password, device_ip, device_port, collection_interval, upload_interval
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.company_id, config.api_username, config.api_password,
                config.device_ip, config.device_port, config.collection_interval, config.upload_interval
            ))

        conn.commit()
        conn.close()
        logger.info("Config saved successfully")

    def get_config(self):
        """Retrieve the current Config as a Config object."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM config LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            return Config(
                company_id=row['company_id'], api_username=row['api_username'],
                api_password=row['api_password'], device_ip=row['device_ip'],
                device_port=row['device_port'], collection_interval=row['collection_interval'],
                upload_interval=row['upload_interval']
            )
        return None

    def save_attendance_records(self, records):
        """Save a list of AttendanceRecord objects."""
        if not records:
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()


            # TODO this tries to insert all the records found in the device even the old ones, find a better solution
            for record in records:
                record = AttendanceRecord.from_dict(record)
                cursor.execute('''
                    INSERT OR IGNORE INTO attendance_records (
                        user_id, username, timestamp, status, punch_type
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (record.user_id, record.username, record.timestamp, record.status, record.punch_type))

            conn.commit()
            logger.info(f"Saved {len(records)} attendance records to database")
        finally:
            conn.close()

    def get_attendance_records(self, processed = '0'):
        """Retrieve unprocessed attendance records as a list of AttendanceRecord objects."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM attendance_records 
            WHERE processed = ?
            ORDER BY username ASC
        ''', processed)

        rows = cursor.fetchall()
        conn.close()

        return [
            AttendanceRecord(
                user_id=row['user_id'], username=row['username'], timestamp=row['timestamp'],
                status=row['status'], punch_type=row['punch_type'], processed=row['processed']
            )
            for row in rows
        ]

    def mark_records_processed(self, timestamps):
        """Mark attendance records as processed using their timestamps."""
        if not timestamps:
            return

        conn = self.get_connection()
        cursor = conn.cursor()

        placeholders = ','.join(['?'] * len(timestamps))
        formatted_timestamps = [ts.replace("T", " ") for ts in timestamps]

        cursor.execute(f'''
            UPDATE attendance_records 
            SET processed = 1 
            WHERE timestamp IN ({placeholders})
        ''', formatted_timestamps)

        conn.commit()
        conn.close()
        logger.info(f"Marked {len(timestamps)} records as processed")

    def log_api_upload(self, log):
        """Log an API upload using an ApiUploadLog object."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO api_upload_logs (
            batch_id, file_path, records_count, status, response_data
        ) VALUES (?, ?, ?, ?, ?)
        ''', (
            log.batch_id, log.file_path, log.records_count, log.status,
            json.dumps(log.response_data) if log.response_data else None
        ))

        conn.commit()
        conn.close()
        logger.info(f"Logged API upload: {log.batch_id}, {log.status}")
