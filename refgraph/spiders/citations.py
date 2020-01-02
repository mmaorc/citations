# -*- coding: utf-8 -*-
import scrapy
import json
from functools import partial


def gen_req_url(paper_id):
    return f'http://api.semanticscholar.org/v1/paper/{paper_id}'


class CitationsSpider(scrapy.Spider):
    name = 'citations'
    allowed_domains = ['semanticscholar.org']

    #def __init__(self, start_id='f26d35d2e32934150cd27b030d4d769942126184', depth=1, extended=False, refs=False, **kwargs):
    def __init__(self, start_id='', depth=1, extended=False, refs=False, **kwargs):
        assert start_id != ''
        self.start_urls = [gen_req_url(start_id)]
        self.depth = int(depth)
        self.extended = extended
        self.refs = refs

    def parse_paper(self, response, cur_depth):
        response_json = json.loads(response.text)
        citation_ids = [cit["paperId"] for cit in response_json['citations'] if self.extended or cit['isInfluential']]

        if cur_depth < self.depth:
            for cit_id in citation_ids:
                yield response.follow(gen_req_url(cit_id), callback=partial(self.parse_paper, cur_depth=cur_depth+1))

        yield {"id": response_json["paperId"],
            "children": citation_ids,
            "url": response_json["url"],
            "title": response_json["title"],
            "year": response_json["year"],
            "citations": response_json["citations"],
            "leaf": cur_depth == self.depth
        }

    def parse(self, response):
        return self.parse_paper(response, 0)
