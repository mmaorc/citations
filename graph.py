import urllib.request
from pathlib import Path
import json
from graphviz import Digraph
from collections import namedtuple

Details = namedtuple('Details', ['id', 'title', 'year', 'references'])

papers = ("36f768dbb12fb44f3faee814b97ad5e495094dcf",
          "2d7551bb6127067d469a810d412c7b149b7d54cc",
          "d834cac83c55ab7f14a9a05f9fd437813fff1403")


def get_paper_str(paper_id):
    paper_info_filepath = rf"papers/{paper_id}.json"
    if Path(paper_info_filepath).exists():
        return Path(paper_info_filepath).read_text()
    else:
        get_url = f"https://api.semanticscholar.org/v1/paper/{paper_id}"
        contents = urllib.request.urlopen(get_url).read()
        Path(paper_info_filepath).write_bytes(contents)
        return contents


def extract_details(paper_str, reference_filter):
    paper_json = json.loads(paper_str)
    id = paper_json['paperId']
    title = paper_json['title']
    year = paper_json['year']
    references = reference_filter(paper_json['references'])
    return Details(id, title, year, references)


def our_refs_filter(refs_json):
    return [r['paperId'] for r in refs_json]


def intluential_refs_filter(refs_json):
    return [r['paperId'] for r in refs_json if r['isInfluential']]


def render_graph(papers_details):
    dot = Digraph()
    for d in papers_details.values():
        dot.node(d.id, f"{d.title} ({d.year})")
        for r in d.references:
            #if r in papers_details:
            #    dot.edge(d.id, r)
            dot.edge(d.id, r)

    dot.render('g', format='pdf')


def render_provided_only(papers_strs):
    papers_details = [extract_details(s, our_refs_filter) for s in papers_strs]
    render_graph(papers_details)


def populate_with_papers(papers_details, papers_ids, max_level, cur_level=0):
    if cur_level >= max_level:
        return
    level_papers_strs = map(get_paper_str, papers_ids) # We use map to to avoid loading all strs to RAM at once
    level_papers_details_list = [extract_details(s, intluential_refs_filter) for s in level_papers_strs]
    level_papers_details = {id: d for id, d in zip(papers_ids, level_papers_details_list) if id not in papers_details}
    for id,d in level_papers_details.items():
        papers_details[id] = d
    refs_ids = [r for r in d.references for d in level_papers_details]
    populate_with_papers(papers_details, refs_ids, max_level, cur_level + 1)


def render_recursively(papers, levels_num=3):
    papers_details = {}
    populate_with_papers(papers_details, papers, 3)

    render_graph(papers_details)


papers_strs = map(get_paper_str, papers) # We use map to to avoid loading all strs to RAM at once
#render_provided_only(papers_strs)
render_recursively(papers)
