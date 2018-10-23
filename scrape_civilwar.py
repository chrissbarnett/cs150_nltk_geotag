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
        self.pages = {}
        self.target_dir = './data/texts/civil_war_photos'
        self.html_file = './data/texts/civil_war_photos/43922-h.htm'

    def read_pages(self):
        self.pages = {}
        soup = self.load_html(self.html_file)
        self.pages = self.get_pages(soup)
        self.persist_pages()

    def persist_pages(self):
        path = os.path.join(self.target_dir, 'pages.json')
        self.write_json(self.pages, path)

    def write_json(self, map, path):
        with open(path, 'w') as f:
            f.write(json.dumps(map, ensure_ascii=False))

    def load_html(self, path):
        html = ''
        with open(path, 'rb') as f:
            html = f.read()
        return Soup(html, 'html.parser')

    def get_page_id(self, span):
        return span.find('a').get('id')

    def parse_text(self, soup):
        if soup.name in ['hr']:
            return {}
        if soup.name == 'p':
            if 'indent' in soup.get('class'):
                text = soup.get_text()
                text = text.replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
                # print(text)
                return {'text': text}
        elif soup.name == 'div':
            caption = soup.find('div', 'caption')
            if caption is not None:
                text = caption.get_text()
                text = text.replace('\r\n', ' ').replace('\n\n', '\n')
                text = text.lstrip('\n')
                text = text.replace('\n', '. ').replace('  ', ' ')
                return {'caption': text}
        return {}

    def get_pages(self, soup):
        page_idx = 0
        firstpage = soup.find('span', 'pagenum')
        m = firstpage.parent
        pages = {
            page_idx: {
                'html': str(m),
                'text': '',
                'caption': '',
                'page_id': self.get_page_id(firstpage)
            }
        }
        while True:
            try:
                m = m.find_next_sibling()
                x = m.find('span', 'pagenum')
                if x is not None and x != -1:
                    page_id = self.get_page_id(x)
                    if int(page_id[4:]) > 114:
                        break
                    page_idx += 1
                    pages[page_idx] = {'html': '', 'text': '', 'caption': '', 'page_id': page_id}
                else:
                    # skip parsing text if pagenum node
                    parsed = self.parse_text(m)
                    if 'text' in parsed:
                        pages[page_idx]['text'] += parsed['text']
                    elif 'caption' in parsed:
                        pages[page_idx]['caption'] += parsed['caption']

                pages[page_idx]['html'] += str(m)

            except AttributeError as e:
                break
        return pages

    def get_paragraphs(self):
        for k, v in self.pages.items():
            page = Soup(v['html'], 'html.parser')
            text = page.get_text()
            text = text.replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')

            v['text'] = text
        self.persist_pages()

    def write_page_json(self):
        for k, v in self.contents.items():
            chapter = copy.deepcopy(v)
            soup = self.load_html(v.get('file_path'))
            chapter['textmap'] = self.get_text_map(soup)
            path = os.path.join(self.target_dir, basename(v.get('file_path')).replace('.html', '.json'))
            self.write_json(chapter, path)






