from __future__ import annotations
from typing import TYPE_CHECKING

from weakref import ref
from abc import ABC

if TYPE_CHECKING:
    from weakref import ReferenceType

    from resources.extras import Account, Attributes


class AccountBoundMixin(ABC):

    __slots__ = ()

    def __init__(self, account: Account, item_id: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._account: ReferenceType[Account] = ref(account)
        self.item_id: str = item_id

    def __hash__(self) -> int:
        return hash(self.item_id)

    def __eq__(self, other: AccountBoundMixin) -> bool:
        return isinstance(other, AccountBoundMixin) and self.item_id == other.item_id

    @property
    def account(self) -> Account:
        return self._account()


class BaseEntity(ABC):

    __slots__ = (
        'template_id',
        'raw_attributes'
    )

    def __init__(self, template_id: str, attributes: Attributes) -> None:
        self.template_id: str = template_id
        self.raw_attributes: Attributes = attributes.copy()
