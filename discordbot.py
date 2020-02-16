"""Run only discord bot"""
import os

from my.discordmod import setup_logging
import config

import board

BOT_LABEL = 'board'

app_config = {
    'REDIS_URL':      os.environ['REDIS_URL'],
    'DEBUG':          os.environ.get('DEBUG', False),
    'BOARD_PLUGIN':   os.environ.get('BOARD_PLUGIN', 'plugins.example'),
    'DISCORD_TOKEN':  os.environ['DISCORD_TOKEN'],
    'DISCORD_MASTER': os.environ.get('DISCORD_MASTER')
}

debug = app_config['DEBUG']

Bot, BoardManager = board.load_plugin(app_config['BOARD_PLUGIN'])

logger = setup_logging(BOT_LABEL)

bot = Bot(__file__, debug=debug, logger=logger, name=BOT_LABEL)
bot.master = app_config.get('DISCORD_MASTER')

bot.manager = BoardManager(app_config, logger=logger)

bot.run(app_config['DISCORD_TOKEN'])
