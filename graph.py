import urllib.request
from pathlib import Path
import json
from graphviz import Digraph
from collections import namedtuple
import argparse


paper_ids = ("36f768dbb12fb44f3faee814b97ad5e495094dcf",
             "2d7551bb6127067d469a810d412c7b149b7d54cc",
             "d834cac83c55ab7f14a9a05f9fd437813fff1403")


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


def render_graph(paper_ids, depth, forward=False):
    dot = Digraph()
    if forward:
        for id in paper_ids:
            render_graph_rec_cit(dot, id, depth)
    else:
        for id in paper_ids:
            render_graph_rec(dot, id, depth)
    dot.render('g', format='pdf')



if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", action="store_true",
                        help="Forward (citations) drawing)")
    parser.add_argument("-d", type=int, default=2,
                        help="Recursion depth")
    parser.add_argument("-id", action="append", required=True,
                        help="Paper ID in SemanticScholar")
    args = parser.parse_args()
    render_graph(args.id, args.d, args.f)
