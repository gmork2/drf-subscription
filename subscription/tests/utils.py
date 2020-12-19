import logging
from pprint import pprint
import os
from typing import Optional, List

logger = logging.getLogger(__name__)

DUMMY_DOTTED_PATH = 'subscription.tests.utils.dummy'


def dummy(*args, **kwargs) -> None:
    """
    Set this function as your resource callback.
    """
    logger.info(f'kwargs: {kwargs}')
    pprint(kwargs)


def split_path(path: str, items: List[str]) -> Optional[List[str]]:
    if path:
        head, tail = os.path.split(path)
        if tail:
            items.insert(0, tail)
            split_path(head, items)
        return items
