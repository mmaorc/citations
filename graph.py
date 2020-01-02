import json
import argparse
import networkx as nx
import plotly
import plotly.graph_objs as go
import numpy as np
from networkx.drawing.nx_agraph import graphviz_layout
import scrapy
from scrapy.crawler import CrawlerProcess
from refgraph.refgraph.spiders.citations import CitationsSpider
from pathlib import Path


# Graph creation

def create_graph(nodes_dict):
    G = nx.DiGraph()
    nodes = []
    edges = []
    for parent_node_id, parent_node in nodes_dict.items():
        nodes.append(parent_node_id)
        if parent_node['leaf'] is False:
            for child_node_id in parent_node['children']:
                edges.append((parent_node_id, child_node_id))
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    return G


def calc_labels(nodes_dict):
    href_str = "<a href=\"{}\" style=\"color: inherit; text-decoration: underline;\">{}</a>({})<br>citations: {}"
    return [href_str.format(node['url'], node['title'], node['year'], len(node['citations']))
            for node in nodes_dict.values()]


def calc_sizes(nodes_dict):
    min_size = 10
    max_size = 40
    threshold = 200
    sizes = np.array([len(node['citations'])
                      for node in nodes_dict.values()])
    sizes[sizes > threshold] = threshold
    range_old = (sizes.max() - sizes.min()) + 1
    range_new = (max_size - min_size)
    sizes = (sizes - sizes.min()) / range_old
    sizes = range_new * sizes + min_size
    return sizes


def calc_years(nodes_dict):
    years = [node['year'] for node in nodes_dict.values()]
    min_year = min([y for y in years if y is not None])
    years = [y if y is not None else min_year for y in years]
    return years


def plot_graph(G, labels, sizes, years, output_filepath):
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
    plotly.io.write_html(fig, file=str(output_filepath), auto_open=False)


def render_graph(nodes_dict, output_filepath):
    G = create_graph(nodes_dict)
    labels = calc_labels(nodes_dict)
    sizes = calc_sizes(nodes_dict)
    years = calc_years(nodes_dict)
    plot_graph(G, labels, sizes, years, output_filepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache_dirpath", default="output/cache")
    parser.add_argument("--output_filepath", default="output/output.html")
    parser.add_argument("--paper_id", required=True)
    args = parser.parse_args()

    cache_dirpath = Path(args.cache_dirpath)
    paper_json_path = cache_dirpath/f"{args.paper_id}.json"
    output_filepath = Path(args.output_filepath)

    # Run the spider if necessary
    if not paper_json_path.exists():
        process = CrawlerProcess(settings={
            'FEED_FORMAT': 'json',
            'FEED_URI': str(paper_json_path),
            'LOG_LEVEL': 'INFO',
        })
        process.crawl(CitationsSpider, start_id=args.paper_id)
        process.start()

    # Draw the graph
    with open(paper_json_path) as f:
        nodes = json.load(f)
    nodes_dict = {n['id']: n for n in nodes}

    render_graph(nodes_dict, output_filepath)
