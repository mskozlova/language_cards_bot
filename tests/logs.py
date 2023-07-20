import logging


log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 
logging.basicConfig(format=log_format, level=logging.INFO)

for logger in logging.Logger.manager.loggerDict.values():
    logger.disabled = True

logger = logging.getLogger("TestingLogger")


def logged_test(func):
    def wrapper(*args, **kwargs):
        logger.info(f"Running test case {func.__name__.upper()}...")
        func(*args, **kwargs)
        logger.info("")
    return wrapper
