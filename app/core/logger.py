import os
import logging
import logging.config
import yaml


with open('logger_config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)


def get_logger():
    """Get logger."""
    return logging.getLogger('root')


def cleanup_logger():
    try:
        path = 'logout.log'
        if os.path.exists(path):
            os.remove(path)
    finally:
        pass
