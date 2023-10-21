from __future__ import annotations
from typing import TYPE_CHECKING

from weakref import ref

if TYPE_CHECKING:
    from typing import Any
    from weakref import ReferenceType
    from core.account import PartialEpicAccount, FullEpicAccount

    Account = PartialEpicAccount | FullEpicAccount
    Attributes = dict[str, Any]


class AccountBoundMixin:

    def __init__(self, account: Account, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._account: ReferenceType[Account] = ref(account)

    @property
    def account(self) -> Account:
        return self._account()


class BaseEntity:

    __slots__ = (
        'item_id',
        'template_id',
        'raw_attributes'
    )

    def __init__(self, item_id: str, template_id: str, attributes: Attributes) -> None:
        self.item_id: str = item_id
        self.template_id: str = template_id
        self.raw_attributes: Attributes = attributes.copy()
