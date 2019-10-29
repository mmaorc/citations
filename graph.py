from pathlib import Path
import json
import argparse
import os
import networkx as nx
import plotly
import plotly.graph_objs as go
import numpy as np
from networkx.drawing.nx_agraph import graphviz_layout
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


# Paper scanning

class Node:
    def __init__(self, id, children, data):
        self.id = id
        self.children = children
        self.data = data
        self.leaf = False


def get_paper_json(paper_id):
    paper_info_filepath = rf"papers/{paper_id}.json"
    if Path(paper_info_filepath).exists():
        contents = Path(paper_info_filepath).read_text()
    else:
        contents = request_paper(paper_id)
        Path(paper_info_filepath).write_bytes(contents)
    contents = json.loads(contents)
    if "error" in contents.keys():
        return None
    return contents


def request_paper(paper_id):
    s = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=1,
                    status_forcelist=[502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    d = s.get(f"https://api.semanticscholar.org/v1/paper/{paper_id}")
    return d.content


def get_node(id, extended=False):
    data = get_paper_json(id)
    if data is None:
        return None
    citation_ids = []
    for citation in data['citations']:
        if extended or citation['isInfluential']:
            citation_ids.append(citation["paperId"])
    return Node(id, citation_ids, data)


def bfs(start_node_id, depth, get_node):
    todo = [(start_node_id, 0)]
    nodes_dict = {}

    while len(todo) > 0:
        node_id, node_depth = todo.pop(0)

        # If node already visited no need to visit again
        if node_id in nodes_dict:
            continue

        # Get the node data
        node = get_node(node_id)
        if node is None:
            continue

        # Save
        nodes_dict[node.id] = node

        # print
        #spacer_str = ''.join(['-' for _ in range(node_depth)])
        #print(f"{spacer_str} {node.id} ({len(node.children)})")

        # If we are too deep continue
        if node_depth > depth:
            node.leaf = True
            continue

        # Add children to visit stack
        for next_node_id in node.children:
            todo.append((next_node_id, node_depth + 1))

    return nodes_dict


# Graph creation

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
    threshold = 200
    sizes = np.array([len(node.data['citations'])
                      for node in nodes_dict.values()])
    sizes[sizes > threshold] = threshold
    range_old = (sizes.max() - sizes.min()) + 1
    range_new = (max_size - min_size)
    sizes = (sizes - sizes.min()) / range_old
    sizes = range_new * sizes + min_size
    return sizes


def calc_years(nodes_dict):
    years = [node.data['year'] for node in nodes_dict.values()]
    min_year = min([y for y in years if y is not None])
    years = [y if y is not None else min_year for y in years]
    return years


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
                       annotations=arrows_annotations
                       )

    fig = go.Figure(data=[trace_nodes], layout=layout)
    plotly.io.write_html(fig, file="output.html", auto_open=False)
    with open("output.html", "r") as f:
        print(f.read())


def render_graph(nodes_dict):
    G = create_graph(nodes_dict)
    labels = calc_labels(nodes_dict)
    sizes = calc_sizes(nodes_dict)
    years = calc_years(nodes_dict)
    plot_graph(G, labels, sizes, years)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", type=int, default=2,
                        help="Recursion depth")
    parser.add_argument("-id", required=True,
                        help="Paper ID in SemanticScholar")
    parser.add_argument("-extended", action="store_true",
                        help="Scan non influential as well")
    args = parser.parse_args()

    if not os.path.exists("papers"):
        os.mkdir("papers")

    get_node_lam = lambda id: get_node(id, args.extended)

    nodes_dict = bfs(args.id, args.d, get_node_lam)
    render_graph(nodes_dict)
