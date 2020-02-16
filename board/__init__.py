from .manager import BoardManager
from .bot import Bot

import importlib

def load_plugin(modulename):
    plugin = importlib.import_module(modulename)

    class PluggedBot(plugin.Parser, Bot):
        _description = plugin.__doc__

    class PluggedBoardManager(plugin.Validator, BoardManager):
        pass

    return (PluggedBot, PluggedBoardManager)
