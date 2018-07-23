# Collection of the frequently called functions we'll be using for entity linking

from wikidata.client import Client
from nltk.corpus import stopwords

import nltk.tokenize
import os
import pywikibot
import wikipedia
import ujson

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
        self.ent_dict = dict(ujson.load(open(self.path)))

    def save_dictionary(self):
        """
        :action: Loads json file into dictionary
        :return: None
        """
        with open(self.path, 'w') as outfile:
            ujson.dump(self.ent_dict, outfile)

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

    @staticmethod
    def page_title_to_political_party(title):
        """
        :param title: A string page title.
        :return: A string representing the political party or affiliation of the entity described in the wikipage, if
                available. Otherwise, None.
        """
        site = pywikibot.Site("en", "wikipedia")
        page = pywikibot.Page(site, title)
        page = pywikibot.ItemPage.fromPage(page).get()

        try:
            party_page = page['claims']['P102'][0].getTarget().get()
        except (KeyError, pywikibot.NoPage):
            # No political party listed for this figure, so return None.
            return None

        # The English labels are usually a list, but sometimes appear as a string.
        english_labels = party_page['labels']['en']
        if isinstance(english_labels, list):
            return english_labels[0]
        elif isinstance(english_labels, str):
            return english_labels
        else:
            return None


    def entity_to_political_party(self, entity, building_dict=True, lookup_enabled=True, dict_allowed=True):
        """
        Given an entity, return the political affiliation of that entity if one is available. Otherwise, return
        'None found'.
        :param entity: A tuple of strings containing the name of a detected entity and its type, such as
        ('Barack Obama', 'PERSON')
        :param building_dict: If true, then newly discovered entities will be added to our
        :param lookup_enabled: Allows looking up terms not already in our dictionary of previous viewed
        entities on Wikipedia. Due to the unavoidable delay which comes with pulling data from Wikipedia,
        and the sheer number of entities mentioned in any given comment chain, this variable is here to
        be disabled in a production setting to speed up the final results.
        :param dict_allowed: Allows the dictionary of already seen entities to be used or disallowed, only used
        in testing.
        :return: A tuple of two strings, the full entity discovered and the party of this entity, if a politically
        affiliated full entity was found. Otherwise, None is returned.
        """

        entity_name, ent_type = entity

        # If already in dictionary, return dict entry instead of looking on Wikipedia
        if dict_allowed and entity_name.lower() in self.ent_dict:
            try:
                if "None" in self.ent_dict[entity_name.lower()][1]:
                    return None
                else:
                    return tuple(self.ent_dict[entity_name.lower()])
            except TypeError:
                return None
        elif lookup_enabled:
            pages = wikipedia.search(entity_name)

            """
            In the present incarnation of this project, we are focused on the political parties of
            only individuals, so other type of entities can be removed. Of course, the mention of
            geopolitical entities does have a certain political connotation, so this feature may be 
            examined at a later point. 
            """
            if ent_type == 'PERSON':

                """
                It is very rare for the subject of a political discussion to not be in the first five results
                for their name on Wikipedia, in fact in the testing done several months ago that was never the 
                case. To save on execution time, we thus limit our exploration to the first five results with
                some semblance to the original query.
                """
                # Occasionally, stop-words such as 'the' are in entities, so these are removed.
                entity_name_components = [part for part in entity_name.split(' ')]

                page_titles = []
                for title in pages[:20]:
                    if len(page_titles) == 5:
                        break
                    if any(part_of_name in title for part_of_name in entity_name_components):
                        page_titles.append(title)

                for title in page_titles:
                    found_party = self.page_title_to_political_party(title)
                    if found_party:
                        if building_dict:
                            self.ent_dict[entity_name.lower()] = (title, found_party)
                            self.save_dictionary()
                        return title, found_party
                else:
                    if building_dict:
                        self.ent_dict[entity_name.lower()] = ('No political figure', 'None found')
                        self.save_dictionary()
        return None

    @staticmethod
    def political_party_to_value(party):
        """
        :param party: A string representing the name of a political party
        :return: An integer value [-1, 1] representing this affiliation.
        """
        # TODO: More nuanced approach, use wikipedia API rather than fixed values
        if party is not None:
            if 'republican' in party.lower():
                return 1
            elif 'democrat' in party.lower():
                return -1
        return 0
