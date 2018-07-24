import utilities.sentiment_toolkit as st
import os

from unittest import TestCase

# Move up to the parent directory so that we can access the correct files.
os.chdir("../")

# Disable the Tensorflow extraneous logs.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Due to the time involved, we don't test the construction of a new model and just load an existing one.
classifier = st.SentimentClassifier(load_path="saved_data/trained_models/model.tfl")


class BasicSentiment(TestCase):

    def test_positive_sentiment_identification(self):
        """
        Correctly identifies the contents of a sentence as having a positive sentiment.
        """

        positive_comments = [
            "This is really great!",
            "TFLearn makes LSTMs really easy to use, and was an excellent experience.",
            "Writing unit tests is the most fun I have had in my life!",
            "That is the cutest dog I have ever seen. I want to take him home, and give him only love."
        ]

        for comment in positive_comments:
            self.assertEqual(classifier.predict(comment), 1)

    def test_negative_sentiment_identification(self):
        """
        Correctly identifies the contents of a sentence as having a positive sentiment.
        """

        negative_comments = [
            "I really hate the smell of cucumbers.",
            "This whole thing was garbage. Just a pile of garbage without any redeeming quality.",
            "Writing these test cases is important, but I am so sick of it."
        ]

        for comment in negative_comments:
            self.assertTrue(classifier.predict(comment), -1)