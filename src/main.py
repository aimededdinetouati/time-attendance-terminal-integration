# main.py - Main application entry point

import logging
import sys
import os
from src.api.api_client import APIClient
from src.device.attendance_processor import AttendanceProcessor


# Ensure logs directory exists
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, 'attendance.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("attendance.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the attendance application."""
    logger.info("Starting attendance application")
    
    # Initialize API client
    api_client = APIClient()
    try:
        api_client.initialize()
        logger.info("API client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        return
    
    # Initialize attendance processor
    processor = AttendanceProcessor(api_client)
    
    try:
        # Connect to ZK device
        if not processor.connect():
            logger.error("Could not connect to ZK device. Exiting.")
            return
            
        # Process attendance data
        processor.process_attendance()
        
    except Exception as e:
        logger.error(f"Error in attendance processing: {e}")
    finally:
        # Ensure disconnection from ZK device
        processor.disconnect()
        
    logger.info("Attendance application completed")

if __name__ == "__main__":
    main()