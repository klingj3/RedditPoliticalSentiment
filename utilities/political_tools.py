# Collection of the frequently called functions we'll be using for entity linking

from collections import namedtuple
from nltk import ChunkParserI, ClassifierBasedTagger
from nltk.chunk import conlltags2tree, tree2conlltags
from nltk.corpus import conll2000
from nltk.stem.snowball import SnowballStemmer
from wikidata.client import Client

import bs4 as BeautifulSoup
import nltk
import nltk.data
import nltk.tokenize
import os
import re
import random
import requests
import string
import sys
import wikipedia

# Load/generate requisite nltk files
try:
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
except LookupError:
    nltk.download('punkt')
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

''' ADDTIONAL ENTITY TOOLS WITH THE PROF API, NOT TESTED OR INTEGRATED'''


def identify_entity(sentence):
    '''
    :param sentence:
    :return: A list of entities and events in the order they appear in the sentence
    '''
    serviceurl = 'https://blender04.cs.rpi.edu/~jih/cgi-bin/ere.py'
    payload = {'textcontent': sentence}
    # verify=False makes it so a HTTPS certificate is not required for the request
    r = requests.get(serviceurl, params=payload, verify=False)

    parsed_html = BeautifulSoup(r.text, "html.parser")
    # We are only concerned about the div lines as that's where the entities and events are in the HTML
    mentions = parsed_html.findAll('div')

    # Our list of entities and events
    taggedMentions = []

    # For each mention in sentence
    for i in mentions:
        # If it is an entity like "George Bush"
        if (str(i).startswith("<div id=\"d")):
            entityID = re.sub("(.+Entity ID: )|(<br/>.+)", "", str(i))
            entityMention = re.sub("(.+Entity Mention: )|(<br/>.+)", "", str(i))
            entityMentionType = re.sub("(.+Entity Mention Type: )|(<br/>.+)", "", str(i))
            entityType = re.sub("(.+Entity Type: )|(<br/>.+)", "", str(i))
            entityClass = re.sub("(.+Entity Class: )|(<br/>.+)", "", str(i))
            taggedMentions.append(['Entity', entityID, entityMention, entityMentionType, entityType, entityClass])
        # If it is an event like "meet"
        elif (str(i).startswith("<div id=\"e")):
            eventID = re.sub("(.+Event ID: )|(<br/>.+)", "", str(i))
            trigger = re.sub("(.+Trigger: )|(<br/>.+)", "", str(i))
            eventType = re.sub("(.+Event Type: )|(<br/>.+)", "", str(i))
            eventSubtype = re.sub("(.+Event Subtype: )|(<br/>.+)", "", str(i))
            genericity = re.sub("(.+Genericity: )|(<br/>.+)", "", str(i))
            modality = re.sub("(.+Modality: )|(<br/>.+)", "", str(i))
            polarity = re.sub("(.+Polarity: )|(<br/>.+)", "", str(i))
            tense = re.sub("(.+Tense: )|(<br/>.+)", "", str(i))
            arguments = re.sub("(.+Arguments: )|(<br/>.+)", "", str(i))
            person = re.sub("(.+;\">)|(</a>.+)", "", str(i))
            taggedMentions.append(['Event', eventID, trigger, eventType, eventSubtype, genericity, modality, polarity, tense, arguments, person])
    return taggedMentions

def page_title_to_political_party(title):
    '''
    :param wiki: a valid WikipediaPage object
    :return: A string representing the political party or affiliation of the entity described in the wikipage, if
            available. Otherwise, a string 'None' is returned.
    '''
    # Go through wikipedia json to get the id for wikidata
    resp = requests.get(url='https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageprops&titles=' + title)
    data = resp.json()
    page_data = data['query']['pages'][list(data['query']['pages'].keys())[0]]
    page_properties = page_data['pageprops']
    item_id = page_properties['wikibase_item']

    # With item id in tow, extract political affiliation
    client = Client()
    entity = client.get(item_id, load=True)
    try:
        party_entity = entity.getlist(client.get('P102'))[0]
        return str(party_entity.label)
    except:
        return 'None found'

def entity_to_political_party(entity, type='Person', previous_subject_titles=[]):
    '''
    :param entity: String containing the name of the entity to be passed
    :return: A tuple containing the name of the matching page and that page's affiliation
    '''
    pages = wikipedia.search(entity)
    # With the exception of Morrissey and Madonna, people have two words in their names
    if type =='Person':
        page_titles = [p.split() for p in pages]
        page_titles = [[w for w in title if '(' not in w] for title in page_titles]
        page_titles = [' '.join(title) for title in page_titles if len(title) >= 2]
    else:
        sys.stderr.write("ERROR: Only person entity-type supported")
        return None

    # If any of the results have been previously discussed in the thread, those should be given priority
    new_titles = [title for title in page_titles if title not in previous_subject_titles]
    page_titles = previous_subject_titles + new_titles

    # Iterate through these titles
    for title in page_titles:
        found_party = page_title_to_political_party(title)
        if found_party != 'None found':
            return title, found_party
    return 'No political figure', 'None found'

''' END UNTESTED ENTITIY TOOLS'''

# Load/generate requisite nltk files
try:
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
except LookupError:
    nltk.download('punkt')
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')


def page_title_to_political_party(title):
    '''
    :param wiki: a valid WikipediaPage object
    :return: A string representing the political party or affiliation of the entity described in the wikipage, if
            available. Otherwise, a string 'None' is returned.
    '''
    # Go through wikipedia json to get the id for wikidata
    resp = requests.get(url='https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageprops&titles=' + title)
    data = resp.json()
    page_data = data['query']['pages'][list(data['query']['pages'].keys())[0]]
    page_properties = page_data['pageprops']
    item_id = page_properties['wikibase_item']

    # With item id in tow, extract political affiliation
    client = Client()
    entity = client.get(item_id, load=True)
    try:
        party_entity = entity.getlist(client.get('P102'))[0]
        return str(party_entity.label)
    except:
        return 'None found'


def entity_to_political_party(entity, type='Person', previous_subject_titles=[]):
    '''
    :param entity: String containing the name of the entity to be passed
    :return: A tuple containing the name of the matching page and that page's affiliation
    '''
    pages = wikipedia.search(entity)
    # With the exception of Morrissey and Madonna, people have two words in their names
    if type =='Person':
        page_titles = [p.split() for p in pages]
        page_titles = [[w for w in title if '(' not in w] for title in page_titles]
        page_titles = [' '.join(title) for title in page_titles if len(title) >= 2]
    else:
        sys.stderr.write("ERROR: Only person entity-type supported")
        return None

    # If any of the results have been previously discussed in the thread, those should be given priority
    new_titles = [title for title in page_titles if title not in previous_subject_titles]
    page_titles = previous_subject_titles + new_titles

    # Iterate through these titles
    for title in page_titles:
        found_party = page_title_to_political_party(title)
        if found_party != 'None found':
            return title, found_party
    return 'No political figure', 'None found'


def political_party_to_value(party):
    '''
    :param party: A string representing the name of a political party
    :return: A value [-1.0, 1.0] representing this affiliation.
    '''
    # TODO: More nuanced approach, use wikipedia API rather than fixed values
    if 'republican' in party.lowercase():
        return 1
    elif 'democrat' in party.lowercase():
        return -1
    else:
        sys.stderr.write('ERROR: Method not yet completed.\n Cannot handle ' + party)
        return 0


class Tagger(ChunkParserI):
    def __init__(self, data=None, test=False, force_new=False, **kwargs):
        def features(tokens, index, _):
            word, pos = tokens[index]
            prev_word, prev_pos = tokens[index - 1] if index > 0 else ('START', 'START')
            next_word, next_pos = tokens[index + 1] if index + 1 < len(tokens) else ('END', 'END')

            next_next_word, next_next_pos = tokens[index + 2] if index + 2 < len(tokens) else ('END2', 'END2')
            prev_prev_word, prev_prev_pos = tokens[index - 2] if index > 1 else ('START2', 'START2')

            return {
                'word': word,
                'stem': SnowballStemmer("english").stem(word),
                'pos': pos,

                'next_word': next_word,
                'next_pos': next_pos,

                'two_words_ahead': next_next_word,
                'two_pos_ahead':next_next_pos,

                'prev_word': prev_word,
                'prev_pos': prev_pos,

                'two_words_past': prev_prev_word,
                'two_pos_past': prev_prev_pos,
            }
        if force_new or not os.path.isfile('cached_data/tagger.p'):
            # Default parameter described here rather in line so we can check file exists.
            try:
                data = conll2000.chunked_sents()
            except LookupError:
                sys.stderr.write('Warning: Default training data does not exist, downloading now...')
                sys.stderr.flush()
                nltk.download('conll2000')
                try:
                    data = conll2000.chunked_sents()
                except LookupError:
                    # If we fail a second time, then the download has failed.
                    sys.stderr.write('Error: Could not download training data.\nExiting.')
                    exit()
            data = list(data)
            # Randomize the order of the data
            random.shuffle(data)
            # Its a large corpus, so just 10% suffices.
            training_data = data[:int(.1*len(data))]

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
            test_data = data[int(.1*len(list(data))):]
            print(self.evaluate(test_data))

    def parse(self, tagged_sent):
        chunks = self.tagger.tag(tagged_sent)
        chunks = conlltags2tree([(w, t, c) for ((w, t), c) in chunks])
        return chunks

    def preprocess(self, comment):
        # Break into individual sentences.
        sentences = [nltk.tokenize.word_tokenize(sentence) for sentence in tokenizer.tokenize(comment)]
        # Apply basic POS tagging.
        try:
            tagged_sentences = [nltk.pos_tag(sentence) for sentence in sentences]
        except LookupError:
            nltk.download(nltk.download('averaged_perceptron_tagger'))
            tagged_sentences = [nltk.pos_tag(sentence) for sentence in sentences]
        return tagged_sentences

    def basic_parsing(self, tagged_sent):
        grammar = r"""
            NP: {<DT>?<JJ>*<NN|NNP>+}
            """
        parser = nltk.RegexpParser(grammar)
        return parser.parse(tagged_sent)


class SentimentClassifier():

    # Used to map NLTK type to sentiment database types
    nltk_map = {
        'NN': 'noun',
        'JJ': 'adj',
        'RB': 'adverb',
        'VB': 'verb',
    }

    def __int__(self, sentiment_file="sentiment_files/list.tff"):
        self.load_sentiments(sentiment_file)

    def load_sentiments(self, sentiment_file):
        '''
        :param sentiment_file: The file containing a list of the words used to assess sentiment.
        :return: A dictionary containing a link from each word to the Sentiment object. In the core of this assignment
                 only the polarity of this sentiment will be used, but we're linking to the whole object rather than
                 the sentiment exclusively since it allows some variations to be applied based on a variety of variables
                 at a later point, if desired.
        '''
        if not os.path.isfile(sentiment_file):
            sys.stderr.write("ERROR: Sentiment file " + sentiment_file + " does not exist.")
            exit(1)

        with open(sentiment_file) as file:
            lines = file.readlines()
        lines = [line.strip() for line in lines]

        self.sentiments = {}
        Sentiment = namedtuple('Sentiment', 'type word pos stemmed polarity')

        for line in lines:
            vars = line.split(' ')
            type = vars[0][vars[0].index('=') + 1:]
            word = vars[2][vars[2].index('=') + 1:]
            pos = vars[3][vars[3].index('=') + 1:]
            stemmed = True if vars[4][vars[4].index('=') + 1:][0] == 'y' else False
            # Two lines in the file, 5500 and 5501, have vars[5] = 'm' for some unknown reason. This is to avoid those.
            if vars[5] == 'm':
                priorpolarity = vars[6][vars[6].index('=') + 1:]
            else:
                priorpolarity = vars[5][vars[5].index('=') + 1:]
            self.sentiments[(word, pos)] = Sentiment(type, word, pos, stemmed, priorpolarity)
        if len(self.sentiments.items()) == 0:
            sys.stderr('ERROR: No lines could be read in the linked file, although the file does exist.')
            exit(2)

    def tally_word_sentiments(review, sentiment_dictionary):
        '''
        The most basic sentiment analysis to meet the requirements of this small assignment.
        :param paragraph: String to be reviewed.
        :return: A tuple containing the number of positive classified words, number of negative classified words, and total.
        '''
        # In this simple version, we don't care about the different sentences or anything, so just make a list of words.
        words = review.split(' ')

        # Used to map NLTK type to sentiment database types
        nltk_map = {
            'NN': 'noun',
            'JJ': 'adj',
            'RB': 'adverb',
            'VB': 'verb',
        }

        # If mistakenly passed an empty string, return 0s and avoid this upcoming computation
        if len(words) == 0:
            return 0, 0, 0

        # Fix numbers, which had no match in the dictionary.
        words = [w for w in words if not any(c.isdigit() for c in w)]
        # remove punctuation, and make lowercase for better dictionary integration
        for i, word in enumerate(words):
            words[i] = ''.join([c for c in word if c not in set(string.punctuation)]).lower()

        words = [w for w in words if len(w) > 0]
        posts = [nltk_map[t[1]] if t[1] in nltk_map.keys() else 'anypos' for t in nltk.pos_tag(words)]

        # Make pairs for the discovered types, but of course override the pos with 'anypos' if the sentiment lexicon
        # doesn't care about the position.
        word_pos_pair = [(word, pos) if (word, 'anypos') not in sentiment_dictionary else (word, 'anypos')
                         for word, pos in zip(words, posts)]

        print([pair for pair in word_pos_pair if pair in sentiment_dictionary and
               sentiment_dictionary[pair].polarity == 'positive'])
        positive_count = len([pair for pair in word_pos_pair if pair in sentiment_dictionary and
                              sentiment_dictionary[pair].polarity == 'positive'])
        negative_count = len([pair for pair in word_pos_pair if pair in sentiment_dictionary and
                              sentiment_dictionary[pair].polarity == 'negative'])
        total = len(words)

        return positive_count, negative_count, total

# Just to be used in testing.
if __name__ == '__main__':
    print("Stating example stage . . .")
    comment = "Test."
    tagger = Tagger(test=False)
    print(tagger.parse(tagger.preprocess(comment)[0]))
