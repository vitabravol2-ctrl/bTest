import logging
from pathlib import Path

from app.config import LOG_FILE


class QtLogHandler(logging.Handler):
    def __init__(self, sink) -> None:
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self.sink(self.format(record))


def setup_logging(gui_sink=None) -> logging.Logger:
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("btest")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    if gui_sink:
        qt_handler = QtLogHandler(gui_sink)
        qt_handler.setFormatter(fmt)
        logger.addHandler(qt_handler)

    return logger
