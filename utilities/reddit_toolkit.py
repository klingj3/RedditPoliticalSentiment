# Collection of tools for interacting with reddit's API

import praw
import utilities.political_tools as pt

from utilities.api_keys import *

reddit = praw.Reddit(user_agent="user", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

# Reddit data
def discussions_of_article(url):
    return reddit.subreddit('all').search('url:' + url)

def reddit_submission(passedURL):
    return reddit.submission(url=passedURL)

# Submission data
def submission_comments(submission):
    return submission.comments

def submission_url(submission):
    return submission.url

def submission_author(submission):
    return submission.author

def submission_title(submission):
    return submission.title

def submission_score(submission):
    return submission.score

# Comment data
def comment_author(comment):
    return comment.author

def comment_body(comment):
    return comment.body

def comment_score(comment):
    return comment.score

def comment_replies(comment):
    return comment.replies

def get_first_X_comments(commentList, X):
    return commentList[:X]

# Printing methods
def print_all_posts(article_url):
    stringList = []
    for post in discussions_of_article(article_url):
        temp = str(post.score) + " | (" + post.title + ") | r/" + str(post.subreddit)
        print(temp)
        stringList.append(temp)
    return stringList

def print_post_data(reddit_url):
    stringList = []
    submission = reddit_submission(reddit_url)
    temp = str(submission_score(submission)) + " | (" + submission_title(submission) + ")"
    print(temp)
    stringList.append(temp)
    print("")
    # print(identify_entity())
    print("---------------------------------------")
    commentList = []

    # Flatten the comment tree so it may be sorted
    for comment in submission.comments:
        # We do this check because discussion with many comments will have 'MoreComments' object which throws things off
        if type(comment).__name__ == "Comment":
            commentList.append(comment)

    # Sort comments by top, not by hot (which is the default)
    commentList.sort(key=lambda x: x.score, reverse=True)

    # Get the first up to 10 comments
    commentList = get_first_X_comments(commentList, 10)

    # Print each comment
    for comment in commentList:
        temp = str(comment_score(comment)) + " | (" + comment_body(comment) + ")"
        print(temp)
        stringList.append(temp)
        if(len(comment_replies(comment))>=1):
            temp = "     " + str(comment_replies(comment)[0].score) + " | (" + comment_replies(comment)[0].body + ")"
            print(temp)
            stringList.append(temp)

    return stringList

def flask_packaging(url, tagger, number=5, num_top_com=3):
    '''
    Barring changes later in the project, this will be the sole method accessed by the Flask app.
    :param url: Article URL
    :return: A list of dictionaries for the contents of each article.
    '''

    discussions = []
    submissions = discussions_of_article(url)
    count = 0
    for submission in submissions:
        count += 1
        dict = {}
        submission.comment_sort = 'top'
        dict['title'] = submission.title
        dict['subreddit'] = submission.subreddit
        dict['score'] = submission.score
        dict['url'] = 'https://reddit.com' + submission.permalink
        dict['comment_count'] = submission.num_comments
        dict['top_comments'] = []

        # Sometimes the top post is a sticky or mod post, which should be ignored.
        top_comments = []
        for comment in submission.comments[:num_top_com+1]:
            if comment.author.name != 'AutoModerator':
                top_comments.append(comment)

        for comment in top_comments:
            comm = {}
            comm['words'] = comment.body.split(' ')
            comm['score'] = comment.score
            comm['url'] = comment.permalink
            comm['r_words'] = set([])
            comm['l_words'] = set([])

            nps = []
            for tagged_sentence in tagger.preprocess(comment.body):
                fully_tagged = tagger.convert(tagger.parse(tagged_sentence))
                nps += tagger.get_nps(fully_tagged)
            affiliations = [pt.entity_to_political_party(np) for np in nps]
            for name, party in affiliations:
                if 'Republican' in party:
                    for word in name.split(' '):
                        comm['r_words'].add(word)
                if 'Democrat' in party:
                    for word in name.split(' '):
                        comm['l_words'].add(word)

            dict['top_comments'].append(comm)
        discussions.append(dict)
        if count > number:
            break
    return discussions

if __name__ == '__main__':
    tagger = pt.Tagger(test=False)
    flask_packaging("https://www.npr.org/2018/04/19/603696749/republicans-push-bill-to-protect-mueller-without-mcconnells-support", tagger)
