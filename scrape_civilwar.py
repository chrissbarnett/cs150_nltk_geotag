import requests
from bs4 import BeautifulSoup as Soup
import json
import time
import os
import urllib.parse
import copy
from slugify import slugify
from os.path import basename


class CivilWarScraper:
    def __init__(self):
        self.contents = {}
        self.target_dir = './data/texts/civil_war_photos'
        self.html_file = './data/texts/civil_war_photos/43922-h.htm'

    def read_contents(self):
        self.contents = {}
        with open(self.html_file, 'r') as f:
            text = f.read()
            x = Soup(text, 'html.parser')
            a = x.findAll('hr')
            volumes = ['1818v1', '1818v2', '1818v3']
            index = 0
            for i in a:
                if 'frankenstein' in i.get('href'):
                    link = i.get('href')
                    volume = self.parse_vol(link)
                    abs_url = urllib.parse.urljoin(self.contents_url, link)
                    if volume in volumes:
                        chapter = {
                            'link': abs_url,
                            'label': i.get_text(),
                            'chapter_index': index,
                            'volume': volume
                        }
                        self.contents[index] = chapter
                        index += 1

    def read_stored_contents(self):
        path = os.path.join(self.target_dir, 'contents.json')
        with open(path, 'r') as f:
            self.contents = json.loads(f.read())

    def parse_vol(self, link):
        return link.split('/')[-2]

    def persist_contents(self):
        path = os.path.join(self.target_dir, 'contents.json')
        self.write_json(self.contents, path)

    def write_json(self, map, path):
        with open(path, 'w') as f:
            f.write(json.dumps(map, ensure_ascii=False))

    def load_html(self, path):
        html = ''
        with open(path, 'r') as f:
            html = f.read()
        return Soup(html, 'html.parser')

    def get_text_map(self, soup):
        text_map = {}
        chapter = soup.find('div', 'field-type-text-with-summary')
        if chapter is None:
            return text_map
        chapter = chapter.find('ol')
        if chapter is None:
            print('no ol found')
            return text_map
        paragraphs = chapter.find_all('li', recursive=False)

        for pindex, p in enumerate(paragraphs):
            text_map[pindex] = {'text': p.get_text().strip()}
            anchors = p.find_all('a')
            for a in anchors:
                pid = a.get('id')
                if pid is not None and pid.startswith('p'):
                    text_map[pindex]['pid'] = pid
        return text_map

    def get_metadata(self, soup):
        metadata = {}
        meta = soup.find_all('meta')
        for m in meta:
            if m.has_attr('name') and m.get('name').startswith('dcterms'):
                metadata[m.get('name')] = m.get('content')
        return metadata

    def write_chapter_json(self):
        for k, v in self.contents.items():
            chapter = copy.deepcopy(v)
            soup = self.load_html(v.get('file_path'))
            chapter['textmap'] = self.get_text_map(soup)
            chapter['metadata'] = self.get_metadata(soup)
            path = os.path.join(self.target_dir, basename(v.get('file_path')).replace('.html', '.json'))
            self.write_json(chapter, path)






