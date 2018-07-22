import utilities.entity_toolkit as et
import os

from unittest import TestCase

# Move up to the parent directory so that we can access the correct files.
os.chdir("../")

ent = et.EntityLinker()


class NamedEntityDetection(TestCase):
    sent_ner = [
        "One president is Barack Obama, who was the president of the United States from 2008 until 2016.",
        "During World War II, the Nazi Party in Germany was headed by Adolf Hitler.",
        "Angela Merkel spoke today at a NATO summit in Brussels.",
        "John Klingelhofer seems like a smart hire for my company."
    ]

    sent_none = [
        "Yeah, I think that ice cream is pretty cool.",
        "My dog knows how to shake hands. It's quite impressive.",
        "Writing test cases is very boring.",
        "How many test sentences is an appropriate number, anyways?",
        "This many?",
        "How about this many?",
        "Surely this is enough.",
        "But we'll do one more just to err on the side of caution."
    ]

    def test_entity_recognition(self):
        """
        Should return the correct matching names for all of the entities in the sentences provided.
        """
        self.assertEqual(ent.identify_entities(self.sent_ner[0]),
                        [('Barack Obama', 'PERSON'), ('United States', 'GPE')])

        self.assertEqual(ent.identify_entities(self.sent_ner[1]),
                         [('Nazi Party', 'ORGANIZATION'), ('Germany', 'GPE'), ('Adolf Hitler', 'PERSON')])

        self.assertEqual(ent.identify_entities(self.sent_ner[2]),
                         [('Angela Merkel', 'PERSON'), ('NATO', 'ORGANIZATION'), ('Brussels', 'GPE')])

        self.assertEqual(ent.identify_entities(self.sent_ner[3]),
                         [('John Klingelhofer', 'PERSON')])

    def test_no_entities(self):
        """
        Tests that empty lists are returned when looking for these named entities.
        """
        for sentence in self.sent_none:
            self.assertFalse(ent.identify_entities(sentence))

