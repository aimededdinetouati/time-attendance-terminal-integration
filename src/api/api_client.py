# api_client.py - API connection and authentication

import requests
import json
import logging
from config.config import API_URL, USERNAME, PASSWORD, COMPANY_ID

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        self.session = None
        self.xsrf_token = None
        self.access_token = None
    
    def initialize(self):
        """Initialize API connection by getting XSRF token and logging in."""
        self.session, self.xsrf_token = self.get_xsrf_token()
        if not self.xsrf_token:
            raise Exception("Failed to retrieve XSRF token. Exiting...")
            
        self.access_token = self.login()
        if not self.access_token:
            raise Exception("Failed to authenticate. Exiting...")
        
        return self.access_token, self.xsrf_token
            
    def get_xsrf_token(self):
        """Fetch the XSRF token from the /hello endpoint."""
        hello_url = f"{API_URL}/auth/hello"
        print(f"Request to {hello_url} to fecth the XSRF token")
        session = requests.Session()  # Maintain session cookies
        
        try:
            response = session.get(hello_url, timeout=5)
            if response.status_code == 200:
                xsrf_token = response.cookies.get("XSRF-TOKEN")
                logger.info(f"XSRF Token retrieved successfully")
                return session, xsrf_token
            else:
                logger.error(f"Failed to fetch XSRF token. Status: {response.status_code}, Response: {response.text}")
                return None, None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching XSRF token: {e}")
            return None, None

    def login(self):
        """Perform login and retrieve authentication token."""
        login_url = f"{API_URL}/auth/login"
        
        headers = {
            "X-XSRF-TOKEN": self.xsrf_token,
            "Content-Type": "application/json"
        }

        payload = json.dumps({
            "username": USERNAME,
            "password": PASSWORD,
            "rememberMe": False
        })

        try:
            response = self.session.post(login_url, headers=headers, data=payload, timeout=5)
            
            if response.status_code == 200:
                auth_response = response.json()
                auth_token = auth_response.get("access_token")
                logger.info("Authentication successful")
                return auth_token
            else:
                logger.error(f"Login failed. Status: {response.status_code}, Response: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during login: {e}")
            return None
            
    def send_attendance(self, emp_id, timestamp):
        """Send live attendance data to external API."""
        if not self.access_token or not self.xsrf_token:
            logger.error("Missing authentication tokens. Cannot send attendance data.")
            return False
            
        headers = {
            "Authorization": f"Bearer {self.access_token}",  
            "X-XSRF-TOKEN": self.xsrf_token,                
            "Content-Type": "application/json",
        }

        data = {
            "employee_id": emp_id,
            "timestamp": timestamp
        }
        
        try:
            response = requests.post(
                    f"{API_URL}/pay/companies/{COMPANY_ID}/pointings/attendance", 
                    headers=headers, 
                    json=data, 
                    timeout=5
                )
            if response.status_code == 200:
                logger.info(f"Successfully sent attendance for employee {emp_id}")
                return True
            else:
                logger.error(f"Failed to send data for employee {emp_id}. Response: {response.status_code}, {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending data: {e}")
            return False