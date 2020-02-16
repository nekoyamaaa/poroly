import calendar
import datetime
import json
import logging
import time

import redis

class BoardManager:
    CHANNEL = 'newroom'
    DEFAULT_CONFIG = {
        'expire_sec': 120,
        'prefix': 'room'
    }

    KEY_GLUE = ':'

    def __init__(self, config, logger=None):
        self.redis = redis.from_url(config.get('REDIS_URL'))
        try:
            self.redis.config_get('notify-keyspace-events')
            self.notifications_available = True
        except:
            self.notifications_available = False
        self.notifications_available = False
        self.config = {}
        for k, v in self.DEFAULT_CONFIG.items():
            self.config[k] = config.get('BOARD_'+k.upper()) or v
        self.logger = logger or logging.getLogger(__name__)
        self.expire_sec = self.config['expire_sec']
        self.prefix = self.config['prefix']

    def get_all(self):
        return [
            json.loads(value)
            for value in self.redis.mget(self.get_all_keys())
        ]

    def get_all_as_json(self):
        return json.dumps({'type': 'all', 'data': self.get_all()})

    def get_all_keys(self):
        return self.redis.keys(self.generate_key())

    def destroy(self, data):
        data = self.validate(data)
        keys = self.redis.keys(
            self.generate_key(data)
        )
        if keys:
            self.redis.delete(*keys)
            if not self.notifications_available:
                msg = json.dumps({'type': 'delete', 'data': [data]})
                self.redis.publish(self.CHANNEL, msg)

    def save(self, data):
        data = self.validate(data)
        owner_keys = self.redis.keys(
            self.generate_key(data, fields='owner')
        )
        if owner_keys:
            self.logger.debug("Owner has keys %s", repr(owner_keys))
            if not self.notifications_available:
                json_data = [
                    {'id': self.split_key(k)['room']}
                    for k in self._decode_message(owner_keys)
                ]
                msg = json.dumps({'type': 'delete', 'data': json_data})
                self.redis.publish(self.CHANNEL, msg)
            self.redis.delete(*owner_keys)

        key = self.generate_key(data)
        self.redis.set(key, json.dumps(data))
        self.redis.expire(key, self.expire_sec)
        msg = json.dumps({'type': 'partial', 'data': [data]})
        self.redis.publish(self.CHANNEL, msg)
        return msg

    def generate_key(self, data=None, fields=None):
        default = {'owner', 'room'}
        if not data and not fields:
            fields = set()
        elif fields is None:
            fields = default
        elif isinstance(fields, str):
            fields = [fields]

        values = [self.prefix]
        if 'owner' in fields:
            values.append(data['owner']['id'])
            if 'room' in fields:
                values.append(data['id'])
            else:
                values.append('*')
        else:
            values.append('*')

        return self.KEY_GLUE.join(values)

    def split_key(self, key):
        result = {}
        _, result['owner'], result['room'] = key.split(self.KEY_GLUE)
        return result

    def validate(self, data):
        """Expected data scheme.
        Text are silently trimmed if longer than maxlength.
        {
            'owner': {
                'id': (str) unique ID
                'name': (str, optional, maxlength=15)
            }
            'time': (int or datetime)
            'guild': (str, optional, maxlength=30)
            'message': (str, optional, maxlength=30)
        }
        """
        cleaned = {}

        cleaned['owner'] = {
            'id': str(data['owner']['id'])
        }
        if not cleaned['owner']['id']:
            raise ValueError('owner.id must not be empty.')
        owner_name = data['owner'].get('name')
        if owner_name:
            cleaned['owner']['name'] = str(owner_name)[0:15]

        if data['guild']:
            cleaned['guild'] = str(data['guild'])[0:30]

        time_data = data.get('time')
        if not time_data:
            time_data = time.time()
        elif isinstance(time_data, str):
            pass
        elif isinstance(time_data, datetime.datetime):
            if time_data.tzinfo:
                time_data = time_data.timestamp()
            else:
                time_data = calendar.timegm(time_data.utctimetuple())
        try:
            cleaned['time'] = int(time_data)
        except ValueError:
            raise ValueError('time is not a valid time') from None

        message = data.get('message')
        if message:
            cleaned['message'] = str(message)[0:30]

        if self.user_validate:
            cleaned.update(self.user_validate(data))

        return cleaned

    @staticmethod
    def _decode_message(message):
        if hasattr(message, 'items'):
            return {
                k: v.decode('utf-8') if hasattr(v, 'decode') else v
                for k, v in message.items()
            }
        else:
            return [
                v.decode('utf-8') if hasattr(v, 'decode') else v
                for v in message
            ]
