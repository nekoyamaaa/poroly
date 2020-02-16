import os
import string
import random
import time

import requests

token = os.environ.get('BACKEND_SECRET')

opts = {}

pool = string.ascii_lowercase + " "
def random_name(length=20):
    return ''.join([random.choice(pool) for i in range(length)])

data = {
    'id': opts.get('id', '%07d' % random.randint(0, 9999999)),
    'time': opts.get('time') or int(time.time()),
    'message': opts.get('message') or random_name(),
    'owner': {'id': '%07d' % random.randint(0, 9999999), 'name': opts.get('owner') or random_name(10).upper(),},
    'guild': random_name(10)
}

response = requests.post('http://127.0.0.1:8000/party', json=data, headers={'X-Authorization-Token': token})
print(response.status_code, response.reason)
try:
    print(response.json())
except Exception as ex:
    print(ex.__class__.__name__, ex)
    print(response.text[0:500])
