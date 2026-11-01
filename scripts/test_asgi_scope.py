import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("services/ai-api"))

from api.index import app as vercel_app

async def test_case(root_path, qs):
    scope = {
        'type': 'http',
        'http_version': '1.1',
        'method': 'GET',
        'path': '/api/index',
        'raw_path': b'/api/index',
        'query_string': qs.encode('latin1'),
        'headers': [(b'host', b'localhost')],
        'root_path': root_path,
        'client': ('127.0.0.1', 12345),
        'server': ('127.0.0.1', 80),
    }
    status_code = None
    body_chunks = []
    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}
    async def send(msg):
        nonlocal status_code
        if msg['type'] == 'http.response.start':
            status_code = msg['status']
        elif msg['type'] == 'http.response.body':
            body_chunks.append(msg.get('body', b''))
    await vercel_app(scope, receive, send)
    print(f"root_path={root_path!r}, qs={qs!r} -> status={status_code}, body={b''.join(body_chunks).decode()[:80]}")

async def main():
    await test_case('/api/index', '__vercel_path=/health')
    await test_case('', '__vercel_path=/health')
    await test_case('/api', '__vercel_path=/api/v1/auth/login')

if __name__ == '__main__':
    asyncio.run(main())
