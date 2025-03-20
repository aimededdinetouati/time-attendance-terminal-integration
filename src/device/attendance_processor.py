# attendance_processor.py - ZK device connection and attendance processing

import logging
from zk import ZK
from config.config import ZK_IP, ZK_PORT, ZK_TIMEOUT, ZK_PASSWORD, ZK_FORCE_UDP, ZK_OMIT_PING

logger = logging.getLogger(__name__)

class AttendanceProcessor:
    def __init__(self, api_client):
        self.api_client = api_client
        self.zk = ZK(ZK_IP, port=ZK_PORT, timeout=ZK_TIMEOUT, 
                     password=ZK_PASSWORD, force_udp=ZK_FORCE_UDP, 
                     ommit_ping=ZK_OMIT_PING)
        self.conn = None
        
    def connect(self):
        """Connect to the ZK device."""
        try:
            self.conn = self.zk.connect()
            logger.info("Successfully connected to ZK device")
            self.conn.test_voice()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ZK device: {e}")
            return False
    
    def process_attendance(self):
        """Process live attendance data from ZK device."""
        if not self.conn:
            logger.error("No connection to ZK device")
            return False
            
        try:
            # Disable device during processing
            self.conn.disable_device()
            logger.info("Device disabled for processing")
            
            for live_attendance in self.conn.live_capture():
                if live_attendance is None:
                    logger.debug('No live attendance data received')
                    continue
                    
                emp_id = live_attendance.user_id  
                timestamp = live_attendance.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                print(live_attendance)
                # success = self.api_client.send_attendance(emp_id, timestamp)
                # if success:
                #     logger.info(f"Processed attendance: {live_attendance}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error processing attendance: {e}")
            return False
        finally:
            if self.conn:
                # Re-enable device after processing
                try:
                    self.conn.enable_device()
                    logger.info("Device re-enabled")
                except Exception as e:
                    logger.error(f"Failed to re-enable device: {e}")
    
    def disconnect(self):
        """Disconnect from ZK device."""
        if self.conn:
            try:
                self.conn.disconnect()
                logger.info("Disconnected from ZK device")
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from device: {e}")
                return False
        return True