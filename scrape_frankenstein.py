import requests
from bs4 import BeautifulSoup as Soup
import json
import time
import os
import urllib.parse
import copy
from slugify import slugify
from os.path import basename


class FrankensteinScraper:
    """
    class for scraping Frankenstein from the web
    """
    def __init__(self, target_dir='./data/texts/frankenstein1818',
                 contents_url='https://www.rc.umd.edu/editions/frankenstein/1818_contents'):
        self.contents = {}
        # directory to store results
        self.target_dir = target_dir
        # table of contents page
        self.contents_url = contents_url

    def read_contents(self):
        """
        read the table of contents to get links to chapters
        :return:
        """
        self.contents = {}
        r = requests.get(self.contents_url)
        x = Soup(r.text, 'html.parser')
        a = x.findAll('a')  # get a list of anchor elements
        volumes = ['1818v1', '1818v2', '1818v3']
        index = 0
        for i in a:
            if 'frankenstein' in i.get('href'):
                link = i.get('href')
                volume = self.parse_vol(link)
                # links are relative urls. get the absolute url
                abs_url = urllib.parse.urljoin(self.contents_url, link)

                # we only want links to chapters in certain volumes
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
        """
        parse the volume name from the link
        :param link:
        :return:
        """
        return link.split('/')[-2]

    def download_html(self):
        """
        download the html files from TOC links
        :return:
        """
        cnts = copy.deepcopy(self.contents)
        for k, v in cnts.items():
            path = os.path.join(self.target_dir, slugify(v.get('volume') + '_' + v.get('label')) + '.html')
            self.contents[k]['file_path'] = path
            r = requests.get(v.get('link'))
            with open(path, 'w') as f:
                f.write(r.text)
            # be friendly!
            time.sleep(1.0)

    def persist_contents(self):
        """
        write the contents to a json file
        :return:
        """
        path = os.path.join(self.target_dir, 'contents.json')
        self.write_json(self.contents, path)

    def write_json(self, map, path):
        with open(path, 'w') as f:
            f.write(json.dumps(map, ensure_ascii=False))

    def load_html(self, path):
        """
        load html file as Beautiful Soup object
        :param path:
        :return:
        """
        with open(path, 'r') as f:
            html = f.read()
            return Soup(html, 'html.parser')

    def get_text_map(self, soup):
        """
        create a structure to store text in
        :param soup:
        :return:
        """
        text_map = {}

        # find the element that holds the text
        chapter = soup.find('div', 'field-type-text-with-summary')
        if chapter is None:
            return text_map

        # paragraphs are list items
        chapter = chapter.find('ol')
        if chapter is None:
            print('no ol found')
            return text_map
        paragraphs = chapter.find_all('li', recursive=False)

        for pindex, p in enumerate(paragraphs):
            text_map[pindex] = {'text': p.get_text().strip()}

            # paragraphs contain anchors with paragraph ids.
            anchors = p.find_all('a')
            for a in anchors:
                pid = a.get('id')
                if pid is not None and pid.startswith('p'):
                    text_map[pindex]['pid'] = pid
        return text_map

    def get_metadata(self, soup):
        """
        the html files have basic Dublin Core metadata. capture it here.
        :param soup:
        :return:
        """
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






