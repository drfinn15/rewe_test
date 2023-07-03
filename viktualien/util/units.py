import re
from enum import Enum
from typing import Optional
from dataclasses import dataclass


# Regulärer Ausdruck, der Zahlangaben in (Kilo-)Gramm und (Milli)Liter
# korrekt, auch wenn ihnen ein Multiplikator wie "6x" voransteht.
_unit_re = re.compile("""(([0-9]+) ?x ?)?(([0-9]+,)?[0-9]+) ?(g|kg|l|L|ml)""")


# Enum mit zwei Werten für Gewichts- und Volumenangaben und einer Methode, um
# sie als "g" bzw. "ml" in Strings zu konvertieren.
class UnitType(Enum):
    WEIGHT = 1
    VOLUME = 2

    def __str__(self):
        if self == UnitType.WEIGHT:
            return "g"
        return "ml"


# Die unterstützten Typen (Art der Einheit und Multiplikator)
_raw_types = {
    "g": (UnitType.WEIGHT, 1),
    "kg": (UnitType.WEIGHT, 1000),
    "ml": (UnitType.VOLUME, 1),
    "l": (UnitType.VOLUME, 1000),
    "L": (UnitType.VOLUME, 1000),
}


# Die eigentliche Unit-Klasse.
@dataclass(frozen=True)
class Unit:
    # Volumen- oder Gewichtseinheit?
    unit_type: UnitType
    # Zahlenwert der Angabe
    value: int

    # Konvertierung in String (Zahlenwert gefolgt von der Einheit)
    def __str__(self):
        return str(self.value) + str(self.unit_type)

    # Werte mit dem gleichen Einheitentyp können addiert werden.
    def __add__(self, other: "Unit") -> "Unit":
        assert self.unit_type == other.unit_type
        return Unit(self.unit_type, self.value + other.value)

    # Werte können mit einer Ganzzahl multipliziert werden
    def __mul__(self, other: int) -> "Unit":
        return Unit(self.unit_type, self.value * other)

    # Werte mit dem gleichen Einheitentyp können verglichen werden.
    def __lt__(self, other):
        assert self.unit_type == other.unit_type
        return self.value < other.value

    def __le__(self, other):
        assert self.unit_type == other.unit_type
        return self.value <= other.value

    def __gt__(self, other):
        assert self.unit_type == other.unit_type
        return self.value > other.value

    def __ge__(self, other):
        assert self.unit_type == other.unit_type
        return self.value >= other.value

    # Methode um Einheitsangaben aus Produktnamen zu extrahieren. (Wendet den
    # regulären Ausdruck an und gibt bei Erfolg eine Unit-Instanz zurück, sonst
    # None.
    @staticmethod
    def parse(product_name: str) -> Optional["Unit"]:
        # Regex anwenden
        match = _unit_re.search(product_name)
        if match:
            # Bei Treffer die Werte der Gruppen im Ausdrück extrahieren
            multiplier, raw_single, raw_type = match.group(2, 3, 5)

            # Wenn keine Multiplikator (wie "6x") gefunden wurde, wird
            # der Wert 1 verwendet
            if multiplier is None:
                multiplier = 1

            # Im Zahlennwert Kommata durch Punkte ersetzen (deutsche Angabe vs.
            # englische Konvention) und den Zahlenwert mit dem Faktor der
            # Typangabe malnehmen (e.g. "kg" bedeutet "Gramm mit Faktor 1000")
            unit_type, unit_factor = _raw_types[raw_type]
            single = float(raw_single.replace(",", "."))
            value = int(int(multiplier) * unit_factor * single)
            return Unit(unit_type, value)

        # Bei Nichttreffer None zurückgeben.
        return None
