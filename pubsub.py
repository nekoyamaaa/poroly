import gevent
from flask.helpers import url_for
from flask import Flask, render_template, request, abort, make_response, jsonify
from flask_sockets import Sockets

import config
from board.manager import BoardManager
from board.server  import PubSubServer


config.flask_logging_config()


app = Flask(__name__)
app.config.from_object(config.get_option(app.env))
board_config = app.config.get_namespace('BOARD_')
app.logger.debug('Load %s config, debug mode: %s', app.env, app.debug)

try:
    from flask_cache_buster import CacheBuster
    cache_buster = CacheBuster()
    cache_buster.register_cache_buster(app)
except Exception as ex:
    app.logger.warning('Could not setup CacheBuster: %s', repr(ex))

proxy_fix_num = app.config.get('PROXY_FIX')
if proxy_fix_num > 0:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_fix_num, x_host=proxy_fix_num)
    app.logger.info('Set proxy_fix with %s', proxy_fix_num)
else:
    app.logger.info('PROXY_FIX was ignored')
del proxy_fix_num

manager = BoardManager(app.config['REDIS_URL'], board_config)
board_server = PubSubServer(app, manager)
SOCKET_PATH = '/room'

@app.route('/')
def frontend():
    opts = {
        'use_cdn': board_config.get('use_jscdn', False),
        'expire_sec': manager.expire_sec,
        'invite_url': app.config.get('DISCORD_INVITE_URL'),
    }
    socket_url = board_config.get('socket_url')
    if not socket_url and board_server.status == 'running':
        socket_url = url_for('fakesocketend', _external=True, _scheme='')

    if socket_url:
        opts['socket_url'] = socket_url
    else:
        app.logger.error('WebSocketServer is not running but socket_url is not configured.')
        if not app.debug:
            abort(503)

    return render_template(
        'index.html',
        **opts
    )

@app.route(SOCKET_PATH)
def fakesocketend():
    abort(406)

def backend():
    if board_server.backend_secret != request.headers.get('X-Authorization-Token'):
        abort(401)
    data = request.get_json()
    if not data:
        abort(400, 'Not a valid JSON')
    try:
        data = manager.validate(data)
        return manager.save(data)
    except ValueError as ex:
        app.logger.warning(str(ex))
        if ex.args:
            abort(400, ex.args[0])
        else:
            abort(400)
if board_server.backend_secret:
    app.logger.info('Open backdoor with %s...', board_server.backend_secret[:8])
    app.add_url_rule('/party', 'backend', backend, methods=['POST'])

@app.errorhandler(400)
def catcher(error):
    if request.is_json:
        response = make_response(jsonify({'error': error.description}), error.code)
    else:
        response = error
    return response

def socketend(ws, *args, **kwargs):
    """Handle WebSockets requests"""
    board_server.register(ws)
    board_server.send(ws, manager.get_all_as_json())

    while not ws.closed:
        # Context switch while `Backend.start` is running in the background.
        gevent.sleep(0.1)

if config.is_gunicorn():
    board_server.start()
    sockets = Sockets(app)
    sockets.add_url_rule(SOCKET_PATH, 'socketend', socketend)
else:
    app.logger.warning('WebSockets is not opened.')
