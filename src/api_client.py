import requests
import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

class WattWiseClient:
    def __init__(self, base_url: str, username: str, password: str, xsrf_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.xsrf_token = xsrf_token
        self.last_response = None
        self.rate_limit_remaining = 60
        
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://wattwise.ng',
            'Referer': 'https://wattwise.ng/dashboard',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        if self.xsrf_token:
            headers['X-XSRF-Token'] = self.xsrf_token
        return headers
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f'{self.base_url}{endpoint}'
        headers = self._get_headers()
        headers.update(kwargs.pop('headers', {}))
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=30,
                **kwargs
            )
            
            self.last_response = response
            if 'X-RateLimit-Remaining' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            
            return response
        except requests.RequestException as e:
            raise Exception(f'API request failed: {str(e)}')
    
    def login(self) -> bool:
        try:
            login_url = 'https://wattwise.ng/login'
            response = self.session.get(login_url, timeout=30)
            
            if 'XSRF-TOKEN' in response.cookies:
                self.xsrf_token = response.cookies['XSRF-TOKEN']
            
            login_data = {
                'email': self.username,
                'password': self.password
            }
            
            response = self.session.post(
                f'{self.base_url}/login',
                json=login_data,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                if 'XSRF-TOKEN' in response.cookies:
                    self.xsrf_token = response.cookies['XSRF-TOKEN']
                return True
            return False
        except Exception as e:
            raise Exception(f'Login failed: {str(e)}')
    
    def get_meter_overview(self) -> Optional[Dict[str, Any]]:
        response = self._make_request('GET', '/user-meter-overview')
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'SUCCESS':
                return data.get('data')
        return None
    
    def get_dashboard_overview(self) -> Optional[Dict[str, Any]]:
        response = self._make_request('GET', '/user-dashboard-overview')
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'SUCCESS':
                return data.get('data')
        return None
    
    def get_monthly_data(self, option: str = 'present') -> Optional[Dict[str, Any]]:
        response = self._make_request(
            'POST', 
            '/my-monthly-data',
            json={'monthly_option': option}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'SUCCESS':
                return data.get('data')
        return None
    
    def get_graph_data(self, option: str = 'item_7_days') -> Optional[Dict[str, Any]]:
        response = self._make_request(
            'POST',
            '/my-graph-data',
            json={'graph_option': option}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'SUCCESS':
                return data.get('data')
        return None
    
    def check_data_freshness(self, updated_at_str: str) -> Dict[str, Any]:
        try:
            updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            now = datetime.now()
            days_stale = (now - updated_at).days
            
            return {
                'is_stale': days_stale > 30,
                'days_stale': days_stale,
                'last_update': updated_at_str,
                'warning': f'Data is {days_stale} days old' if days_stale > 30 else None
            }
        except:
            return {'is_stale': True, 'days_stale': None, 'last_update': updated_at_str, 'warning': 'Unable to parse date'}

def create_client_from_env() -> WattWiseClient:
    from dotenv import load_dotenv
    load_dotenv()
    
    base_url = os.getenv('WATTWISE_BASE_URL', 'https://wattwise.ng/api')
    username = os.getenv('WATTWISE_USERNAME')
    password = os.getenv('WATTWISE_PASSWORD')
    xsrf_token = os.getenv('WATTWISE_XSRF_TOKEN')
    
    if not username or not password:
        raise ValueError('WATTWISE_USERNAME and WATTWISE_PASSWORD must be set in .env')
    
    return WattWiseClient(base_url, username, password, xsrf_token)

if __name__ == '__main__':
    client = create_client_from_env()
    
    print('Logging in...')
    if client.login():
        print('Login successful')
        
        print('\nFetching meter overview...')
        meter_data = client.get_meter_overview()
        if meter_data:
            print(f'Cumulative consumption: {meter_data.get("cumulative_total_consumption")} kWh')
            print(f'Residual amount: {meter_data.get("residual_amount")}')
            
            if 'updated_at' in meter_data:
                freshness = client.check_data_freshness(meter_data['updated_at'])
                print(f'Data freshness: {freshness}')
        else:
            print('Failed to fetch meter overview')
    else:
        print('Login failed')
