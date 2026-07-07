import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import config


def setup_logger():
    if not os.path.exists(config.LOG_DIR):
        os.makedirs(config.LOG_DIR)

    log_file = os.path.join(
        config.LOG_DIR,
        f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logger = logging.getLogger("discord_auto")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


logger = setup_logger()


def info(msg):
    logger.info(msg)


def debug(msg):
    logger.debug(msg)


def warning(msg):
    logger.warning(msg)


def error(msg):
    logger.error(msg)


def success(msg):
    logger.info(f"[成功] {msg}")


def fail(msg):
    logger.warning(f"[失败] {msg}")