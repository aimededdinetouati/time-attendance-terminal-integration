# Attendance System

## Overview

The Attendance System is a Python application that connects to a ZK biometric device, captures real-time attendance data, and sends it to a web API. The system authenticates with the API using XSRF tokens and JWT authentication, processing attendance records in real time.

## System Architecture

The application is structured using a modular approach:

```
attendance-system/
│
├── config/
│   ├── __init__.py
│   └── config.py         # Configuration settings
│
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── api_client.py  # API connection and authentication
│   │
│   ├── device/
│   │   ├── __init__.py
│   │   └── attendance_processor.py  # ZK device connection and processing
│   │
│   └── main.py           # Main application entry point
│
├── logs/                 # Directory for log files
│   └── .gitkeep
│
├── README.md             # Project overview
├── requirements.txt      # Dependencies
└── .gitignore            # Git ignore file
```

## Installation

### Prerequisites

- Python 3.7 or higher
- Network access to the ZK device
- Network access to the API endpoints

### Setup

1. Clone the repository:

   ```bash
   git clone [repository-url] attendance-system
   cd attendance-system
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Update the configuration in `config/config.py` with your specific settings:
   - Company ID
   - API URL
   - Authentication credentials
   - ZK device IP and port

## Usage

Run the application with:

```bash
python -m src.main
```

## Components

### Configuration (config/config.py)

Contains all system configuration variables including API connection details, authentication credentials, and ZK device settings.

### API Client (src/api/api_client.py)

Manages the API authentication flow, XSRF token acquisition, and JWT authentication. Provides methods to send attendance data to the API.

### Attendance Processor (src/device/attendance_processor.py)

Handles the connection to the ZK biometric device, processes live attendance capture, and coordinates with the API client to send data.

### Main Application (src/main.py)

Serves as the application entry point, orchestrates the overall process flow, configures logging, and handles error cases and cleanup.

## Workflow

1. The API client establishes a connection to the API server
2. Authentication is performed using XSRF tokens and JWT
3. The application connects to the ZK biometric device
4. The system listens for attendance events from the ZK device
5. Each attendance record is processed in real-time and sent to the API
6. The device acknowledges successful processing with a voice confirmation

## Logging

Logs are written to both the console and to files in the `logs/` directory. The default log level is INFO, which can be adjusted in `src/main.py`.

## Troubleshooting

Common issues and their solutions:

1. **Unable to connect to ZK device**

   - Verify the IP address and port in the configuration
   - Ensure the device is powered on and connected to the network
   - Check for any firewall rules that might block the connection

2. **API authentication failures**

   - Verify the API URL, username, and password
   - Check if the API server is accessible from your network
   - Ensure the company ID is correct

3. **No attendance data being processed**
   - Verify the ZK device is properly configured for live capture
   - Check the logs for any error messages during connection

## Extending the System

### Adding New API Endpoints

To add support for additional API endpoints:

1. Add new methods to the `APIClient` class in `src/api/api_client.py`
2. Ensure proper authentication headers are included
3. Handle response validation and error cases

### Supporting Different Biometric Devices

To add support for different biometric devices:

1. Create a new processor module in `src/device/`
2. Implement the same interface as the `AttendanceProcessor` class
3. Update the main application to use the new processor based on configuration
