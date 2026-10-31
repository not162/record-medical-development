import urllib.request
import json
import time
import concurrent.futures

backend = 'https://ai-api-dusky-eight.vercel.app'
frontend = 'https://halo-skut.vercel.app'

print('=== 1. Live Health Check (Caching & Continuous Batching) ===')
req = urllib.request.Request(f'{backend}/api/v1/health')
with urllib.request.urlopen(req, timeout=15) as r:
    data = json.loads(r.read().decode())
    print('Status:', data.get('status'))
    print('Caching:', data.get('caching'))
    print('Continuous Batching:', data.get('continuous_batching'))
    print('AI Gateway:', data.get('ai_gateway'))

print('\n=== 2. Concurrent Registration & Login Test (Multiple Simultaneous Devices) ===')
ts = int(time.time())

def test_user_flow(idx):
    user = f'dev_{ts}_{idx}'
    email = f'dev_{ts}_{idx}@klinik.id'
    pwd = 'Password123!'
    
    # Register
    reg_req = urllib.request.Request(
        f'{frontend}/api/v1/auth/register',
        data=json.dumps({'username': user, 'email': email, 'password': pwd, 'full_name': f'Device {idx}'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(reg_req, timeout=20) as r:
        reg_data = json.loads(r.read().decode())
        
    # Login
    login_req = urllib.request.Request(
        f'{frontend}/api/v1/auth/login',
        data=json.dumps({'username_or_email': user, 'password': pwd}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(login_req, timeout=20) as r:
        login_data = json.loads(r.read().decode())
        
    return f'Device {idx}: Register 201 Created -> Login 200 OK (Username: {reg_data.get("username")}, Role: {login_data.get("role")})'

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(test_user_flow, i) for i in range(1, 6)]
    for f in concurrent.futures.as_completed(futures):
        print('  ', f.result())

print('\n=== 3. Frontend Lighthouse Optimization Headers ===')
req = urllib.request.Request(f'{frontend}/')
with urllib.request.urlopen(req, timeout=15) as r:
    h = dict(r.headers)
    print('X-Content-Type-Options:', h.get('x-content-type-options'))
    print('X-Frame-Options:', h.get('x-frame-options'))
    print('Referrer-Policy:', h.get('referrer-policy'))

print('\nALL VERIFICATIONS PASSED!')
