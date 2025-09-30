# utils/logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "output")
os.makedirs(LOG_DIR, exist_ok=True)

def _build_logger() -> logging.Logger:
    lg = logging.getLogger("rpa-jusbrasil")
    if lg.handlers:              # evita duplicar handlers em reloads
        return lg
    lg.setLevel(LOG_LEVEL)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(LOG_LEVEL)
    sh.setFormatter(fmt)

    fh = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(fmt)

    # desabilitar saída no console
    # lg.addHandler(sh)
    lg.addHandler(fh)
    lg.propagate = False
    return lg

# >>> ESTE É O NOME QUE OS OUTROS MÓDULOS IMPORTAM <<<
logger = _build_logger()
