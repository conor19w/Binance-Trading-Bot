import logging
from datetime import datetime
import colorlog
from LiveTradingConfig import LOG_LEVEL, log_to_file
import os
import sys


def get_logger():
    # Create a logger and set its level to LOG_LEVEL
    log = logging.getLogger()
    log.setLevel(LOG_LEVEL)
    # Create a formatter with colorlog's ColoredFormatter
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s %(levelname)s: %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "bold_white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    if log_to_file:
        file_formatter = logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )
        # Get the current datetime
        current_datetime = datetime.now()
        # Format the datetime with underscores between elements
        formatted_datetime = current_datetime.strftime("%d_%m_%Y_%H_%M_%S")
        # Create a file handler and set the formatter
        file_handler = logging.FileHandler(f"Live_Trading_{formatted_datetime}.log")
        file_handler.setFormatter(file_formatter)
        log.addHandler(file_handler)

    # Create a console handler and set the formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    # Add the console handler to the logger
    log.addHandler(console_handler)
    return log


log = get_logger()

