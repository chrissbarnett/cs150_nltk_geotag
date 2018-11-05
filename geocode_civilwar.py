import json
import nltk
import copy
from geonames_client import GeoNamesClient
from fuzzywuzzy import fuzz


class CivilWarGeocoder:
    states = {}
    pages = {}
    geocode_cache = {}
    places = {}
    firstnames = []

    def __init__(self):
        self.geocoder = GeoNamesClient(token='data_lab')

    def load_states(self):
        # list of states during the Civil War (ignoring territories for now)
        # territories: Montana, Washington, Utah, Arizona, Dakota, Nebraska, Idaho, Colorado, New Mexico, Indian Territory
        self.states = {}
        with open('./data/resources/states.txt', 'r') as f:
            for x in f:
                state_list = x.strip().lower().split(', ')
                for s in state_list:
                    self.states[s] = state_list[0]

    def match_state(self, name):
        if len(self.states) == 0:
            self.load_states()
        match_val = name.replace('.', '').strip().lower()
        if match_val in self.states:
            return self.states[match_val]
        else:
            return None

    def load_pages(self):
        with open('./data/texts/civil_war_photos/pages.tagged.json', 'rb') as f:
            self.pages = json.loads(f.read())

    def persist_pages(self):
        with open('./data/texts/civil_war_photos/pages.tagged.json', 'w') as f:
            f.write(json.dumps(self.pages, ensure_ascii=False))

    def load_geocode_cache(self):
        with open('./data/texts/civil_war_photos/geocode_cache.json', 'rb') as f:
            self.geocode_cache = json.loads(f.read())

    def persist_geocode_cache(self):
        with open('./data/texts/civil_war_photos/geocode_cache.json', 'w') as f:
            f.write(json.dumps(self.geocode_cache, ensure_ascii=False))

    def clear_geocode_cache(self):
        self.geocode_cache = {}
        self.persist_geocode_cache()

    def print_state_entities(self, entities):
        for p in entities:
            match = self.match_state(p.get('name'))
            if match is not None:
                print(match)

    def combine_city_state(self, state_entity, place_entities, tokens):
        """
        look for the pattern 'city, state'. This is a fairly common pattern and will decrease our ambiguity
        :param state_entity:
        :param place_entities:
        :param tokens:
        :return:
        """
        matched_idx = state_entity.get('index')
        for p in place_entities:
            if tokens[matched_idx - 1] == ',':
                last_index = p.get('index') + len(p.get('name').split())
                if matched_idx - last_index == 1:
                    # if the previous token is also a state, assume that this is a list of states, so skip
                    match = self.match_state(p.get('name'))
                    if match is None:
                        combined_entity = {
                            'name': p.get('name') + ', ' + state_entity.get('name'),
                            'index': p.get('index')
                        }
                        # this is getting moved to another list, so we should ignore the original reference
                        p['ignore'] = True
                        return combined_entity
        return None

    def find_city_state_candidates(self, entities, tokens):
        candidates = []
        for p in entities:
            if 'ignore' in p and p['ignore'] is True:
                continue

            match = self.match_state(p.get('name'))
            if match is not None:
                combined = self.combine_city_state(p, entities, tokens)
                if combined is not None:
                    p['ignore'] = True
                    candidates.append(combined)
                else:
                    # New York and Washington get special treatment, since they could be either a state or city
                    if p.get('name') not in ['New York', 'Washington']:
                        state = copy.deepcopy(p)
                        p['ignore'] = True
                        # just the state
                        state['feature_code'] = ['ADM1']
                        candidates.append(state)

        return candidates

    def find_city_state_combinations(self):
        """
        look through place name entities and return matches to US states list (US civil war era)
        :return:
        """
        for k, v in self.pages.items():
            candidates = []
            tokens = self.tokenize(v['text'])
            cap_tokens = self.tokenize(v['caption'])
            key = 'places'
            es = self.find_city_state_candidates(v['entities_stanford'][key], tokens)
            print(es)
            for i in es:
                i['entity_type'] = key
                i['entity_src'] = 'entities_stanford'
            candidates.extend(es)

            cs = self.find_city_state_candidates(v['cap_entities_stanford'][key], cap_tokens)
            print(cs)
            for i in cs:
                i['entity_type'] = key
                i['entity_src'] = 'cap_entities_stanford'
            candidates.extend(cs)
            v['place_candidates'] = candidates

    def tokenize(self, text):
        return nltk.word_tokenize(text)

    def place_as_name(self, place_entity, tokenized_text):
        """
        This method simply checks to see if the entity is quoted.
        :param place_entity:
        :param tokenized_text:
        :return:
        """
        idx = place_entity.get('index')
        name = place_entity.get('name')
        offset = idx + len(name.split())
        quotes = ['\"', '\'', '`', '``', '\'\'']
        if tokenized_text[idx - 1] in quotes and tokenized_text[offset] in quotes:
            # print(tokenized_text[idx - 2: idx + 2])
            print('{} is used as a name'.format(name))
            return True
        return False

    def filter_places_as_names(self):
        """
        sometimes a place is used as the name of something else, like a ship. We want to skip these entities.
        :return:
        """
        for k, v in self.pages.items():
            self.set_ignore_flag(v['entities_stanford']['places'], v['text'], self.place_as_name)

            self.set_ignore_flag(v['cap_entities_stanford']['places'], v['caption'], self.place_as_name)

    def set_ignore_flag(self, entities, text, filter_method):
        tokens = self.tokenize(text)
        for p in entities:
            if filter_method(p, tokens):
                # skip
                p['ignore'] = True

    def get_candidates(self):
        for k, v in self.pages.items():
            for p in v['place_candidates']:
                if len(p) > 0:
                    print(p)

    def geocode_states(self):
        for k, v in self.pages.items():
            for p in v['place_candidates']:
                if len(p) > 0:
                    name = p['name']
                    if ',' in p['name']:
                        name = name.split(',')[1].strip()
                        self.geocode_state(name)
                    else:
                        result = self.geocode_state(name)
                        p['results'] = result['results']
                        p['selected'] = result['selected']

    def geocode_state(self, name):
        match = self.match_state(name)
        if match is not None:
            cache_key = self.get_geonames_cache_key(match, fcodes=('ADM1',))
            result = self.check_cache(cache_key)
            if result is None:
                r = self.geocoder.search_state(match)
                if r is not None:
                    self.cache_geonames(match, [r], fcodes=('ADM1',), selected=r)
                    result = {'results': [r], 'selected': r}
            return result

    def geocode_combined(self):
        """
        geocode combined entities, using state for context
        :return:
        """
        for k, v in self.pages.items():
            for p in v['place_candidates']:
                if len(p) > 0:
                    name = p['name']
                    if ',' in p['name']:
                        results, selected = self.geocode_feature_in_state(name)
                        p['results'] = results
                        p['selected'] = selected

    def clear_ignores(self):
        entity_src = ['cap_entities', 'entities', 'entities_stanford', 'cap_entities_stanford']
        for k, v in self.pages.items():
            for e in entity_src:
                for entity_type, entity_list in v[e].items():
                    for entity in entity_list:
                        print(entity)
                        if 'ignore' in entity:
                            del entity['ignore']

    def geocode_feature_in_state(self, full_name):
        s = full_name.split(',')
        state = s[1].strip()
        match = self.match_state(state)
        # should be cached
        state_code = self.geocode_state(match)['selected']['adminCode1']
        locale = s[0].strip()
        cache_key = self.get_geonames_cache_key(full_name)
        result = self.check_cache(cache_key)
        if result is None:
            results, selected = self.geocoder.search_locale_in_state(locale, state_code)
            if len(results) > 0:
                self.cache_geonames(full_name, results, selected=selected)
            else:
                # loosen the results a bit
                resp = self.geocoder.search_name(locale, style='FULL', fuzz=0.5, state_code=state_code)
                match = (0, None)
                for i in resp['geonames']:
                    ratio, partial = self.place_name_fuzzy_match(locale, i['name'])
                    if ratio > match[0]:
                        match = (ratio, i)
                print(match)
                if match[0] > 85:
                    results = [match[1]]
                    selected = match[1]
                    self.cache_geonames(full_name, results, selected=selected)
            return results, selected
        else:
            print('using cache')
            print(result['selected'])
            return result['results'], result['selected']

    def geocode(self):
        self.load_pages()
        self.load_geocode_cache()
        self.filter_places_as_names()
        self.find_city_state_combinations()
        self.geocode_states()
        self.geocode_combined()
        self.find_matched_place_entities()
        self.process_names()
        self.get_remainder_result_sets()
        self.narrow_results()
        self.select_places()
        self.persist_places()

    def recode(self):
        self.load_pages()
        self.clear_ignores()
        self.persist_pages()
        self.geocode()

    def rescore(self):
        self.load_pages()
        self.select_places()
        self.persist_places()

    def get_geonames_cache_key(self, name, fcodes=None):
        if fcodes is not None:
            key = name + '-' + '_'.join(sorted(fcodes))
            return key.lower()
        else:
            return name.lower()

    def cache_geonames(self, name, results, fcodes=None, selected={}):
        key = self.get_geonames_cache_key(name, fcodes)
        print('cache key: ', key)
        self.geocode_cache[key] = {'results': results, 'selected': selected}

    def check_cache(self, key):
        key = key.lower()
        if key in self.geocode_cache:
            return self.geocode_cache[key]
        else:
            return None

    def find_matched_place_entities(self):
        """
        if we have tagged some places with a high degree of certainty (like 'Richmond, Virginia'), find all other
        matching entities (instances of 'Richmond')
        :return:
        """
        for k, v in self.pages.items():
            for i in v['entities_stanford']['places']:
                if 'ignore' not in i:
                    match = self.match_cached_entities(i['name'])
                    if match is not None:
                        # set ignore flag, add to place candidates
                        i['ignore'] = True
                        v['place_candidates'].append({
                            'name': i['name'],
                            'index': i['index'],
                            'entity_src': 'entities_stanford',
                            'entity_type': 'places',
                            'results': [copy.deepcopy(match)],
                            'selected': copy.deepcopy(match)
                        })
            for i in v['cap_entities_stanford']['places']:
                if 'ignore' not in i:
                    match = self.match_cached_entities(i['name'])
                    if match is not None:
                        # set ignore flag, add to place candidates
                        i['ignore'] = True
                        v['place_candidates'].append({
                            'name': i['name'],
                            'index': i['index'],
                            'entity_src': 'entities_stanford',
                            'entity_type': 'places',
                            'results': [copy.deepcopy(match)],
                            'selected': copy.deepcopy(match)
                        })

    def match_cached_entities(self, placename):
        for k, v in self.geocode_cache.items():
            if 'selected' in v and 'name' in v['selected']:
                if placename.lower() == v['selected']['name'].lower():
                    return v['selected']
        else:
            print('no match for ', placename)
            return None

    def get_remainder_result_sets(self):
        """
        for place entities, not yet matched, search geonames with 10 max results for further processing.
        :return:
        """
        for k, v in self.pages.items():
            print(k)
            for i in v['entities_stanford']['places']:
                if 'ignore' not in i:
                    results = self.generic_geocode(i['name'])
                    v['place_candidates'].append({
                        'name': i['name'],
                        'index': i['index'],
                        'entity_src': 'entities_stanford',
                        'entity_type': 'places',
                        'results': results,
                        'selected': {}
                    })
                    i['ignore'] = True
            for i in v['cap_entities_stanford']['places']:
                if 'ignore' not in i:
                    results = self.generic_geocode(i['name'])
                    v['place_candidates'].append({
                        'name': i['name'],
                        'index': i['index'],
                        'entity_src': 'cap_entities_stanford',
                        'entity_type': 'places',
                        'results': results,
                        'selected': {}
                    })
                    i['ignore'] = True

    def generic_geocode(self, place):
        cache_key = self.get_geonames_cache_key(place)
        result = self.check_cache(cache_key)
        if result is None:
            results = self.geocoder.search_name(place, style='FULL')['geonames']
            if len(results) > 0:
                self.cache_geonames(place, results, selected={})
            return results
        else:
            print('using cache')
            return result['results']

    def show_place_matches(self):
        for k, v in self.pages.items():
            for i in v['place_candidates']:
                if 'selected' in i and 'name' in i['selected']:
                    print(i['name'])
                else:
                    print(i['results'])

    def narrow_results(self):
        for k, v in self.pages.items():
            print(k)

            for i in v['place_candidates']:
                candidates = []
                if 'selected' not in i or 'name' not in i['selected']:
                    print(i['name'])
                    if len(i['results']) > 0:
                        for r in i['results']:
                            test = r['name']
                            ratio, partial = self.place_name_fuzzy_match(i['name'], test)
                            if ratio >= 85:
                                print(i['name'] + ': ' + test + '= ' + str(ratio) + ', ' + str(partial))
                                candidates.append(r)
                    if len(candidates) == 1:
                        print(candidates[0]['name'] + ' selected for ' + i['name'])
                        print(candidates[0])
                        i['selected'] = candidates[0]
                    elif len(candidates) == 0:
                        #print('look at alt names for ' + i['name'])
                        for r in i['results']:
                            if 'alternateNames' in r:
                                for a in r['alternateNames']:
                                    test = a['name']
                                    ratio, partial = self.place_name_fuzzy_match(i['name'], test)
                                    if ratio >= 90:
                                        candidates.append(r)
                                        print(i['name'] + ': ' + test + '= ' + str(ratio) + ', ' + str(partial))
                            else:
                                print('no alternateNames for ' + r['name'])
                    i['results'] = candidates

    def place_name_fuzzy_match(self, name, test):
        name = name.lower()
        test = test.lower()
        historic_terms = ['old', 'battlefield', 'battleground', 'cemetery', '(historical)', 'historic']
        for i in historic_terms:
            if i not in name.split():
                test = test.replace(i, '')
        test = test.replace('  ', ' ').strip()
        ratio = fuzz.ratio(name, test)
        partial = fuzz.partial_ratio(test, name)
        return ratio, partial

    def choose_candidates(self, candidates):
        """
        generate matrix of all candidate choices, return highest scoring set

        :param candidates:
        :return:
        """
        places = {'score':  0, 'places': None}
        base_candidate_list = candidates['selected']
        counter = []
        limits = []
        for r in candidates['results']:
            counter.append(0)
            limits.append(len(r) - 1)
        print(limits)
        #return
        while True:

            candidate = copy.deepcopy(base_candidate_list)
            for i, r in enumerate(candidates['results']):
                candidate.append(r[counter[i]])
            score = self.score_candidate(candidate, sum(counter))
            if score > places['score']:
                places['places'] = candidate
                places['score'] = score

            # print(counter)
            # print(limits)
            if counter == limits:
                break
            # increment counter
            c_index = len(counter) - 1
            while c_index >= 0:
                new_val = counter[c_index] + 1
                if new_val > limits[c_index]:
                    new_val = 0
                counter[c_index] = new_val
                if new_val != 0:
                    break
                else:
                    c_index -= 1

        return places

    def score_candidate(self, candidate_list, depth):
        list_len = len(candidate_list)
        if list_len == 0:
            return 0
        countries = set()
        states = set()
        for c in candidate_list:
            if 'countryCode' in c:
                countries.add(c['countryCode'])
            if 'adminCode1' in c:
                states.add(c['adminCode1'])
        return list_len / max([len(countries) + len(states), 1]) / (depth + list_len)

    def select_places(self):
        """
        CLAVIN uses an algorithm that scores all combinations of place search results and returns the one with
        the fewest state and country values. We will modify that by having a few exact locations to seed that will
        reduce the number of combinations to try. (by combining city, state place names)
        :return:
        """
        places = {}
        max_depth = 5
        for k, v in self.pages.items():
            print(k)
            candidates = {'selected': [], 'results': []}
            added = set()
            for i in v['place_candidates']:
                if 'selected' in i and 'name' in i['selected']:
                    candidates['selected'].append(i['selected'])
                else:
                    if i['name'].lower() in added:
                        continue
                    added.add(i['name'].lower())
                    results = i['results'][0:min(max_depth, len(i['results']))]
                    if len(results) > 0:
                        candidates['results'].append(results)
            chosen = self.choose_candidates(candidates)
            print('chosen')
            print(chosen)
            places[k] = chosen
        self.places = places
        return places

    def persist_places(self):
        with open('./data/texts/civil_war_photos/places.json', 'w') as f:
            f.write(json.dumps(self.places, ensure_ascii=False))

    def load_places(self):
        with open('./data/texts/civil_war_photos/places.json', 'rb') as f:
            self.places = json.loads(f.read())

    def process_names(self):
        """
        find all the values that definitely seem like names, take last names, remove these values from places list
        :return:
        """
        self.load_names()
        last_names = set()
        for k, v in self.pages.items():
            for p in v['entities_stanford']['people']:
                if self.match_person_name(p['name']):
                    ln = p['name'].split()[-1].lower()
                    last_names.add(ln)
            for p in v['cap_entities_stanford']['people']:
                if self.match_person_name(p['name']):
                    ln = p['name'].split()[-1].lower()
                    last_names.add(ln)
        # ignore any place entities that have a match in the list of last names.
        for k, v in self.pages.items():
            for p in v['entities_stanford']['places']:
                if p['name'].lower() in last_names:
                    p['ignore'] = True
            for p in v['cap_entities_stanford']['places']:
                if p['name'].lower() in last_names:
                    p['ignore'] = True

    def match_person_name(self, person_name):
        person_name = person_name.upper()
        s = person_name.split()
        if len(s) > 1:
            return s[0] in self.firstnames
        else:
            return False

    def load_names(self):
        self.firstnames = []
        with open('./data/resources/male_firstnames.txt', 'r') as f:
            for x in f:
                self.firstnames.append(x.rstrip())