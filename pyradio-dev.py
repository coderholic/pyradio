import logging
import pyradio.main

PATTERN = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def configureLogger():
    logger = logging.getLogger("pyradio.player")
    logger.setLevel(logging.DEBUG)

    # Handler
    fh = logging.FileHandler("pyradio.log")
    fh.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(PATTERN)

    # add formatter to ch
    fh.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(fh)


if __name__ == "__main__":
    configureLogger()
    pyradio.main.shell()
