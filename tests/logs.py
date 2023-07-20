import logging


log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 
logging.basicConfig(format=log_format, level=logging.INFO)

for logger in logging.Logger.manager.loggerDict.values():
    logger.disabled = True

logger = logging.getLogger("TestingLogger")
