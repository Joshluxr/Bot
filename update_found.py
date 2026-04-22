#!/usr/bin/env python3
"""Download latest found.txt from GPU server to local HTTP server"""

import requests
import warnings
warnings.filterwarnings('ignore')

JUPYTER_URL = '74.48.140.178:25349'
TOKEN = 'afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7'
LOCAL_PATH = '/root/repo/address_server/found.txt'

def update():
    path = 'workspace/Bot/vanitysearch_analysis/found.txt'
    url = f'https://{JUPYTER_URL}/api/contents/{path}?content=1&format=text'

    print('Downloading latest found.txt from GPU server...')
    response = requests.get(url, headers={'Authorization': f'token {TOKEN}'}, verify=False, timeout=180)

    if response.status_code == 200:
        data = response.json()
        content = data.get('content', '')

        with open(LOCAL_PATH, 'w') as f:
            f.write(content)

        addresses = content.count('PubAddress')
        print(f'Updated: {len(content):,} bytes')
        print(f'Total addresses: {addresses:,}')
        print(f'File available at: http://localhost:8080/found.txt')
    else:
        print(f'Error: {response.status_code}')

if __name__ == '__main__':
    update()
