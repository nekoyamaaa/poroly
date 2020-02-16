import os
import secrets
import logging
import logging.config
import logging.handlers

class Config:
    """Configurations for flask app.
    See .env.example for details about environ values"""
    DEBUG = os.environ.get('DEBUG', False)
    TESTING = False
    REDIS_URL = os.environ['REDIS_URL']

    # Deliver javascripts from jscdn.com
    BOARD_USE_JSCDN = False

    # each room will be automatically removed after this seconds
    BOARD_EXPIRE_SEC = 120

    BOARD_BACKEND_SECRET = os.environ.get('BACKEND_SECRET')
    BOARD_PLUGIN = os.environ.get('BOARD_PLUGIN', 'plugins.example')

    DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
    DISCORD_MASTER = os.environ.get('DISCORD_MASTER')

class ProductionConfig(Config):
    BOARD_USE_JSCDN = True

class DevelopmentConfig(Config):
    DEBUG = True

    BOARD_EXPIRE_SEC = 60

class TestingConfig(Config):
    TESTING = True

    BOARD_EXPIRE_SEC = 10

options = {
    'production': ProductionConfig,
    'development': DevelopmentConfig,
    'test': TestingConfig,
}

def get_option(env):
    return options[env]

def is_gunicorn():
    return 'gunicorn' in os.environ.get('SERVER_SOFTWARE', '')

def is_heroku():
    """very buggy check.  Use only for non-critical actions."""
    return 'FOREMAN_WORKER_NAME' in os.environ

def flask_logging_config():
    stream = 'ext://flask.logging.wsgi_errors_stream'

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            # access log contains timestamp in its message
            'access_log': {
                'format': ' ACCESS %(message)s',
            },
            'default': {
                'format': '%(asctime)s %(levelname)7s %(name)s: %(message)s',
            },
            'notime': {
                'format': '%(levelname)7s %(name)s: %(message)s',
            },
        },
        'handlers': {
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': stream,
                'formatter': 'notime' if is_heroku() else 'default'
            },
            'access_log': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'stream': stream,
                'formatter': 'access_log'
            },
        },
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi']
        },
        'loggers': {
            'werkzeug': {
                'level': 'INFO',
                'handlers': ['access_log'],
                'propagate': False
            },
            # In gunicorn, the logger 'geventwebsocket.handler' outputs
            # access log as INFO but they remove all handlers on initialization.
            # At last, I decided to ignore all access log because I have no
            # interests in access log about static files.
            # Might be rewrite when someone uses POST backend frequently.
            'geventwebsocket': {
                'level': 'ERROR',
            }
        }
    })
