import sys
from loguru import logger
from config import APP_ENV

logger.remove()

if APP_ENV == "development":
    logger.add(sys.stderr, level="DEBUG", colorize=True,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
else:
    logger.add(sys.stderr, level="INFO", colorize=False,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}")

logger.add("logs/app.log", level="INFO", rotation="10 MB", retention="30 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}")
