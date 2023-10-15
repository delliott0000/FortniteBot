from __future__ import annotations
from typing import TYPE_CHECKING

from typing import TypedDict
from datetime import datetime

if TYPE_CHECKING:
    from core.account import PartialEpicAccount


class PartialAccountCacheEntry(TypedDict):

    account: PartialEpicAccount
    expires: datetime
