import sys
import pathlib
from jinja2 import Environment

APP_ROOT = pathlib.Path(__file__, '../../').resolve()
sys.path.append(str(APP_ROOT))

from config import ProductionConfig

def url_for(endpoint, filename=None):
    if endpoint != 'static' or not filename:
        raise ValueError('mock cannot handle url for {!r}'.format(endpoint))
    return f'static/{filename}'

ctx = {
    'use_cdn':    ProductionConfig.BOARD_USE_JSCDN,
    'socket_url': ProductionConfig.BOARD_SOCKET_URL,
    'invite_url': ProductionConfig.DISCORD_INVITE_URL,
    'expire_sec': ProductionConfig.BOARD_EXPIRE_SEC,
    'url_for':    url_for
}

jenv = Environment(trim_blocks=True, lstrip_blocks=True)

if __name__ == '__main__':
    for key in ['invite_url', 'socket_url']:
        if not ctx[key]:
            raise ValueError('missing configuration: {!r}'.format(key))

    if sys.stdin.isatty():
        from subprocess import run, PIPE
        source = run(
            ['git', 'show', 'master:templates/index.html'],
            capture_output=True, text=True
        ).stdout
    else:
        source = sys.stdin.read()

    template = jenv.from_string(source)
    print(template.render(ctx))
