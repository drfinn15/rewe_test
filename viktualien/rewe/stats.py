from typing import Callable, Dict, Optional

from treelib import Tree

from viktualien.rewe.model import ProductInfo


def _loop(func: Callable[[], bool]):
    while func():
        pass


def _prune_zero(tree: Tree) -> bool:
    for node in tree.all_nodes():
        if node.data == 0:
            tree.remove_node(node.identifier)
            return True
    return False


def _prune_depth(tree: Tree, depth: int) -> bool:
    for node in tree.all_nodes():
        if tree.depth(node) > depth:
            tree.remove_node(node.identifier)
            return True
    return False


def _prune_single(tree: Tree) -> bool:
    for leaf in tree.leaves():
        parent = tree.parent(leaf.identifier)
        siblings = tree.children(parent.identifier)
        if len(siblings) == 1:
            tree.remove_node(leaf.identifier)
            return True
    return False


# Aggregation der Bestellhistorie anhand einer Metrik, bspw. Gesamtkosten
# Erhält als Eingabe:
# - Metrik (Zuordnung von Produkt-ID zu numerischem Wert)
# - Produktinformationen (zur Ermittlung von Kategorieinformationen)
# - Kategorienbaum
# - Flag ob Kategorien mit nur einem Kind zusammengefasst werden sollen
# - Maximale Tiefe des Resultatbaums
# Liefert zurück: Baum mit aggregierten Werten
def categories_metric(
    metric: Dict[str, int],
    infos: Dict[str, ProductInfo],
    categories: Tree,
    prune_single: bool = False,
    max_depth: Optional[int] = None,
) -> Tree:
    tree = Tree(categories, deep=True)

    for node in tree.all_nodes():
        node.data = 0

    for name, value in metric.items():
        node = tree[infos[name].category_id]
        while node:
            node.data += value
            node = tree.parent(node.identifier)

    _loop(lambda: _prune_zero(tree))

    if max_depth:
        max_depth_int: int = max_depth
        _loop(lambda: _prune_depth(tree, max_depth_int))

    if prune_single:
        _loop(lambda: _prune_single(tree))

    return tree
