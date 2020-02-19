"""Run only discord bot"""
import os

from my.discordmod import setup_logging
import config

import board
from board.bot import Bot
from board.manager import BoardManager

BOT_LABEL = 'board'
REDIS_URL = os.environ['REDIS_URL']
DEBUG = os.environ.get('DEBUG', False)

app_config = {
    'board': {
        'url': os.environ.get('BOARD_URL'),
        'plugin': os.environ.get('BOARD_PLUGIN', 'plugins.example'),
    },
    'discord': {
        'token':  os.environ['DISCORD_TOKEN'],
        'master': os.environ.get('DISCORD_MASTER')
    }
}

plugin = board.check_plugin(app_config['board']['plugin'])

logger = setup_logging(BOT_LABEL)

bot = Bot(__file__, debug=DEBUG, logger=logger, name=BOT_LABEL)
bot.load_plugin(plugin)
bot.master = app_config['discord']['master']

bot.manager = BoardManager(REDIS_URL, plugin.Validator, app_config['board'])
bot.board_url = app_config['board']['url']

bot.run(app_config['discord']['token'])
