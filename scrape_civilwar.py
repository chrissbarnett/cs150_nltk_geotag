from bs4 import BeautifulSoup as Soup
import json
import os


class CivilWarScraper:
    def __init__(self):
        self.pages = {}
        self.target_dir = './data/texts/civil_war_photos'
        self.html_file = './data/texts/civil_war_photos/43922-h.htm'

    def read_pages(self):
        """
        load the html and read it into our output json structure. Save the json file.
        :return:
        """
        self.pages = {}
        soup = self.load_html(self.html_file)
        self.pages = self.get_pages(soup)
        self.persist_pages()

    def persist_pages(self):
        """
        write the pages json file
        :return:
        """
        path = os.path.join(self.target_dir, 'pages.json')
        self.write_json(self.pages, path)

    def write_json(self, map, path):
        """
        write a json file from a python dictionary
        :param map:
        :param path:
        :return:
        """
        with open(path, 'w') as f:
            f.write(json.dumps(map, ensure_ascii=False))

    def load_html(self, path):
        """
        open a locally saved html file and return a BeautifulSoup object
        :param path:
        :return:
        """
        html = ''
        with open(path, 'rb') as f:
            html = f.read()
        return Soup(html, 'html.parser')

    def get_page_id(self, span):
        """
        gets the id from a nested anchor tag. document specific.
        :param span:
        :return:
        """
        return span.find('a').get('id')

    def parse_text(self, soup):
        """
        decides how to parse an element passed in. document specific
        :param soup:
        :return:
        """
        # if the element is an hr element, skip it
        if soup.name in ['hr']:
            return {}

        # if the element is a p element, process it if it has class 'indent'
        if soup.name == 'p':
            if 'indent' in soup.get('class'):
                text = soup.get_text()

                # removing extra whitespace, making sure emdashes have space around them for proper tokenization
                text = text.replace('\n', ' ').replace('\r', ' ').replace('—', ' — ').replace('  ', ' ')

                # make sure that there is a space at the end of a sentence, to prevent segmentation issues
                if not text.endswith(' '):
                    text = text + ' '
                # print(text)
                return {'text': text}
        elif soup.name == 'div':
            # image captions are in a child div with class 'caption'
            caption = soup.find('div', 'caption')
            if caption is not None:
                text = caption.get_text()

                # removing extra whitespace, making sure emdashes have space around them for proper tokenization
                text = text.replace('\r\n', ' ').replace('\n\n', '\n').replace('—', ' — ')
                text = text.lstrip('\n')

                # ideally, we would process caption titles differently, but we're adding a period just to make sure
                # titles don't get concatenated with the following sentence.
                text = text.replace('\n', '. ').replace('  ', ' ')
                return {'caption': text}
        return {}

    def get_pages(self, soup):
        """
        pulls 'pages' from the html book, parses out captions and text, stuffs the result into a dictionary. document
        specific
        :param soup:
        :return:
        """
        page_idx = 0
        # each page in the book begins with a span element with class 'pagenum'
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






