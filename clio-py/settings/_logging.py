import sys
import logging
import re

__format = "%(asctime)s [%(threadName)-14.14s] [%(levelname)-5.5s]  %(message)s"
__consoleHandler = logging.StreamHandler(sys.stdout)
__consoleHandler.setFormatter(logging.Formatter(__format))

__log = logging.getLogger()
__log.addHandler(__consoleHandler)
__log.setLevel(logging.INFO)


def set_process_pool_format():
    __consoleHandler.setFormatter(
        logging.Formatter("%(asctime)s [%(processName)-14.14s] [%(levelname)-5.5s]  %(message)s")
    )


def logger_exists(name: str, logger: logging.Logger = ...) -> bool:
    if logger is ...:
        logger = logging.Logger
    return name in logger.manager.loggerDict


def no_scan_logger(name: str, regex_replacements: list[tuple[str, str]] = ...) -> logging.Logger:
    if logger_exists(name) and logging.getLogger(name).propagate:
        raise Exception(f"Logger {name} already exists. Typically no scan loggers use the suffix `no_scan`.")
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RegexReplaceFormatter(__format, regex_replacements=regex_replacements))

    logger.propagate = False
    logger.addHandler(handler)
    return logger


class RegexReplaceFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, regex_replacements=...):
        super().__init__(fmt, datefmt)
        if regex_replacements is ...:
            regex_replacements = [
                (r"(ERROR)", "ERR_R"),
                (r"(Exception)", "Excepti_n"),
            ]
        self._compiled_patterns = []
        for pattern, replacement, *flags in regex_replacements or []:
            flag_value = flags if flags else (re.IGNORECASE | re.MULTILINE)
            self._compiled_patterns.append((re.compile(pattern, flag_value), replacement))

    def format(self, record):
        formatted_msg = super().format(record)

        for pattern, replacement in self._compiled_patterns:
            formatted_msg = pattern.sub(replacement, formatted_msg)

        return formatted_msg
