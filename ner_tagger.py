import nltk
import json


class NERTagger:
    """
    Extract Named Entities using NLTK built-in taggers.

    usage:
    nt = NERTagger()
    nt.set_text(raw_text=text_string)
    entities = nt.extract_named_entities()

    or for a text file:
    nt = NERTagger()
    nt.set_text(txtfile_path=path_to_text)
    entities = nt.extract_named_entities()
    """
    def __init__(self, nltk_dir='./data/nltk'):
        # downloading needed components inline to a specified directory
        nltk.download('averaged_perceptron_tagger', download_dir=nltk_dir)
        nltk.download('maxent_ne_chunker', download_dir=nltk_dir)
        nltk.download('words', download_dir=nltk_dir)

        # add the directory to the nltk data path
        nltk.data.path.append(nltk_dir)

        self.txtfile_path = None
        self.raw_text = None

    def set_text(self, raw_text=None, txtfile_path=None):
        if txtfile_path is not None:
            self.load_txt()
        else:
            self.raw_text = raw_text

    def load_txt(self):
        """
        load the text from a file
        :return:
        """
        if self.txtfile_path is None:
            raise Exception('No text file path specified!')
        with open(self.txtfile_path, 'r') as f:
            self.raw_text = f.read()
            return self.raw_text

    def write_json(self, json_path, json_data):
        with open(json_path, 'w') as f:
            f.write(json.dumps(json_data, ensure_ascii=False))

    def segment(self, raw_text):
        """
        segment the loaded text into sentences
        :return:
        """
        return nltk.sent_tokenize(raw_text)

    def tokenize(self, sentences):
        """
        tokenize the words in the sentences. basically tokenizes on white space
        :return:
        """
        return [nltk.word_tokenize(sent) for sent in sentences]

    def tag_pos(self, tokenized):
        """
        tag parts of speech
        :param tokenized:
        :return:
        """
        return [nltk.pos_tag(sent) for sent in tokenized]

    def chunk(self, pos_tagged):
        """
        chunk POS tags into named entities
        :param pos_tagged:
        :return:
        """
        return nltk.ne_chunk_sents(pos_tagged)

    def parse_entity(self, c, entity_tree):
        """
        recursively parse the tree structure from the chunker, placing Named Entities in an entities dict.
        :param c:
        :param entity_tree:
        :return:
        """
        if hasattr(c, 'label') and c.label:
            label = c.label()
            if label == 'PERSON':
                entity_tree['people'].append(' '.join([child[0] for child in c]))
            elif label == 'GPE':
                entity_tree['places'].append(' '.join([child[0] for child in c]))
            elif label == 'ORGANIZATION':
                entity_tree['organizations'].append(' '.join([child[0] for child in c]))
            else:
                for child in c:
                    self.parse_entity(child, entity_tree)

    def build_entities(self, chunk_iter):
        entity_tree = {'people': [], 'places': [], 'organizations': []}
        for c in chunk_iter:
            self.parse_entity(c, entity_tree)
        return entity_tree

    def extract_named_entities(self):
        """
        run through the whole process
        :return:
        """
        sentences = self.segment(self.raw_text)
        tokenized = self.tokenize(sentences)
        pos_tagged = self.tag_pos(tokenized)

        return self.build_entities(self.chunk(pos_tagged))



