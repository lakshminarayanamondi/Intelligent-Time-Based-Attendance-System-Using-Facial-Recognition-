import requests
import json

base_url = 'http://127.0.0.1:5000'

print('=== Testing Working Days API ===')

# Test 1: Set working days for February 2025
print('\n1. Testing /set_working_days...')
data = {
    'year': 2025,
    'month': 2,
    'days': ['2025-02-03', '2025-02-04', '2025-02-05', '2025-02-06', '2025-02-07']
}
r = requests.post(f'{base_url}/set_working_days', json=data)
print(f'Status: {r.status_code}')
print(f'Response: {r.json()}')

# Test 2: Get working days for February 2025
print('\n2. Testing /get_working_days...')
r = requests.get(f'{base_url}/get_working_days?year=2025&month=2')
print(f'Status: {r.status_code}')
result = r.json()
print(f'Status: {result["status"]}')
print(f'Month: {result["month_name"]} {result["year"]}')
print(f'Working days count: {len(result["working_days"])}')
print(f'Working days: {result["working_days"]}')

# Test 3: Test student login
print('\n3. Testing /login with student credentials...')
login_data = {'username': 'ganapathi', 'password': 'ganapathi_1'}
r = requests.post(f'{base_url}/login', json=login_data)
print(f'Status: {r.status_code}')
print(f'Response: {r.json()}')

# Test 4: Test student stats with working days
print('\n4. Testing /student_stats_working_days...')
r = requests.post(f'{base_url}/student_stats_working_days', json={'id': 1})
print(f'Status: {r.status_code}')
print(f'Response: {r.json()}')

print('\n=== All API Tests Complete ===')
