from dataclasses import dataclass
from core import ToDict, Keyed, Key, Stamped, DttmLike


@dataclass
class Ticket(Stamped, Keyed, ToDict):
    id: str
    group: str
    message: str
    open: bool
    acknowledged: bool
    owner: str
    created_dttm: DttmLike

    def key(self) -> Key:
        return Key(self.id)
