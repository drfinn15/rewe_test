from dataclasses import dataclass, replace
from datetime import datetime
from functools import cached_property
from collections import ChainMap
from typing import Callable, Dict, Iterator, List, Optional, TypeVar

from viktualien.ean import EAN

R = TypeVar("R")  # pylint: disable=invalid-name
S = TypeVar("S", int, float, str)  # pylint: disable=invalid-name

# Information über ein beestimmtes Produkt, bspw. Kategorie und EAN
@dataclass(frozen=True)
class ProductInfo:
    ean: EAN
    name: str
    category_id: str
    product_id: str


# Einzelne Bestellzeile, d.h. Produkt mit Preis und Anzahl
@dataclass(frozen=True)
class LineItem:
    product_id: str
    single_price: int
    quantity: int

    # Gesamtwert der Bestellzeile berechnen
    # Einzelpreis * Anzahl
    @cached_property
    def total_price(self) -> int:
        return self.quantity * self.single_price


# Sammlung von Bestellzeilen
@dataclass(frozen=True)
class LineItems:
    line_items: List[LineItem]

    # Gesamt-Bestellwert berechnen
    @cached_property
    def sum(self) -> int:
        return sum([item.total_price for item in self.line_items])

    def aggregate(
        self, func: Callable[[LineItem], R], reduce: Callable[[R, R], R]
    ) -> Dict[str, R]:
        result: Dict[str, R] = {}
        for line_item in self:
            val = func(line_item)
            if line_item.product_id in result:
                result[line_item.product_id] = reduce(val, result[line_item.product_id])
            else:
                result[line_item.product_id] = val
        return result

    # Aggregieren der Bestellzeilen nach einer bestimmten Metrik
    # Beispiel:
    #   line_items.aggregate_add(lambda item: item.total_price)
    # ... liefert ein Dictionary, welches Produkt-ID auf Bestellbetrag abbildet
    def aggregate_add(self, func: Callable[[LineItem], S]) -> Dict[str, S]:
        return self.aggregate(func, lambda x, y: x + y)

    # Methode zum Iterieren:
    # for line_item in line_items: ...
    def __iter__(self) -> Iterator[LineItem]:
        return iter(self.line_items)

    # Methode um Anzahl der Bestellzeilen zu erhalten:
    # len(line_items)
    def __len__(self) -> int:
        return len(self.line_items)


# Bestellungen, d.h. Sammlung von Bestellzeilen, weitergehende Produktinformationen und Datum
@dataclass(frozen=True)
class Order:
    date: datetime
    line_items: LineItems
    order_id: str
    product_infos: Dict[str, ProductInfo]

    def __post_init__(self):
        for line_item in self.line_items:
            assert line_item.product_id in self.product_infos
        for product_id, product_info in self.product_infos.items():
            assert product_info.product_id == product_id

    # Gesamt-Bestellwert berechnen
    @cached_property
    def value(self) -> int:
        return self.line_items.sum

    # Ersetzt die Produktinfos, wenn bspw. genauere Kategorieninformationen vorliegen
    def update_infos(
        self, func: Callable[[str, ProductInfo], Optional[ProductInfo]]
    ) -> "Order":
        new_product_infos: Dict[str, ProductInfo] = {}
        for name, old_product_info in self.product_infos.items():
            new_product_infos[name] = func(name, old_product_info) or old_product_info
        return replace(self, product_infos=new_product_infos)


# Sammlung von Bestellungen
@dataclass(frozen=True)
class Orders:
    orders: List[Order]

    # Gesamt-Bestellwert berechnen
    @cached_property
    def value(self) -> int:
        return sum([order.value for order in self.orders])

    # Durchschnittlichen Bestellwert berechnen
    @cached_property
    def average_value(self) -> Optional[float]:
        if len(self) > 0:
            return self.value / len(self)
        return None

    # Methode zum Iterieren:
    # for order in orders: ...
    def __iter__(self) -> Iterator[Order]:
        return iter(self.orders)

    # Methode um Anzahl der Bestellungen zu erhalten:
    # len(orders)
    def __len__(self) -> int:
        return len(self.orders)

    # Sammelt alle Bestellzeilen aller Bestellungen in einem einzigen LineItems-Objekt
    @cached_property
    def all_line_items(self) -> LineItems:
        return LineItems([item for order in self for item in order.line_items])

    # Sammelt alle Produktinfos aller Bestellungen in einem einzigen Dictionary
    @cached_property
    def all_product_infos(self) -> Dict[str, ProductInfo]:
        return dict(ChainMap(*[order.product_infos for order in self]))

    # Ersetzt die Produktinfos, wenn bspw. genauere Kategorieninformationen vorliegen
    def update_infos(
        self, func: Callable[[str, ProductInfo], Optional[ProductInfo]]
    ) -> "Orders":
        return replace(self, orders=[order.update_infos(func) for order in self])
