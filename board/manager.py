import calendar
import datetime
import json
import logging
import time
import importlib

import redis

from .exceptions import PluginError

class DefaultPlugin:
    def parse_content(self, content, *args, **kwargs):
        logging.getLogger('board.manager').error(
            'Parser is empty.  All messages will be ignored!'
        )
        return

    def report_for(self, action, obj=None):
        if obj is None:
            obj = {}
        if action == "saved" and obj.get('message'):
            return "`{}`として投稿しました".format(obj.get('message'))

    def validate(self, data, cleaned_by_others=None):
        logging.getLogger('board.manager').error(
            'Validator is empty.  All extended data will be ignored!'
        )
        return {}

class DefaultValidator:
    @staticmethod
    def validate(data, cleaned_by_others=None):
        """Expected data scheme.
        Text are silently trimmed if longer than maxlength.
        {
            'owner': {
                'id': (str) unique ID
                'name': (str, optional)
            }
            'time': (int or datetime)
            'guild': {
                'id': (str) unique ID
                'name': (str, optional)
            }
            'message': (str, optional)
        }
        """
        cleaned = {}

        # owner / guild: Based on discord specs
        max_length = {
            'owner': 32,
            'guild': 100,
            'message': 30,
        }
        for attr in ('owner', 'guild'):
            attr_id = data[attr]['id']
            if isinstance(attr_id, int):
                attr_id = str(attr_id)
            if not attr_id:
                raise ValueError('%s.id must not be empty.' % attr)
            cleaned[attr] = {'id': str(attr_id)}

            attr_displayname = data[attr].get('name')
            if attr_displayname:
                cleaned[attr]['name'] = str(attr_displayname)[0:max_length[attr]]

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
            cleaned['message'] = str(message)[0:max_length['message']]

        return cleaned

class BoardManager:
    CHANNEL = 'newroom'
    DEFAULT_CONFIG = {
        'expire_sec': 120,
        'prefix': 'room',
    }

    KEY_GLUE = ':'

    def __init__(self, redis_url, config, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.redis = redis.from_url(redis_url)
        try:
            self.redis.config_get('notify-keyspace-events')
            self.notifications_available = True
        except:
            self.notifications_available = False
        self.notifications_available = False
        self.config = dict(self.DEFAULT_CONFIG)
        if config:
            for k, v in config.items():
                if v:
                    # Do not override with None
                    self.config[k] = v

        self.validators = []
        self.add_validator(DefaultValidator)
        self.load_plugin(config['plugin'])

        self.expire_sec = self.config['expire_sec']
        self.prefix = self.config['prefix']

    def load_plugin(self, plugin):
        if isinstance(plugin, str):
            plugin = importlib.import_module(plugin)
        self._parser = plugin.Parser()
        self.add_validator(self._parser)
        if not plugin.__doc__:
            self.logger.warning('%s has no description.', plugin.__class__)
        self.description = plugin.__doc__
        self.logger.debug('Plugin %s loaded.', plugin.__class__)

    def add_validator(self, instance):
        if isinstance(instance, type):
            instance = instance()
        self.validators.append(instance)
        self.logger.debug('Validator %s added.', instance.__class__)

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
        try:
           data['id']
           data['owner']['id']
        except KeyError:
            raise PluginError('Required keys are missing.  It seems that Plugin removed them or did not handle them at all.')

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

        values = [str(v) if isinstance(v, int) else v for v in values]

        return self.KEY_GLUE.join(values)

    def split_key(self, key):
        result = {}
        _, result['owner'], result['room'] = key.split(self.KEY_GLUE)
        return result

    def validate(self, data):
        cleaned = {}
        for validator in self.validators:
            cleaned.update(validator.validate(data, cleaned))
        return cleaned

    @property
    def parser(self):
        return getattr(self, '_parser', None) or DefaultParser()

    def parse(self, content, *args, **kwargs):
        return self.parser.parse_content(content, *args, **kwargs)

    def report_for(self, action, obj=None):
        return self.parser.report_for(action, obj)

    @property
    def description(self):
        return (getattr(self, '_description', None) or "")

    @description.setter
    def description(self, value):
        self._description = str(value) if value else None

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
