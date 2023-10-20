from __future__ import annotations
from typing import TYPE_CHECKING

from weakref import ref

if TYPE_CHECKING:
    from core.account import PartialEpicAccount, FullEpicAccount

    MaybeAccount = PartialEpicAccount | FullEpicAccount | None


class BaseEntity:

    def __init__(
            self,
            account: MaybeAccount,
            item_id: str,
            template_id: str
    ) -> None:
        try:
            self._account = ref(account)
        except TypeError:
            self._account = lambda: None

        self.item_id: str = item_id
        self.template_id: str = template_id

    @property
    def account(self) -> MaybeAccount:
        return self._account()
