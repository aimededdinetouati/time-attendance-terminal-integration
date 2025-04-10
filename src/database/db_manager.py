import sqlite3
import os
import logging
from datetime import datetime
import json
from src.database.models import Config, User, AttendanceRecord, APIUploadLog

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # go two levels up
            db_path = os.path.join(base_dir, 'data', 'attendance.db')
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
            import_interval INTEGER NOT NULL DEFAULT 12,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY,
            uid INTEGER NOT NULL UNIQUE DEFAULT 2000000,
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
                device_ip = ?, device_port = ?, collection_interval = ?, upload_interval = ?, import_interval = ?, updated_at = ? 
            WHERE id = ?
            ''', (
                config.company_id, config.api_username, config.api_password,
                config.device_ip, config.device_port, config.collection_interval,
                config.upload_interval, config.import_interval, datetime.now(), existing_config['id']
            ))
        else:
            cursor.execute('''
            INSERT INTO config (
                company_id, api_username, api_password, device_ip, device_port, collection_interval, upload_interval, import_interval
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.company_id, config.api_username, config.api_password,
                config.device_ip, config.device_port, config.collection_interval, config.upload_interval, config.import_interval
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
                upload_interval=row['upload_interval'], import_interval=row['import_interval']
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
                cursor.execute('''
                    INSERT OR IGNORE INTO attendance_records (
                        uid, user_id, username, timestamp, status, punch_type
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (record.uid, record.user_id, record.username, record.timestamp, record.status, record.punch_type))

            conn.commit()
            logger.info(f"Saved {len(records)} attendance records to database")
        finally:
            conn.close()

    def save_attendance_record(self, record):
        """Save a signle AttendanceRecord."""

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            record = AttendanceRecord.from_dict(record)

            cursor.execute('SELECT MAX(uid) FROM attendance_records')
            max_uid = cursor.fetchone()[0]
            max_uid = max_uid + 1 if max_uid > 2000000 else 2000000
            cursor.execute('''
                INSERT INTO attendance_records (
                    uid, user_id, username, timestamp, status, punch_type, processed
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (max_uid, record.user_id, record.username, record.timestamp, record.status, record.punch_type, record.processed))

            conn.commit()
            logger.info(f"Saved attendance record with id {record.id} to database")
        finally:
            conn.close()


    def delete_attendance_record(self, attendance_record):
        """
        Delete a single AttendanceRecord in the database.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = '''
                DELETE FROM attendance_records
                WHERE id = ?
            '''
            cursor.execute(query, (attendance_record.id,))
            conn.commit()
            logger.info(
                f"Deleted attendance record for id {attendance_record.id}")
        finally:
            conn.close()

    def update_attendance_record(self, attendance_record):
        """
        Update a single AttendanceRecord in the database.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = '''
                UPDATE attendance_records
                SET 
                    username = ?,
                    status = ?,
                    punch_type = ?,
                    processed = ?,
                    timestamp = ?
                WHERE id = ?
            '''
            cursor.execute(query, (
                attendance_record.username,
                attendance_record.status,
                attendance_record.punch_type,
                attendance_record.processed,
                attendance_record.timestamp,
                attendance_record.id
            ))
            conn.commit()
            logger.info(
                f"Updated attendance record for id {attendance_record.id}")
        finally:
            conn.close()

    def get_attendance_records(self, filter_processed=None, order_by='timestamp'):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Base query
        query = f'''
            SELECT * FROM attendance_records 
        '''

        params = []

        # Add WHERE clause if filtering by processed status
        if filter_processed is not None:
            query += 'WHERE processed = ? '
            params.append(filter_processed)

        # Add ORDER BY clause
        query += f'ORDER BY {order_by} ASC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            AttendanceRecord(
                id=row['id'],
                user_id=row['user_id'],
                username=row['username'],
                timestamp=row['timestamp'],
                status=row['status'],
                punch_type=row['punch_type'],
                processed=row['processed']
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
