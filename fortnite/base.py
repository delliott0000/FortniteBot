from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any
    from core.account import PartialEpicAccount, FullEpicAccount

    Account = PartialEpicAccount | FullEpicAccount
    Attributes = dict[str, Any]
