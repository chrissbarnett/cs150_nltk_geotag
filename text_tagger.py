import glob
import os
import json
import copy

from ner_tagger import NERTagger
from stanford_ner_tagger import StanfordTagger


class TextTagger:
    """
    Tag a structured text with named entities
    """
    def __init__(self, use_stanford=True):
        # by default, use the StanfordTagger
        self.use_stanford = use_stanford
        if use_stanford:
            self.tagger = StanfordTagger()
        else:
            self.tagger = NERTagger()

    def process_directory(self, dir_path, retag=False):
        """
        process structured text files (json) in the specified directory
        :param dir_path:
        :param retag: flag that allows additional tagging
        :return:
        """
        pattern = '*.json'
        if retag:
            pattern = '*.tagged.json'
        matches = glob.glob(os.path.join(dir_path, pattern))
        for m in matches:
            name = os.path.basename(m)

            # ignore some json files
            if name in ['contents.json']:
                continue

            # skip already tagged files if retag flag is set
            if not retag:
                if name.endswith('.tagged.json'):
                    continue

            self.tag_text(m)

    def load_json(self, path):
        json_txt = ''
        with open(path, 'r') as f:
            json_txt = f.read()
        return json.loads(json_txt)

    def write_json(self, path, json_dict):
        with open(path, 'w') as f:
            f.write(json.dumps(json_dict, ensure_ascii=False))

    def tag_text(self, path):
        """
        tag text with extracted entities
        :param path:
        :return:
        """
        txt = self.load_json(path)

        # use a copy so we aren't modifying an object as we iterate over it
        txt_copy = copy.deepcopy(txt)

        # process the text
        for k, v in txt_copy.get('textmap').items():
            entities = self.process_text(v.get('text'))
            key = 'entities'

            # store stanford entities with a different key
            if self.use_stanford:
                key = 'entities_stanford'

            txt['textmap'][k][key] = entities
        suffix = '.tagged.json'
        if path.endswith('.tagged.json'):
            suffix = '.json'
        self.write_json(path[:-5] + suffix, txt)

    def process_text(self, raw_text):
        self.tagger.set_text(raw_text=raw_text)
        return self.tagger.extract_named_entities()
