import logging
import logging.config
from pathlib import Path
import yaml


def setup_logging() -> None:
    """
    Initialize logging from YAML.

    - Always logs to stdout (console handler).
    - Optionally adjusts levels based on environment:
        - development: root/app at DEBUG
        - production (or anything else): root/app at INFO
    """
    with open(Path("logger_config.yaml"), "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["root"]["level"] = config["root"].get("level", "INFO")
    if "app" in config.get("loggers", {}):
        config["loggers"]["app"]["level"] = config["loggers"]["app"].get("level", "INFO")

    logging.config.dictConfig(config)

    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.access").propagate = False
    
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("openai._base_client").setLevel(logging.INFO)


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Small helper around logging.getLogger.

    Recommended usage in modules:
        logger = get_logger(__name__)
    """
    if name is None:
        name = "app"
    return logging.getLogger(name)
