class BoardException(Exception):
    pass

class PluginError(BoardException):
    """Exception when plugin has an invalid behavior"""
    pass
