import json
import logging

import gevent
from geventwebsocket.exceptions import WebSocketError

class PubSubServer:
    """Interface for registering and updating WebSocket clients."""

    def __init__(self, app, manager, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.backend_secret = app.config.get('BOARD_BACKEND_SECRET')
        self.manager = manager
        self.clients = list()
        if self.manager.notifications_available:
            self.manager.redis.config_set('notify-keyspace-events', 'Egx')

        self.pubsub = self.manager.redis.pubsub()
        self.pubsub.psubscribe(**{
            '__keyevent@0__:*': self.keyevent_handler,
            self.manager.CHANNEL: self.newroom_handler,
        })
        self.pubsub_thread = None
        self.status = 'initial'

    def log_socket(self, level, prefix, ws):
        """Leave log message about a WebSocket client"""
        if not self.logger.isEnabledFor(level):
            return

        if ws.environ:
            info = []
            for attr in ['REMOTE_ADDR', 'HTTP_ORIGIN', 'HTTP_USER_AGENT']:
                value = ws.environ.get(attr)
                if not value:
                    info.append("-")
                elif " " in value:
                    info.append(f'"{value}"')
                else:
                    info.append(value)
            info = " ".join(info)
        else:
            info = "Unknown"
        self.logger.log(level, '%s %s', prefix, info)

    def register(self, client):
        """Register a WebSocket connection for Redis updates."""
        self.log_socket(logging.INFO, 'New client', client)
        self.clients.append(client)

    def send(self, client, data):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        try:
            client.send(data)
        except WebSocketError:
            self.log_socket(logging.DEBUG, "WebSocketError", client)
            try:
                client.close()
                self.clients.remove(client)
            except:
                # Already removed
                pass
        except:
            # TODO: Gather error examples and add better handling
            self.logger.error('Could not send data to %s', client, exc_info=True)

    def send_all(self, data):
        for client in self.clients:
            gevent.spawn(self.send, client, data)

    def newroom_handler(self, message):
        message = self.manager._decode_message(message)
        self.send_all(message.get('data'))

    def keyevent_handler(self, message):
        message = self.manager._decode_message(message)
        self.logger.debug('Handler %s', message)
        # Examples
        # ('type' == b'pmessage', 'pattern == PATTERN)
        # channel,data
        # "__keyevent@0__:del","room:2955926"
        # "__keyevent@0__:expire","room:6457465"
        # "__keyevent@0__:expired","room:6457465"
        #
        # Even if multiple keys are deleted at once (DEL key1 key2)
        # messages are sent separatedly

        channel = message.get('channel')
        data_type = None

        key = message.get('data')
        command = channel.split(':')[-1]
        if command in ['expired', 'del']:
            data_type = 'delete'
            data = [{'id': self.manager.split_key(key)['room']}]
        elif command in ['expire', 'set']:
            return

        if not data_type:
            self.logger.debug('No action for %s', channel)
            return
        msg = json.dumps({'type': data_type, 'data': data})

        self.send_all(msg)

    def start(self):
        self.status = 'running'
        self.pubsub_thread = self.pubsub.run_in_thread(sleep_time=1)
