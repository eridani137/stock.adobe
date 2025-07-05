import logging

from colorlog import ColoredFormatter


def configure(logger: logging.Logger):
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        log_format = '%(log_color)s%(asctime)s %(message)s'
        colored_formatter = ColoredFormatter(
            log_format,
            datefmt="[%X]",
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            },
            secondary_log_colors={},
            style='%'
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(colored_formatter)

        logger.addHandler(console_handler)
