import importlib

def check_plugin(modulename):
    plugin = importlib.import_module(modulename)

    # TODO: check type
    plugin.Validator
    plugin.Parser

    return plugin
