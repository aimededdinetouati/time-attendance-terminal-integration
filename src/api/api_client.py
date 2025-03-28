import requests
import logging
import os
import time
from datetime import datetime, timedelta

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

            logger.debug(f"Token before login: {self.xsrf_token}")
            # After login, update token
            if 'XSRF-TOKEN' in self.session.cookies:
                self.xsrf_token = self.session.cookies['XSRF-TOKEN']
            logger.debug(f"Token after login: {self.xsrf_token}")

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
        if not self.authenticate():
            raise Exception("Authentication required")

        return {
            'X-XSRF-TOKEN': self.xsrf_token,
            'Authorization': f"Bearer {self.jwt_token}",
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_pointing_import(self):
        headers = self.get_auth_headers()


        response = self.session.get(
            f"{self.api_url}/pay/api/companies/{self.company_id}/pointing-imports",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print("Pointing import data retrieved successfully.")
            return {
                "id": data.get("id"),
                "status": data.get("status"),
                "companyId": data.get("companyId"),
                "jobExecutionId": data.get("jobExecutionId"),
                "total": data.get("total"),
                "skipped": data.get("skipped"),
                "written": data.get("written"),
                "filename": data.get("filename"),
                "created": data.get("created")
            }
        else:
            print(f"Failed to retrieve pointing import data. Status code: {response.status_code}")
            response.raise_for_status()  # Raise an exception for other error status codes

        print("Timeout reached: No content was retrieved within 30 seconds.")
        raise Exception("Timeout reached: No content was retrieved within 30 seconds.")

    def get_pointings_with_job_id(self, job_execution_id):
        """Fetch pointings with filters, including jobExecutionId."""
        headers = self.get_auth_headers()

        # Build query parameters
        params = {
            'jobExecutionId': job_execution_id,
        }

        try:
            response = self.session.get(
                f"{self.api_url}/pay/api/companies/{self.company_id}/pointings",
                headers=headers,
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                print("Pointings data retrieved successfully.")
                return self.transform_data(data)  # Returns the list of PointingDTO
            else:
                print(f"Failed to retrieve pointings. Status code: {response.status_code}")
                response.raise_for_status()

        except Exception as e:
            print(f"Error fetching pointings: {e}")
            raise

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

                month = datetime.now().strftime("%Y-%m")
                response = self.session.post(
                    f"{self.api_url}/pay/api/companies/{self.company_id}/month-pointing/{month}/import",
                    headers=headers,
                    files=files
                )

            if response.status_code == 200:
                # os.remove(file_path)
                response_data = response.json()
                job_execution_id = response_data.get("jobExecutionId")
                logger.info(f"Job execution started with ID: {job_execution_id}")
                return {'success': True, 'jobExecutionId': job_execution_id}
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

    def transform_data(self, pointings):
        result = []

        # Iterate through each pointing and extract the entrance and exit timestamps
        for pointing in pointings:
            if pointing.get("entrance"):
                result.append(pointing.get("entrance"))
            if pointing.get("exit"):
                result.append(pointing.get("exit"))
        return result
