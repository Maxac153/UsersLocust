import logging


class LogConfig:
    logger = logging.getLogger('logger')
    logger.setLevel('INFO')
    file = logging.FileHandler(filename='output/logs/logs.log')
    file.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    logger.addHandler(file)
    logger.propagate = False


logger = LogConfig.logger