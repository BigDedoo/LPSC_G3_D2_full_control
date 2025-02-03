# logging_config.py
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,  # change to INFO in production
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
