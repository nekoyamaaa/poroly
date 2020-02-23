import os
import string
import random
import time

import requests

token = os.environ.get('BACKEND_SECRET')

pool = string.ascii_lowercase + " "
def random_name(length=20, fixed=False):
    if not fixed:
        length = random.randint(2, length)
    return ''.join([random.choice(pool) for i in range(length)])

def random_id(length=7, fixed=True):
    if not fixed:
        length = random.randint(2, length)
    return ''.join([random.choice(string.digits) for i in range(length)])

guilds = []

for _ in range(5):
    guilds.append({'id': random_id(48), 'name': random_name(32)})

types = ['ミド', 'ムム', 'マキュ']
url = f"http://127.0.0.1:{os.environ.get('PORT', 8000)}/party"

while True:
    data = {
        'id': random_id(),
        'time': int(time.time()),
        'message': random_name(),
        'owner': {
            'id': random_id(20, False),
            'name': random_name(32).upper(),
        },
        'guild': random.choice(guilds),
        'type': random.choice(types)
    }

    response = requests.post(url, json=data, headers={'X-Authorization-Token': token})
    print(response.status_code, response.reason)
    try:
        print(response.json())
    except Exception as ex:
        print(ex.__class__.__name__, ex)
        print(response.text[0:500])
    time.sleep(5)
