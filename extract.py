from bs4 import BeautifulSoup as Soup
import os
import glob


class TEIExtractor:
    """
    extract text from a TEI document. very rudimentary.
    """

    def __init__(self):
        pass

    def extract_text(self, xmlfile_path):
        if not xmlfile_path.lower().endswith('.xml'):
            raise Exception('{} is missing xml extension.'.format(xmlfile_path))
        with open(xmlfile_path, 'r') as f:
            soup = Soup(f.read(), 'xml')
            return soup.get_text()

    def persist_text(self, xmlfile_path):
        text = self.extract_text(xmlfile_path)
        txt_path = xmlfile_path[:-4] + '.txt'
        with open(txt_path, 'w') as f:
            f.write(text)

    def process_directory(self, dir_path):
        matches = glob.glob(os.path.join(dir_path, '*.xml')) + glob.glob(os.path.join(dir_path, '*.XML'))
        for m in matches:
            self.persist_text(m)
