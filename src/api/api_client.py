import requests
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self, api_url, company_id, username, password):
        """Initialize the API client with connection details."""
        self.api_url = api_url.rstrip('/')
        self.company_id = company_id
        self.username = username
        self.password = password
        self.xsrf_token = None
        self.jwt_token = None
        self.session = requests.Session()

    def authenticate(self):
        """Authenticate with the API using XSRF and JWT."""
        try:
            # Step 1: Get XSRF token
            response = self.session.get(f"{self.api_url}/auth/hello")
            if response.status_code != 200:
                logger.error(f"Failed to get XSRF token: {response.status_code}")
                return False

            # Extract XSRF token from cookies
            if 'XSRF-TOKEN' in self.session.cookies:
                self.xsrf_token = self.session.cookies['XSRF-TOKEN']
                logger.info("Successfully obtained XSRF token")
            else:
                logger.error("XSRF token not found in response cookies")
                return False

            # Step 2: Perform login to get JWT token
            headers = {
                'X-XSRF-TOKEN': self.xsrf_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            data = {
                'username': self.username,
                'password': self.password,
                'company_id': self.company_id
            }

            response = self.session.post(
                f"{self.api_url}/auth/login",
                json=data,
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"Authentication failed: {response.status_code}")
                logger.debug(f"Response: {response.text}")
                return False

            # Extract JWT token from response
            auth_data = response.json()
            if 'access_token' in auth_data:
                self.jwt_token = auth_data['access_token']
                logger.info("Successfully authenticated with API")
                return True
            else:
                logger.error("JWT token not found in authentication response")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def get_auth_headers(self):
        """Get headers with authentication tokens."""
        if not self.xsrf_token or not self.jwt_token:
            if not self.authenticate():
                raise Exception("Authentication required")

        return {
            'X-XSRF-TOKEN': self.xsrf_token,
            'Authorization': f"Bearer {self.jwt_token}",
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def upload_attendance(self, file_path):
        """Upload attendance data from an Excel file to the API."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {'success': False, 'message': 'File not found'}

        try:
            headers = self.get_auth_headers()
            # Remove Content-Type as it will be set by requests for multipart/form-data
            headers.pop('Content-Type', None)

            with open(file_path, 'rb') as file:
                files = {
                    'file': (os.path.basename(file_path), file,
                             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                }

                data = {
                    'company_id': self.company_id,
                    'upload_date': datetime.now().strftime('%Y-%m-%d')
                }

                response = self.session.post(
                    f"{self.api_url}/api/attendance/upload",
                    headers=headers,
                    data=data,
                    files=files
                )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token might be expired, try to re-authenticate
                logger.warning("Authentication token expired, attempting to re-authenticate")
                if self.authenticate():
                    # Retry with new token
                    return self.upload_attendance(file_path)
                else:
                    return {'success': False, 'message': 'Re-authentication failed'}
            else:
                logger.error(f"API upload failed: {response.status_code}")
                logger.debug(f"Response: {response.text}")
                return {'success': False, 'message': f'API Error: {response.text}'}

        except Exception as e:
            logger.error(f"Error uploading attendance data: {e}")
            return {'success': False, 'message': str(e)}