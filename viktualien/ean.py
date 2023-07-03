from dataclasses import dataclass

import re

_ean_re = re.compile("([0-9]{8,8})|([0-9]{13,13})")


@dataclass(frozen=True)
class EAN:
    code: str

    def __post_init__(self):
        if not _ean_re.match(self.code):
            raise ValueError(f"{self.code} not a valid EAN")

    def is_dummy(self):
        return self.code.startswith("2")

    def __str__(self):
        dummy = "*" if self.is_dummy() else ""
        return dummy + self.code
