import logging

logger = logging.getLogger(__name__)


def dummy(*args, **kwargs) -> None:
    """
    Set this function as your resource callback.
    """
    logger.info(f'kwargs: {kwargs}')
