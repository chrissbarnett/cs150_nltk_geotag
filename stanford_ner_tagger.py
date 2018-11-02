from nltk.tag import StanfordNERTagger, StanfordPOSTagger
from nltk.chunk.regexp import RegexpParser
import nltk
import os
import json


class StanfordTagger:
    """
    Extract Named Entities using Stanford NER and Stanford POS taggers.

    usage:
    st = StanfordTagger()
    st.set_text(raw_text=text_string)
    entities = st.extract_named_entities()

    or for a text file:
    st = StanfordTagger()
    st.set_text(txtfile_path=path_to_text)
    entities = st.extract_named_entities()
    """
    def __init__(self,
                 ner_model='english.muc.7class.distsim.crf.ser.gz',
                 pos_model='english-bidirectional-distsim.tagger',
                 path_to_pos_jar='./stanford/stanford-postagger-full-2018-02-27/stanford-postagger.jar',
                 path_to_ner_jar='./stanford/stanford-ner-2018-02-27/stanford-ner.jar'):

        stanford_models = ['./stanford/stanford-postagger-full-2018-02-27/models',
                           './stanford/stanford-ner-2018-02-27/classifiers',
                           './stanford/stanford-parser-full-2018-02-27/data']
        os.environ['STANFORD_MODELS'] = ':'.join(stanford_models)

        self.pos_tagger = StanfordPOSTagger(pos_model, path_to_jar=path_to_pos_jar)
        self.ner_tagger = StanfordNERTagger(ner_model, path_to_jar=path_to_ner_jar)
        self.txtfile_path = None
        self.raw_text = None

    def set_text(self, raw_text=None, txtfile_path=None):
        """
        set the text to extract entities from
        :param raw_text:
        :param txtfile_path:
        :return:
        """
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

    def tag_ner(self, tokenized):
        """
        use the Stanford NER tagger to tag the tokens
        :return:
        """
        return [self.ner_tagger.tag(sent) for sent in tokenized]

    def tag_pos(self, tokenized):
        """
        use the Stanford POS tagger to tag tokens with the parts of speech
        :return:
        """
        return [self.pos_tagger.tag(sent) for sent in tokenized]

    def merge_tags(self, ner_tagged, pos_tagged):
        """
        merge tags for flexibility in chunking. the Stanford NER tagger tags everything id'ed as an entity with 'O'.
        This makes it difficult to specify tag patterns for chunking. This function merges the tags by appending the
        POS tag to the NER tag (separated by an underscore)
        :return:
        """
        merged_tags = []
        for i, val in enumerate(pos_tagged):
            sent = []
            merged_tags.append(sent)
            for n, tag in enumerate(val):
                newval = (tag[0], ner_tagged[i][n][1] + '_' + tag[1])
                sent.append(newval)
        return merged_tags

    def chunk(self, merged_tags):
        """
        use the NLTK RegexpParser to chunk tagged text into usable tokens
        :return:
        """
        pattern = '''
            GEO: {<LOCATION_.*><LOCATION_.*>+}
            {<LOCATION_NNP>+<O_NN>}
            {<LOCATION_NNP>}
            ORG: {<ORGANIZATION_.*>+}
            PER: {<PERSON_.*>+}
            DTT: {<DATE_.*>+}
        '''

        return self.regex_chunk(merged_tags, pattern)

    def regex_chunk(self, tagged, pattern):
        pr = RegexpParser(pattern)
        chunked = [pr.parse(sent) for sent in tagged]
        return chunked

    def test_regex_chunker(self, tagged, pattern):
        """
        used to test different chunking patterns
        :param tagged:
        :param pattern:
        :return:
        """
        chunked = self.regex_chunk(tagged, pattern)
        return self.collate_chunks(chunked)

    token_index = 0

    def collate_chunks(self, chunks):
        self.token_index = 0
        entity_tree = {'people': [], 'places': [], 'organizations': [], 'dates': []}
        for c in chunks:
            self.parse_entity(c, entity_tree)
        return entity_tree

    def process_node(self, n):
        group = [child[0] for child in n]
        entity = ' '.join(group)
        for i in [',', ')']:
            entity = entity.replace(' ' + i, i)
        for j in ['(']:
            entity = entity.replace(j + ' ', j)
        return entity, len(group)

    def append_entity(self, node, entity_label, entity_tree):
        entity, index_adv = self.process_node(node)
        entity_tree[entity_label].append({'name': entity, 'index': self.token_index})
        self.token_index += index_adv

    def parse_entity(self, c, entity_tree):
        """
        recursively parse the tree structure from the chunker, placing Named Entities in an entities dict.
        :param entity_tree:
        :param c:
        :return:
        """
        if hasattr(c, 'label') and c.label:
            label = c.label()
            if label == 'PER':
                self.append_entity(c, 'people', entity_tree)
            elif label == 'GEO':
                self.append_entity(c, 'places', entity_tree)
            elif label == 'ORG':
                self.append_entity(c, 'organizations', entity_tree)
            elif label == 'DTT':
                self.append_entity(c, 'dates', entity_tree)
            else:
                for child in c:
                    self.parse_entity(child, entity_tree)
        else:
            self.token_index += 1

    def extract_named_entities(self):
        """
        run all of the steps in order
        :return:
        """
        sentences = self.segment(self.raw_text)
        tokenized = self.tokenize(sentences)
        ner_tagged = self.tag_ner(tokenized)
        pos_tagged = self.tag_pos(tokenized)
        merged = self.merge_tags(ner_tagged, pos_tagged)

        chunked = self.chunk(merged)

        return self.collate_chunks(chunked)
