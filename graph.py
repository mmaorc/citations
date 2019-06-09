import urllib.request
from pathlib import Path
import json
import argparse
import os
import networkx as nx
import plotly
import plotly.graph_objs as go
import numpy as np
from networkx.drawing.nx_agraph import write_dot, graphviz_layout



def get_paper_json(paper_id):
    paper_info_filepath = rf"papers/{paper_id}.json"
    if Path(paper_info_filepath).exists():
        contents = Path(paper_info_filepath).read_text()
    else:
        get_url = f"https://api.semanticscholar.org/v1/paper/{paper_id}"
        contents = urllib.request.urlopen(get_url).read()
        Path(paper_info_filepath).write_bytes(contents)
    return json.loads(contents)


def render_graph_rec(dot, paper_id, max_level, cur_level=0):
    if cur_level >= max_level:
        return
    j = get_paper_json(paper_id)
    if cur_level == 0:
        dot.node(j['paperId'], f"{j['title']} ({j['year']})")
    for r in j['references']:
        if r['isInfluential']:
            dot.node(r['paperId'], f"{r['title']} ({r['year']})")
            dot.edge(j['paperId'], r['paperId'])
            render_graph_rec(dot, r['paperId'], max_level, cur_level + 1)


def render_graph_rec_cit(dot, paper_id,  max_level, cur_level=0):
    if cur_level >= max_level:
        return
    j = get_paper_json(paper_id)
    if cur_level == 0:
        dot.node(j['paperId'], f"{j['title']} ({j['year']})")
    for c in j['citations']:
        if c['isInfluential']:
            dot.node(c['paperId'], f"{c['title']} ({c['year']})")
            dot.edge(c['paperId'], j['paperId'])
            render_graph_rec_cit(dot, c['paperId'], max_level, cur_level + 1)


def create_graph(nodes_dict):
    G = nx.DiGraph()
    nodes = []
    edges = []
    for parent_node_id, parent_node in nodes_dict.items():
        nodes.append(parent_node_id)
        if parent_node.leaf is False:
            for child_node_id in parent_node.children:
                edges.append((parent_node_id, child_node_id))
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    return G


def calc_labels(nodes_dict):
    href_str = "<a href=\"{}\" style=\"color: inherit; text-decoration: underline;\">{}</a>({})<br>citations: {}"
    return [href_str.format(node.data['url'], node.data['title'], node.data['year'], len(node.data['citations']))
            for node in nodes_dict.values()]


def calc_sizes(nodes_dict):
    min_size = 10
    max_size = 40
    sizes = np.array([len(node.data['citations'])
                      for node in nodes_dict.values()])
    range_old = (sizes.max() - sizes.min())
    range_new = (max_size - min_size)
    sizes = (range_new / range_old) * (sizes - sizes.max()) + max_size
    return sizes


def calc_years(nodes_dict):
    return [node.data['year'] for node in nodes_dict.values()]


def plot_graph(G, labels, sizes, years):
    pos = graphviz_layout(G, prog='dot')

    # Nodes
    Xn, Yn = zip(*[(p[0], p[1]) for p in pos.values()])
    trace_nodes = dict(type='scatter',
                       x=Xn,
                       y=Yn,
                       mode='markers',
                       marker=dict(size=sizes,
                                   colorscale='Jet',
                                   color=years,
                                   colorbar=dict(title='Colorbar')),
                       text=labels,
                       textposition='top center',
                       hoverinfo='text')

    # Edges
    x0 = [pos[e[0]][0] for e in G.edges()]
    y0 = [pos[e[0]][1] for e in G.edges()]
    x1 = [pos[e[1]][0] for e in G.edges()]
    y1 = [pos[e[1]][1] for e in G.edges()]
    arrows_annotations = [dict(ax=x0[i],
                               ay=y0[i],
                               axref='x',
                               ayref='y',
                               x=x1[i],
                               y=y1[i],
                               xref='x',
                               yref='y',
                               arrowsize=1,
                               arrowwidth=1,
                               arrowhead=2,
                               opacity=0.5)
                          for i in range(0, len(x0))]

    # Layout
    axis = dict(showline=False,  # hide axis line, grid, ticklabels and  title
                zeroline=False,
                showgrid=False,
                showticklabels=False,
                title=''
                )

    layout = go.Layout(title='Citations graph',
                       showlegend=False,
                       xaxis=axis,
                       yaxis=axis,
                       margin=dict(l=40,
                                   r=40,
                                   b=85,
                                   t=100,
                                   pad=0,
                                   ),
                       hovermode='closest',
                       annotations = arrows_annotations
                       )

    fig = go.Figure(data=[trace_nodes], layout=layout)
    plotly.offline.plot(fig, auto_open=True)


def render_graph(nodes_dict):
    G = create_graph(nodes_dict)
    labels = calc_labels(nodes_dict)
    sizes = calc_sizes(nodes_dict)
    years = calc_years(nodes_dict)
    plot_graph(G, labels, sizes, years)


def bfs(start_node_id, depth):
    todo = [(start_node_id, 0)]
    nodes_dict = {}

    while len(todo) > 0:
        node_id, node_depth = todo.pop(0)

        # If node already visited no need to visit again
        if node_id in nodes_dict:
            continue

        # Save
        node = get_node(node_id)
        nodes_dict[node.id] = node

        # print
        spacer_str = ''.join(['-' for _ in range(node_depth)])
        print(f"{spacer_str} {node.id} ({len(node.children)})")

        # If we are too deep continue
        if node_depth > depth:
            node.leaf = True
            continue

        # Add children to visit stack
        for next_node_id in node.children:
            todo.append((next_node_id, node_depth + 1))

    return nodes_dict


def get_node(id):
    data = get_paper_json(id)
    citation_ids = []
    for citation in data['citations']:
        if citation['isInfluential']:
            citation_ids.append(citation["paperId"])
    return Node(id, citation_ids, data)


class Node:
    def __init__(self, id, children, data):
        self.id = id
        self.children = children
        self.data = data
        self.leaf = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", action="store_true",
                        help="Forward (citations) drawing)")
    parser.add_argument("-d", type=int, default=2,
                        help="Recursion depth")
    # parser.add_argument("-id", action="append", required=True,
    #                       help="Paper ID in SemanticScholar")
    parser.add_argument("-id", required=True,
                        help="Paper ID in SemanticScholar")
    args = parser.parse_args()

    if not os.path.exists("papers"):
        os.mkdir("papers")

    # render_graph(args.id, args.d, args.f)
    nodes_dict = bfs(args.id, args.d)
    render_graph(nodes_dict)
