import logging
from zk import ZK, const
from datetime import datetime
import time

from src.database.models import User, AttendanceRecord

logger = logging.getLogger(__name__)


class AttendanceProcessor:
    def __init__(self, ip, port):
        """Initialize the attendance processor with device connection details."""
        self.ip = ip
        self.port = port
        self.zk = ZK(ip, port=port)
        self.conn = None

    def connect(self):
        """Connect to the ZK device."""
        try:
            self.conn = self.zk.connect()
            logger.info(f"Connected to ZK device at {self.ip}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ZK device: {e}")
            return False

    def disconnect(self):
        """Disconnect from the ZK device."""
        if self.conn:
            self.conn.disconnect()
            logger.info("Disconnected from ZK device")

    def get_users(self):
        """Get users from the device"""
        if not self.conn:
            logger.error("Not connected to ZK device")
            return None
        try:
            users = self.conn.get_users()
            logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error retrieving users: {e}")
            return []


    def get_attendance(self, users):
        """Get attendance records from the device."""
        if not self.conn:
            logger.error("Not connected to ZK device")
            return []

        try:
            attendance = self.conn.get_attendance()
            processed_records = []

            users_map = {user.user_id: user.name for user in users} if users else {}

            for record in attendance:
                username = users_map[record.user_id]
                # Parse attendance data

                processed_record = AttendanceRecord (
                    uid = record.uid,
                    user_id = record.user_id,
                    username = username,
                    timestamp = record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    status = record.status,
                    punch_type = record.punch
                )
                processed_records.append(processed_record)

            logger.info(f"Retrieved {len(processed_records)} attendance records")
            return processed_records
        except Exception as e:
            logger.error(f"Error retrieving attendance data: {e}")
            return []

    def clear_attendance(self):
        """Clear attendance records from the device."""
        if not self.conn:
            logger.error("Not connected to ZK device")
            return False

        try:
            self.conn.clear_attendance()
            logger.info("Cleared attendance records from device")
            return True
        except Exception as e:
            logger.error(f"Error clearing attendance data: {e}")
            return False