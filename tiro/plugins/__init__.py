import logging

try:
    from .utinni import TiroTSPump
except ImportError:
    logging.warning("Utinni is not available. Please install Utinni first.")
