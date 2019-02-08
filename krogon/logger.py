import logging


class Logger:
    def __init__(self, name: str):
        self.name = name

    def add_prefix(self, suffix):
        return Logger(self.name + ':' + suffix)

    def debug(self, message):
        self.log('debug', message)

    def error(self, message):
        self.log('error', message)

    def warn(self, message):
        self.log('warn', message)

    def info(self, message):
        self.log('info', message)

    def log(self, level, message):
        # logging.log(level, self.name + ':' + message)
        print(self.name + ', LEVEL: ' + level + ', ' + message)
