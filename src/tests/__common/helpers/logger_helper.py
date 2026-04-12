import logging
import os
from datetime import datetime
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class LoggerHelper:
    __LOG_LEVEL_MAP = {
        "DEBUG": DEBUG,
        "INFO": INFO,
        "WARNING": WARNING,
        "ERROR": ERROR,
        "CRITICAL": CRITICAL
    }

    @classmethod
    def setup_logger(
            cls,
            name: str = "locust_runner",
            max_bytes: Optional[int] = 3_145_728,
            backup_count: int = 3,
            date_now: str = datetime.now().strftime("%Y-%m-%d"),
            date_time_now: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ) -> logging.Logger:
        log_file = f"output/logs/{date_now}/{date_time_now}/{name}.log"
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(name)
        logger.setLevel(cls.__LOG_LEVEL_MAP.get(os.getenv("LOG_LEVEL", "INFO").upper(), INFO))
        logger.propagate = False

        if logger.handlers:
            return logger

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(threadName)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        if max_bytes:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8"
            )
        else:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")

        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.info(
            "Logger Initialized. File: %s (Rotation: %s Bytes, %s Backups)",
            log_file, max_bytes or "disabled", backup_count
        )

        return logger
