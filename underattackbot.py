#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UnderAttackBot

Usage:
    underattackbot.py
    underattackbot.py gen-access-tokens
    underattackbot.py tweet-test
    underattackbot.py (-h | --help)
    underattackbot.py --version

    Options:
      -h --help     Show this screen.
      --version     Show version.
"""
import os
import sys
import urllib2
import json
import tweepy
import time
import logging
import traceback
import yaml
import re
from math import floor
from itertools import izip_longest, chain
from docopt import docopt
from collections import defaultdict

__version__ = '0.0.4'

try:
    with open(sys.path[0] + "/config.yaml") as f:
        config = yaml.load(f)
except:
    print "Make sure config.yaml is present and readable"
    sys.exit(2)


# Modify paths to match your setup
PIDFILE = config['files']['pid_file']
LOGFILE = config['files']['log_file']
LOCATIONS_INDEX = config['files']['locations_file']

DEBUG = config['debug']

logging.basicConfig(filename=LOGFILE,level=logging.DEBUG)
if DEBUG:
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logging.getLogger('').addHandler(console)

ACCESS_KEY = config['keys']['access_key']
ACCESS_SECRET = config['keys']['access_secret']
API_KEY = config['keys']['api_key']
API_SECRET = config['keys']['api_secret']

DATA_API_URL = 'http://www.oref.org.il/WarningMessages/alerts.json'
EXAMPLE_FILE = config['dev']['stub_file']
HEADERS = { 'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36' }

TIME_FORMAT = '%b%d,%H:%M'
TWEET_MSG = '{0} #Hamas fired against citizens of {1}. #IsraelUnderFire bit.ly/retweet4israel'
ALTERNATE_TWEET_MSG = '{0} #Hamas fired against citizens of {1} & {2} others. #IsraelUnderFire bit.ly/retweet4israel'
GENERIC_TWEET_MSG = '{0} Missiles launched against numerous cities right now!. #IsraelUnderFire bit.ly/retweet4israel'
def get_access_tokens():
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    auth.secure = True
    auth_url = auth.get_authorization_url()
    print 'Please authorize: ' + auth_url
    verifier = raw_input('PIN: ').strip()
    auth.get_access_token(verifier)
    print "ACCESS_KEY = '%s'" % auth.access_token.key
    print "ACCESS_SECRET = '%s'" % auth.access_token.secret

class Bot:

    auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
    auth.secure = True
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
    api = tweepy.API(auth)
    location_index = None;

    def __init__(self):
        self.last_alert_id = 0
        with open(LOCATIONS_INDEX, "r") as loc:
            Bot.location_index = json.loads(loc.read())


    def check_for_alarm(self):
        answer = {'data': [], 'id': 0}
        try:
            if DEBUG:
                with open(EXAMPLE_FILE, 'r') as response:
                    data = response.read()
                    obj = json.loads(data.decode('utf-8'))
            else:
                url = DATA_API_URL + '?_=' + str(int(time.time()))  #add cache busting
                request = urllib2.Request(url, None, HEADERS)
                response = urllib2.urlopen(request)
                data = response.read()
                obj = json.loads(data.decode('utf-16'))
                logging.debug("Requesting url: %s data is: %s , last alert id: %s,", url, obj['data'], obj['id'])
            answer = obj
        except:
            logging.exception('Problem retrieving status')

        return answer

    def extract_city_name(self, long_name):
        """
        Take a string like "SomeName, Israel, Israel" or "SmallName, BiggerName, Israel"
        and attempt to extract the most relevant info,
        Structure of the file is quite weird in some places
        """
        elements = [part.strip() for part in long_name.split(',')]
        try:
            if len(elements) == 1 or len(elements[0].split(' ')) <= 2:
                return elements[0]
            elif elements[1] != 'Israel' and len(elements[1].split(' '))<=2:
                return elements[1]
            else:
                return None
        except IndexError:
            logging.warning("INDEXERROR for area : %s", area)

        return None

    def cities_by_location_indices(self, indices):
        """
        Returns a unique list of city names according to the indices parameter
        which is a some sort of weird geo-fence name
        """
        logging.debug("Got indices: %s", indices)
        # Extract english name of areas, exclude areas which names contains any Hebrew characters (some oddities)
        heb = re.compile(ur'^[^\u05d0-\u05ea]*$', re.UNICODE)
        areas = defaultdict(list)
        [areas[area].append(self.extract_city_name(city['name_en'])) for area in indices for city in Bot.location_index[area] if city['name_en'] != '' and heb.match(city['name_en'])]

        # group_of_cities is a list of lists. Every sublist is a list of cities for a particular area
        # Those cities names have already been cleaned by extract_city_name
        groups_of_cities = [v for k,v in areas.items()]

        # zipped_cities is a list of iterables, each one contains of element from each group
        # of group_of_cities, this allows to try and display at least on city from each area before displaying
        # other cities from the same area
        zipped_cities = [filter(None,l) for l in izip_longest(fillvalue='', *groups_of_cities)]

        # cities is a flattened list of that iterable generated from zipped_cities]
        cities = list(chain.from_iterable(zipped_cities))

        logging.debug("Extracted cities from indices: %s", cities)
        return cities

    def build_tweets(self, n, cities, alternate=False):
        """
        Build tweets with n cities (from cities list) in each tweet
        """
        args = [iter(cities)] * n
        grouped_cities = [filter(None,l) for l in izip_longest(fillvalue='', *args)]

        time_str = time.strftime(TIME_FORMAT)
        if alternate:
            others = sum(len(group) for group in grouped_cities[2:])
            tweets = [ALTERNATE_TWEET_MSG.format(time_str, ",".join(group), int(floor(others/2))) for group in grouped_cities[:2]]
            return tweets

        tweets = [TWEET_MSG.format(time_str, ",".join(group)) for group in grouped_cities]
        return tweets

    def tweet_it(self, cities, test=False):
        if test:
            test_msg = "TEST Tweet!!"
            Bot.api.update_status(test_msg)
            return

        #First create a list with only one tweet
        all_tweets = self.build_tweets(len(cities), cities)
        good_tweets = [tweet for tweet in all_tweets if len(tweet) <= 140]
        over_140 = [tweet for tweet in all_tweets if len(tweet) > 140]
        n = len(cities)-1
        while over_140 and n >= 1:
            # Loop and break up the list of cities into smaller and smaller chunks but try to do it with minimum tweets as possible to avoid spamming
            all_tweets = self.build_tweets(n, cities)

            over_140 = [tweet for tweet in all_tweets if len(tweet) > 140]
            good_tweets = [tweet for tweet in all_tweets if len(tweet) <= 140]
            # Once we have more than one valid tweet (140 chars) we need to represent the attack
            # in an alternate form - summing up the other cities we're no displaying
            # as we don't want to tweet too many tweets per missile launch
            # but we fallback to alternate form only when we've found the maximum group size n
            if len(good_tweets) > 2:
                logging.debug("More than 2 good tweets - Going into alternate form")
                logging.debug("Good tweets before alternate form: %s", good_tweets)
                # too many tweets to send at once, lets restructure them
                while len(good_tweets) > 2 or [len(t) for t in good_tweets if len(t) > 140]:
                    # First try to increase the group size by one, since the alternate form tweet
                    # has one less hashtag to make room for the extra string "& xx others"
                    # so we might be able to display one more city per tweet
                    good_tweets = self.build_tweets(n+1, cities, True)
                    n = n - 1
                logging.debug("Alternate tweets built: %s", good_tweets)
                # Break from main loop if we had too many tweets, but used alternate form
                # we don't need to try to optimize any more good tweets
                break
            n = n - 1

        # If still nothing good to post, tweet the generic tweet - Not sure this case can even exist
        # This case is mostly left over from previous forms of building the tweet list
        # But I don't have the energy or time to test if in fact every possible case will not trigger it
        if not good_tweets:
            good_tweets = [GENERIC_TWEET_MSG.format(time.strftime(TIME_FORMAT))]

        if not DEBUG:
            logging.warning("Alarm was set off - tweeting messages: %s", good_tweets)

        for msg in good_tweets:
            if DEBUG:
                print "Tweeting: ", msg
            else:
                Bot.api.update_status(msg)
                time.sleep(1)

    def run(self):
        try:
            while True:
                result = self.check_for_alarm()
                result_id = int(result['id'])
                if result['data'] and result_id > self.last_alert_id:
                    logging.debug("New alert with id: %s (old id: %s)", result_id, self.last_alert_id)
                    self.last_alert_id = result_id
                    indices = [item.strip() for d in result['data'] for item in d.split(',')]
                    cities = self.cities_by_location_indices(indices)
                    self.tweet_it(cities)

                time.sleep(2)
        except (KeyboardInterrupt, SystemExit):
            raise

def main():
    opts = docopt(__doc__, argv=None, help=True, version=__version__)
    if opts['gen-access-tokens']:
        get_access_tokens()
        sys.exit(0)

    bot = Bot()
    if opts['tweet-test']:
        bot.tweet_it([], test=True)
    else:
        pid = str(os.getpid())

        if os.path.isfile(PIDFILE):
            print "%s already exists, exiting" % PIDFILE
            sys.exit(2)
        else:
            try:
                with open(PIDFILE,'w') as p:
                    p.write(pid)
            except Exception,e:
                print "Could not create pid file"
                print traceback.format_exc()
                sys.exit(2)

        try:
            bot.run()
        except:
            os.unlink(PIDFILE)
            raise

if __name__ == "__main__":
    main()

