import urllib.request
from pathlib import Path
import json

papers = ("36f768dbb12fb44f3faee814b97ad5e495094dcf",
          "2d7551bb6127067d469a810d412c7b149b7d54cc")


def get_paper_str(paper_id):
    paper_info_filepath = rf"papers/{paper_id}.json"
    if Path(paper_info_filepath).exists():
        return Path(paper_info_filepath).read_text()
    else:
        get_url = f"https://api.semanticscholar.org/v1/paper/{paper_id}"
        contents = urllib.request.urlopen(get_url).read()
        Path(paper_info_filepath).write_bytes(contents)
        return contents


def extract_refs(paper_str):
    d = json.loads(paper_str)
    return [r['paperId'] for r in d['references']]


def filter_refs(papers, paper_refs):
    return [r for r in paper_refs if r in papers]


papers_strs = [get_paper_str(p) for p in papers]
papers_refs = [extract_refs(s) for id,s in zip(papers, papers_strs)]
papers_refs_filetered = [filter_refs(papers, refs) for refs in papers_refs]
