import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Config:
    """Configuration model for the attendance system."""
    id: Optional[int] = None
    company_id: str = ""
    api_username: str = ""
    api_password: str = ""
    device_ip: str = ""
    device_port: int = 4370
    collection_interval: Optional[int] = None
    upload_interval: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data):
        """Create a Config instance from a dictionary."""
        if not data:
            return None

        return cls(
            id=data.get('id'),
            company_id=data.get('company_id', ''),
            api_username=data.get('api_username', ''),
            api_password=data.get('api_password', ''),
            device_ip=data.get('device_ip', ''),
            device_port=data.get('device_port', 4370),
            collection_interval=data.get('collection_interval'),
            upload_interval = data.get('upload_interval'),
            created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data.get('updated_at')) if data.get('updated_at') else None
        )

    def to_dict(self):
        """Convert Config object to dictionary."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'api_username': self.api_username,
            'api_password': self.api_password,
            'device_ip': self.device_ip,
            'device_port': self.device_port,
            'collection_interval': self.collection_interval,
            'upload_interval': self.upload_interval,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

@dataclass
class User:
    id: Optional[int] = None
    full_name: str = ""
    created_at: Optional[datetime] = None

    @staticmethod
    def parse_zk_user(zk_user):
        try:
            return User(id=zk_user.user_id, full_name=zk_user.name)
        except Exception as e:
            print(f"Error parsing zk_user: {e}")
            return None

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        return cls(
            id=data.get('id'),
            full_name=data.get('full_name', ''),
            created_at = datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None,
        )

    @classmethod
    def to_dic(cls):
        return {
            'id': cls.id,
            'full_name': cls.full_name,
            'created_at': cls.created_at.isoformat() if cls.created_at else None
        }

@dataclass
class AttendanceRecord:
    """Model for attendance records from the device."""
    id: Optional[int] = None
    uid: Optional[int] = None
    user_id: int = 0
    username: str = ""
    timestamp: str = ""
    status: int = 0
    punch_type: int = 0
    processed: bool = False
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data):
        """Create an AttendanceRecord instance from a dictionary."""
        if not data:
            return None

        return cls(
            id=data.get('id'),
            uid = data.get('uid'),
            user_id=data.get('user_id', 0),
            username=data.get('username', ''),
            timestamp=data.get('timestamp', ''),
            status=data.get('status', 0),
            punch_type=data.get('punch_type', 0),
            processed=data.get('processed', False),
            created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None
        )

    def to_dict(self):
        """Convert AttendanceRecord object to dictionary."""
        return {
            'id': self.id,
            'uid': self.uid,
            'user_id': self.user_id,
            'username': self.username,
            'timestamp': self.timestamp,
            'status': self.status,
            'punch_type': self.punch_type,
            'processed': self.processed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def parse_zk_record(zk_record):
        """Parse a raw ZK attendance record into the structure needed for the database.

        Example format: ": 1 : 2025-03-20 11:25:57 (1, 0)"
        """
        try:
            # Parse the user ID
            parts = zk_record.split(' : ')
            user_id = int(parts[1].strip())

            # Parse the timestamp
            timestamp_part = parts[2].split(' (')[0].strip()

            # Parse status and punch_type
            status_punch = parts[2].split('(')[1].split(')')[0]
            status, punch_type = map(int, status_punch.split(','))

            return AttendanceRecord(
                user_id=user_id,
                username='',
                timestamp=timestamp_part,
                status=status,
                punch_type=punch_type,
                processed = False
            )
        except Exception as e:
            # If parsing fails, return None
            return None


@dataclass
class APIUploadLog:
    """Model for API upload log entries."""
    id: Optional[int] = None
    batch_id: str = ""
    file_path: str = ""
    records_count: int = 0
    status: str = ""  # SUCCESS, FAILED, ERROR
    response_data: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data):
        """Create an APIUploadLog instance from a dictionary."""
        if not data:
            return None

        return cls(
            id=data.get('id'),
            batch_id=data.get('batch_id', ''),
            file_path=data.get('file_path', ''),
            records_count=data.get('records_count', 0),
            status=data.get('status', ''),
            response_data=data.get('response_data'),
            created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None
        )

    def to_dict(self):
        """Convert APIUploadLog object to dictionary."""
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'file_path': self.file_path,
            'records_count': self.records_count,
            'status': self.status,
            'response_data': self.response_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }