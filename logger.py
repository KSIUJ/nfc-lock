from systemd import journal
import logging
import uuid

class Logger:
    log = None

    def __init__(self):
        if self.log == None:
            logging.basicConfig(level=logging.INFO)
            self.log = logging.getLogger()
            #self.log.addHandler(journal.JournaldLogHandler())

    def getLog(self):
        return self.log