import urllib.request
from pathlib import Path
import json
# from graphviz import Digraph
import argparse
import os
import networkx as nx
import plotly
import plotly.graph_objs as go


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


#def calc_init_pos(nodes_dict):
#    init_pos = {}
#    for node_id, node in nodes_dict.items():
#        # import pdb; pdb.set_trace()
#        init_pos[node_id] = (0, node.data['year'])
#    return init_pos

def calc_init_pos(nodes_dict):
    init_pos = {}
    for node_id, node in nodes_dict.items():
        year = node.data['year']
        if year not in init_pos:
            init_pos[year] = []
        init_pos[year].append(node_id)
    return [node_list for node_list in init_pos.values()]

# ----------- Need to add text to draw proper text labels

def plot_graph(G, init_pos=None):
    print(init_pos)
    #pos = nx.spring_layout(G, pos=init_pos, fixed=init_pos.keys())
    #graphviz_layout(G)
    # pos = nx.nx_agraph.graphviz_layout(G)
    pos = nx.shell_layout(G, nlist=init_pos)
    print(pos)
    #import pdb; pdb.set_trace()

    # Nodes
    Xn, Yn = zip(*[(p[0], p[1]) for p in pos.values()])
    print(G.nodes())
    import pdb; pdb.set_trace()
    #for n in G.nodes():
    #Xn.append(pos[
    trace_nodes = dict(type='scatter',
                       x=Xn,
                       y=Yn,
                       mode='markers',
                       marker=dict(size=28, color='rgb(0,240,0)'),
                       text=[],
                       hoverinfo='text')

    # Edges
    Xe = []
    Ye = []
    for e in G.edges():
        Xe.extend([pos[e[0]][0], pos[e[1]][0], None])
        Ye.extend([pos[e[0]][1], pos[e[1]][1], None])
    trace_edges = dict(type='scatter',
                       mode='lines',
                       x=Xe,
                       y=Ye,
                       line=dict(width=1, color='rgb(25,25,25)'),
                       hoverinfo='none'
                       )

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
                       )

    fig = dict(data=[trace_edges, trace_nodes], layout=layout)
    plotly.offline.plot(fig, auto_open=True)


def render_graph(nodes_dict):
    G = create_graph(nodes_dict)
    init_pos = calc_init_pos(nodes_dict)
    plot_graph(G, init_pos)

# def render_graph(nodes_dict):
#     dot = Digraph()
#     for id, node in nodes_dict.items():
#         data = node.data
#         dot.node(id, f"{data['title']} ({data['year']})")
#         for child_id in node.children:
#             dot.edge(child_id, id)
#     dot.render('g', format='pdf')


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
