import logging

class Logger:
    log = None

    def __init__(self):
        if self.log == None:
            logging.basicConfig(level=logging.INFO)
            self.log = logging.getLogger()

    def getLog(self):
        return self.log
