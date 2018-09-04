import logging

class SLogger:
    _logger = None

    def __init__(self, tag):
        if not SLogger._logger:
            SLogger._logger = logging.getLogger(tag)

    def __getattr__(self, attr):
        return getattr(self._logger, attr)
