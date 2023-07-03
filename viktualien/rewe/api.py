import dataclasses
from datetime import datetime
import json
from typing import Dict, List, Optional

from treelib import Node, Tree

from viktualien.config import Config
from viktualien.ean import EAN
from viktualien.rewe import model
from viktualien.util import cached_http

# Kategorienbaum von der API laden und in Tree-Objekt konvertieren
def load_categories() -> Tree:
    response = cached_http.get("https://mobile-api.rewe.de/mobile/categories/")

    tree = Tree()
    root = tree.create_node(tag="REWE", identifier="__root__")

    def recurse(parent: Node, raw_tree) -> None:
        node = Node(tag=raw_tree["name"], identifier=raw_tree["id"])
        tree.add_node(node, parent)
        if "childCategories" in raw_tree:
            for child in raw_tree["childCategories"]:
                recurse(node, child)

    for child in json.loads(response)["topLevelCategories"]:
        recurse(root, child)

    return tree

# Basierend auf einem bekannten EAN-Code die API nach der Kategorie befragen
# Kann für ältere Produkte fehlschlagen, dann wird None zurückgeliefert
def lookup_category(categories: Tree, ean: EAN) -> Optional[str]:
    logger = Config.get().logger("rewe.api")

    try:
        response = cached_http.get(
            f"https://mobile-api.rewe.de/products/ean/{ean.code}"
        )
    except cached_http.HTTPError as err:
        logger.info("EAN lookup %s failed", ean.code, exc_info=err)
        return None

    raw = json.loads(response)["items"]

    if len(raw) > 1:
        logger.info("EAN lookup %s yielded %d results", ean.code, len(raw))

    raw = raw[0]

    if raw["ean"] != ean.code:
        logger.warning(
            "EAN mismatch, requested %s but received %s", ean.code, raw["ean"]
        )

    if "categoryIds" not in raw:
        logger.info("No category information provided for EAN %s", ean.code)
        return None

    category_id = raw["categoryIds"][-1]

    if categories.get_node(category_id) is None:
        logger.warning("Unknown category id %s for EAN %s", category_id, ean.code)
        return None

    return category_id


# In einem existierenden Bestellungsobjekt die Kategorien verfeinern
# Jedes Produkt hat bereits eine bekannte Oberkategorie.
# Pro Produkt fragen wir nach konkreteren Kategorien, falls diese verfügbar sind.
def narrow_categories_in(categories: Tree, orders: model.Orders) -> model.Orders:
    product_infos: Dict[str, model.ProductInfo] = {}
    for product_id, product_info in Config.get().meter(
        orders.all_product_infos.items()
    ):
        narrowed_id = lookup_category(categories, product_info.ean)
        if narrowed_id:
            product_infos[product_id] = dataclasses.replace(
                product_info, category_id=narrowed_id
            )

    return orders.update_infos(lambda name, _: product_infos.get(name))


# Verarbeiten der JSON-Daten und Aufbau eines strukturieren Bestellungsobjekts
def parse_order(raw_order, categories: Tree) -> model.Order:
    product_infos: Dict[str, model.ProductInfo] = {}

    def get_product_id(raw_line_item) -> str:
        product_id = raw_line_item["productId"]
        if product_id not in product_infos:
            category: Node = categories[
                raw_line_item["listing"]["_embedded"]["category"]["id"]
            ]
            product_infos[product_id] = model.ProductInfo(
                EAN(raw_line_item["gtin"]),
                raw_line_item["title"],
                category.identifier,
                product_id,
            )
        return product_id

    def parse_line_item(raw_line_item) -> Optional[model.LineItem]:
        if raw_line_item["lineItemType"] != "PRODUCT":
            return None

        return model.LineItem(
            get_product_id(raw_line_item),
            raw_line_item["price"],
            raw_line_item["quantity"],
        )

    def parse_sub_order(raw_sub_order) -> List[model.LineItem]:
        result: List[model.LineItem] = []
        for raw_line_item in raw_sub_order["lineItems"]:
            parsed = parse_line_item(raw_line_item)
            if parsed is not None:
                result.append(parsed)
        return result

    def parse_date(timestamp) -> datetime:
        return datetime.strptime(timestamp, "%Y%m%d%H%M")

    return model.Order(
        parse_date(raw_order["orderDate"]),
        model.LineItems(
            [
                line_item
                for sub_order in raw_order["subOrders"]
                for line_item in parse_sub_order(sub_order)
            ]
        ),
        raw_order["orderId"],
        product_infos,
    )
