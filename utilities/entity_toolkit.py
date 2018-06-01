# Collection of the frequently called functions we'll be using for entity linking

from nltk import ne_chunk, pos_tag
from nltk.tree import Tree
from wikidata.client import Client
from nltk.corpus import stopwords

import nltk.tokenize
import os
import requests
import sys
import wikipedia
import urllib3
import json

from nltk.tokenize import word_tokenize

# Load/generate requisite nltk files
tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
stop_words = set(stopwords.words('english'))

class EntityLinker(object):
    def __init__(self, *, path='saved_data/entity_files/dict.json'):
        self.path = path

        # If file exists
        if os.path.isfile(path):
            # Load json file into dictionary
            self.load_dictionary()
        else:
            self.ent_dict = {}
            # Save dictionary to json file
            self.save_dictionary()

    # This tagger is a vestige of an earlier version, now used as a jumping off point as I supplant
    # the professor's API
    class Tagger(ChunkParserI):
        def __init__(self, data=None, test=False, force_new=False, **kwargs):
            def features(tokens, index, _):
                word, pos = tokens[index]
                prev_word, prev_pos = tokens[index - 1] if index > 0 else ('START', 'START')
                next_word, next_pos = tokens[index + 1] if index + 1 < len(tokens) else ('END', 'END')

                return {
                    'word': word,
                    'pos': pos,

                    'next-word': next_word,
                    'next-pos': next_pos,

                    'prev-word': prev_word,
                    'prev-pos': prev_pos,
                }

            if force_new or not os.path.isfile('cached_data/tagger.p'):
                # Default parameter described here rather in line so we can check file exists.
                data = conll2000.chunked_sents()
                data = list(data)
                # Randomize the order of the data
                random.shuffle(data)
                # Its a large corpus, so just 10% suffices.
                training_data = data[:int(.1 * len(data))]
                test_data = data[int(.1 * len(data)):]

                training_data = [tree2conlltags(sent) for sent in training_data]
                training_data = [[((word, pos), chunk) for word, pos, chunk in sent] for sent in training_data]

                self.feature_detector = features
                self.tagger = ClassifierBasedTagger(
                    train=training_data,
                    feature_detector=features,
                    **kwargs)

                # TODO: Find way to save classifier
                ''' 
                with open('cached_data/tagger.p', 'wb') as output:
                    pickle.dump(self.tagger, output, pickle.HIGHEST_PROTOCOL)
            else:
                with open('cached_data/tagger.p', 'rb') as input:
                    self.tagger = pickle.load(input)
                '''
            if test:
                print(self.evaluate(test_data))

        def parse(self, tagged_sent):
            chunks = self.tagger.tag(tagged_sent)

            # Transform the result from [((w1, t1), iob1), ...]
            # to the preferred list of triplets format [(w1, t1, iob1), ...]
            iob_triplets = [(w, t, c) for ((w, t), c) in chunks]

            # Transform the list of triplets to nltk.Tree format
            return conlltags2tree(iob_triplets)


    def preprocess(comment):
        # Break into individual sentences.
        sentences = [nltk.tokenize.word_tokenize(sentence) for sentence in tokenizer.tokenize(comment)]
        # Apply basic POS tagging.
        tagged_sentences = [nltk.pos_tag(sentence) for sentence in sentences]
        return tagged_sentences


    def load_dictionary(self):
        """
        :action: Saves dictionary to json file
        :return: None
        """
        self.ent_dict = dict(json.load(open(self.path)))

    def save_dictionary(self):
        """
        :action: Loads json file into dictionary
        :return: None
        """
        with open(self.path, 'w') as outfile:
            json.dump(self.ent_dict, outfile)


    def identify_all_entities(self, comments, filter=True):
        """
        :param comments: A list of comments
        :return: A list of entities and events in the order they appear in the comment section, by each comment
        """
        for comment in comments:



    def get_all_entity_political_parties(self, entity_list):
        """
        :param entityList: the list that is returned from identify_entity when passed an input String
        :return: a list of tuples containing the normalized name for the entity and their party
        """
        entity_party_list = []
        for e in entity_list:
            entity_party_list.append(self.entity_to_political_party(e[2]))
        return entity_party_list


    def page_title_to_political_party(self, title):
        """
        :param wiki: a valid WikipediaPage object
        :return: A string representing the political party or affiliation of the entity described in the wikipage, if
                available. Otherwise, a string 'None' is returned.
        """
        # Go through wikipedia json to get the id for wikidata
        try:
            resp = requests.get(url='https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageprops&titles=' + title)
        except:
            return None
        data = resp.json()
        page_data = data['query']['pages'][list(data['query']['pages'].keys())[0]]
        try:
            page_properties = page_data['pageprops']
            item_id = page_properties['wikibase_item']
        except KeyError:
            return 'None found'

        # With item id in tow, extract political affiliation
        client = Client()
        entity = client.get(item_id, load=True)
        try:
            party_entity = entity.getlist(client.get('P102'))[0]
            return str(party_entity.label)
        except:
            return 'None found'

    def get_continuous_chunks(self, text):
        chunked = ne_chunk(pos_tag(word_tokenize(text)))
        continuous_chunk = []
        current_chunk = []

        for i in chunked:
            if type(i) == Tree:
                current_chunk.append(" ".join([token for token, pos in i.leaves()]))
            elif current_chunk:
                named_entity = " ".join(current_chunk)
                if named_entity not in continuous_chunk:
                    continuous_chunk.append(named_entity)
                    current_chunk = []
            else:
                continue

        if continuous_chunk:
            named_entity = " ".join(current_chunk)
            if named_entity not in continuous_chunk:
                continuous_chunk.append(named_entity)

        return continuous_chunk

    def entity_to_political_party(self, *, entity, ent_type='PER', previous_subject_titles=[], train=True):
        """
        :param entity: String containing the name of the entity to be passed
        :return: A tuple containing the name of the matching page and that page's affiliation
        """
        # If already in dictionary, return dict entry instead of looking on Wikipedia
        if entity.lower() in self.ent_dict:
            try:
                if "None" in self.ent_dict[entity.lower()][1]:
                    return None
                else:
                    return self.ent_dict[entity.lower()]
            except TypeError:
                return None

        if train:
            try:
                pages = wikipedia.search(entity)
            except ConnectionError:
                return None
            # With the exception of Morrissey and Madonna, people have two words in their names
            if ent_type == 'PER':
                page_titles = [p.split() for p in pages]
                page_titles = [[w for w in title if '(' not in w] for title in page_titles]
                page_titles = [' '.join(title) for title in page_titles if len(title) >= 2]
            else:
                # TODO: ADD SUPPORT TYPES FOR NON-PERSON ENTITIES
                return None

            # Iterate through these titles
            for title in page_titles[:3]:
                found_party = self.page_title_to_political_party(title)
                if found_party != 'None found':
                    self.ent_dict[entity.lower()] = (title, found_party)
                    self.save_dictionary()
                    return title, found_party
            else:
                self.ent_dict[entity.lower()] = ('No political figure', 'None found')
                self.save_dictionary()
                return None
        else:
            return None

    def political_party_to_value(self, party):
        """
        :param party: A string representing the name of a political party
        :return: A value [-1.0, 1.0] representing this affiliation.
        """
        # TODO: More nuanced approach, use wikipedia API rather than fixed values
        if party is not None:
            if 'republican' in party.lower():
                return 1
            elif 'democrat' in party.lower():
                return -1

        return 0
