# Collection of the frequently called functions we'll be using for entity linking

from nltk import ne_chunk, pos_tag
from nltk.tree import Tree
from wikidata.client import Client
from nltk.corpus import stopwords

import nltk.tokenize
import os
import requests
import wikipedia
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

    @staticmethod
    def identify_entities(comment):
        entities = []
        for sentence in nltk.sent_tokenize(comment):
            pending = None
            tagged_words = nltk.pos_tag(nltk.word_tokenize(sentence))
            for i, chunk in enumerate(nltk.ne_chunk(tagged_words)):
                if hasattr(chunk, 'label'):
                    """
                    Occasionally, names such as Angela Merkel are interpreted by the parser as two named entities,
                    Angela and Merkel. To resolve this issue, we hold the most recent entity before adding it to the 
                    returned list and check to see if the following entity is the next word, in which case we join the
                    two. 
                    """
                    if pending and pending[2] == i-1:
                        pending[0] += ' ' + ' '.join([c[0] for c in chunk])
                    else:
                        if pending:
                            entities.append(tuple(pending[:2]))
                        pending = [' '.join(c[0] for c in chunk), chunk.label(), i]
            if pending:
                entities.append(tuple(pending[:2]))
        return entities

    def get_all_entity_political_parties(self, entity_list):
        """
        :param entity_list: the list that is returned from identify_entity when passed an input String
        :return: a list of tuples containing the normalized name for the entity and their party
        """
        entity_party_list = []
        for e in entity_list:
            entity_party_list.append(self.entity_to_political_party(e[2]))
        return entity_party_list

    @staticmethod
    def page_title_to_political_party(title):
        """
        :param wiki: a valid WikipediaPage object
        :return: A string representing the political party or affiliation of the entity described in the wikipage, if
                available. Otherwise, None.
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
        party_entity = entity.getlist(client.get('P102'))[0]
        return str(party_entity.label)

    def entity_to_political_party(self, *, entity, ent_type='PERSON', building_dict=True, lookup_enabled=True):
        """
        Given an entity, return the political affiliation of that entity if one is available. Otherwise, return
        'None found'.
        :param entity: A string containing the entity to be recognized, i.e. 'Barack Obama'
        :param ent_type: String representing type of entity, such as a person ('PERSON') or geopolitical entity (GPE)
        :param building_dict: If true, then newly discovered entities will be added to our
        :return:
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
        elif lookup_enabled:
            pages = wikipedia.search(entity)

            if ent_type == 'PERSON':
                """
                With the exceptions of Morrissey and Madonna, most people have two words in their names
                """
                page_titles = [p.split() for p in pages]
                page_titles = [[w for w in title if '(' not in w] for title in page_titles]
                page_titles = [' '.join(title) for title in page_titles if len(title) >= 2]
            else:
                # TODO: ADD SUPPORT TYPES FOR NON-PERSON ENTITIES
                return None

            # Iterate through these titles
            for title in page_titles[:3]:
                found_party = self.page_title_to_political_party(title)
                if found_party:
                    if building_dict:
                        self.ent_dict[entity.lower()] = (title, found_party)
                        self.save_dictionary()
                    return title, found_party
            else:
                if building_dict:
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
