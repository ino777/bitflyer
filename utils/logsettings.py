import logging

from config import config

def getLogger(name, stream_level=config.Config.log_stream_level, log_file=config.Config.system_log_file, file_level=config.Config.system_log_file_level):
    logger = logging.getLogger(name)
    ''' Logger Config '''
    handler_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s')

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_level)
    stream_handler.setFormatter(handler_format)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(file_level)
    file_handler.setFormatter(handler_format)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    logger.setLevel(min(stream_handler.level, file_handler.level))

    return logger