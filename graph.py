import urllib.request
from pathlib import Path
import json
from graphviz import Digraph
from collections import namedtuple

Details = namedtuple('Details', ['id', 'title', 'year', 'references'])

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


def render_graph_rec(dot, paper_id,  max_level, cur_level=0):
    j = get_paper_json(paper_id)
    dot.node(j['paperId'], f"{j['title']} ({j['year']})")
    if cur_level >= max_level:
        return
    for r in j['references']:
        if r['isInfluential']:
            dot.edge(j['paperId'], r['paperId'])
            render_graph_rec(dot, r['paperId'], max_level, cur_level + 1)


def ren(paper_ids):
    dot = Digraph()
    for id in paper_ids:
        render_graph_rec(dot, id, 1)
    dot.render('g', format='pdf')


ren(paper_ids)
