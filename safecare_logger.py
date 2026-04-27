import logging
import os

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def get_logger(name: str = "safecare") -> logging.Logger:
    """Return a named logger that writes to both the console and logs/safecare.log."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    os.makedirs(_LOG_DIR, exist_ok=True)
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(os.path.join(_LOG_DIR, "safecare.log"), encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger
