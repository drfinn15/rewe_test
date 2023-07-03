from logging import StreamHandler, LogRecord

from tqdm import tqdm

# Log Handler für TQDM, damit Logausgaben sich nicht mit Fortschrittsbalken mischen
class TqdmHandler(StreamHandler):
    def __init__(self):
        StreamHandler.__init__(self)

    def emit(self, record: LogRecord):
        msg = self.format(record)
        tqdm.write(msg)
