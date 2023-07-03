from plotly import graph_objects as go
from treelib import Tree

# Erzeugen eines Plotly-Graphens für einen Baum mit Statistiken
def treechart(tree: Tree) -> go.Figure:
    ids = []
    labels = []
    values = []
    parents = []

    for node in tree.all_nodes():
        ids.append(node.identifier)
        labels.append(node.tag)
        values.append(node.data)
        if node.is_root():
            parents.append("")
        else:
            parents.append(tree.parent(node.identifier).identifier)

    return go.Figure(
        go.Treemap(
            ids=ids, labels=labels, values=values, parents=parents, branchvalues="total"
        )
    )
