from collections import Counter
from json.decoder import JSONDecodeError
from nltk.corpus import stopwords
from sys import stderr
from utilities.api_keys import *
from urllib.error import URLError
from utilities.reddit_toolkit import RedditExplorer
from utilities.sentiment_toolkit import SentimentClassifier

import utilities.entity_toolkit as et

# Interface between flask and the core of this project.

class Interface(object):
    def __init__(self, abs_path=""):
        self.rt = RedditExplorer(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        self.ent_linker = et.EntityLinker(path=abs_path+'saved_data/entity_files/dict.json')
        self.sentiment = SentimentClassifier(load_path=abs_path + 'saved_data/trained_models/sentiment.tfl')
        self.stop_words = set(stopwords.words("english"))

    def flask_packaging(self, *, url, max_number=5, num_top_com=3):
        """
        Barring changes later in the project, this will be the sole method accessed by the Flask app.
        :param url: Article URL
        :return: A list of dictionaries for the contents of each article.
        """

        def markdown_to_html(markdown):
            """
            :param markdown: A reddit comment in markdown form
            :return: A string containing the passed comment, but with the markdown
                    tags replaced by html tags. I.E., ## becomes <h2>, ** becomes <i>,
                    etc.
            TODO: Complete this method.
            """
            pass

        def heuristic_for_comment(comment_text, comment_score, found_entities, parent_party=0):
            """
            :param comment_text: The text of a comment being analyzed
            :param comment_score: The integer score of the comment
            :param found_entities: Political entities identified in the comment
            :param parent_party: TODO: Implement parent party.
                                 In later incarnations of this program, this is set to take in the party
                                 of the parent comment (if this is a child comment) so that if there is no
                                 strong party mention within this comment, we can assume it is referring to the
                                 parent comment.
            :return:
            """
            try:
                affiliations = [self.ent_linker.entity_to_political_party(entity_name=entity)
                                for entity in found_entities]
                affiliations = [x for x in affiliations if x is not None]
            except (ConnectionError, URLError, JSONDecodeError) as e:
                # TODO: Diagnose these minor, occasional, and straggling errors.
                stderr.write("ERROR: Comment heuristic: {}\n".format(e))
                return 0

            if affiliations:
                party_count = Counter([affiliation[1] for affiliation in affiliations])
                most_common_party = party_count.most_common(1)[0][0]
                political_lean = self.ent_linker.political_party_to_value(most_common_party)
            else:
                return 0

            sentiment_score = self.sentiment.predict(comment_text)
            final_value = sentiment_score*comment_score*political_lean
            return final_value

        # Process the number of discussions described above
        discussions = []
        submissions = self.rt.discussions_of_url(url)
        for submission in submissions[:max_number]:
            sub = self.rt.parse_submission_info(submission)
            sub['top_comments'] = []
            all_comments = self.rt.all_comments_to_list(submission.comments, max_num_comments=100)

            # In some subreddits, comment scores are hidden for the first several hours. We can't analyze
            # these, so they aren't returned in all comments.
            if len(all_comments) > 0:
                comment_entities = self.ent_linker.identify_entities(all_comments)

                # Generate word-specific details for our showcased top comments.
                for i, comment in enumerate(self.rt.top_comments(submission.comments, num_top_com)):
                    comm = {
                            'words': comment.body.split(' '),
                            'score': comment.score,
                            'url': comment.permalink,
                            'sentiment': self.sentiment.predict(comment.body)
                            }

                    entities = comment_entities[i]

                    # We'll ignore thing that are upper-case too, partially because they're more likely to be
                    # false-positives, but also because people who type in caps aren't contributing to the conversation.
                    affiliations = [(entity, self.ent_linker.entity_to_political_party(entity_name=entity, ent_type=ent_type))
                                    for entity, ent_type in entities
                                    if self.ent_linker.entity_to_political_party(entity_name=entity, ent_type=type)
                                    and entity != entity.upper()]

                    for entity, affiliation in affiliations:
                        if "Republican Party" == affiliation[1]:
                            for word in affiliation[0].lower().split(' '):
                                sub['r_words'].add(word.lower())
                            for word in entity.lower().split(' '):
                                sub['r_words'].add(word.lower())
                        if "Democratic Party" == affiliation[1]:
                            for word in affiliation[0].lower().split(' '):
                                sub['l_words'].add(word.lower())
                            for word in entity.lower().split(' '):
                                sub['l_words'].add(word.lower())
                    sub['top_comments'].append(comm)

                # We limit the number of response comments for the sake of reducing computational complexity.
                for i, comm_tup in enumerate(all_comments):
                    comment, score = comm_tup
                    mod = heuristic_for_comment(comment, score, comment_entities[i])
                    if mod > 0:
                        sub['r_percentage'] += mod
                    else:
                        sub['l_percentage'] += abs(mod)

                total = (sub['r_percentage']+sub['l_percentage'])
                if total != 0:
                    sub['r_percentage'] = sub['r_percentage']/total*100
                    sub['l_percentage'] = sub['l_percentage']/total*100

            discussions.append(sub)

        return discussions

