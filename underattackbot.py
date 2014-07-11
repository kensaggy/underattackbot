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
from itertools import izip_longest
from docopt import docopt

__version__ = '0.0.3'

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

TIME_FORMAT = '%d/%m/%y,%H:%M:%S'
TWEET_MSG = '{0} Missiles are being launched against {1}. #IsraelUnderFire #GazaUnderAttack #PreyForGaza #PrayForPalestina'
GENERIC_TWEET_MSG = '{0} Missiles are being launched against numerous cities right now!. #IsraelUnderFire #GazaUnderAttack #PreyForGaza #PrayForPalestina'
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
            answer = obj
            logging.debug("Requesting url: %s data is: %s , last alert id: %s,", url, obj['data'], obj['id'])
        except:
            logging.exception('Problem retrieving status')

        return answer

    def cities_by_location_indices(self, indices):
        """
        Returns a unique list of city names according to the indices parameter
        which is a some sort of weird geo-fence name
        """
        logging.debug("Got indices: %s", indices)
        # Extract english name of areas
        areas = [Bot.location_index[loc][0]['name_en'] for loc in indices]

        # Structure of the file is quite weird in some places :-/
        names = []
        for area in areas:
            t = [a.strip() for a in area.split(',')]
            names.append(t[1] if t[1] != 'Israel' else t[0])

        names = list(set(names)) #stupid uniquify trick
        logging.debug("Extracted names from indices: %s", names)
        return names

    def tweet_it(self, cities, test=False):
        if test:
            test_msg = "TEST Tweet!!"
            Bot.api.update_status(test_msg)
            return

        logging.debug("Running tweet_it on cities: %s", cities)
        #First create a list with only one tweet
        tweets = [TWEET_MSG.format(time.strftime(TIME_FORMAT), ",".join(cities))]
        tweets_over_140 = [tweet for tweet in tweets if len(tweet) > 140]
        n = len(cities)-1
        while tweets_over_140 and n >= 1:
            # Loop and break up the list of cities into smaller and smaller chunks but try to do it with minimum tweets as possible to avoid spamming
            args = [iter(cities)] * n
            subcities = list(izip_longest(fillvalue='', *args))
            tweets = [TWEET_MSG.format(time.strftime(TIME_FORMAT), ",".join(list(part))) for part in subcities]
            tweets_over_140 = [tweet for tweet in tweets if len(tweet) > 140]
            n = n - 1

        # Filter one last time to make sure we don't post more than 140 chars
        good_tweets = [t for t in tweets if len(t) <= 140]
        # If still nothing good to post, tweet the generic tweet - very unlikely
        if not good_tweets:
            good_tweets = [GENERIC_TWEET_MSG.format(time.strftime(TIME_FORMAT))]

        logging.warning("Alarm was set off - tweeting messages: %s", good_tweets)
        print "We have %s to tweet" % len(good_tweets)
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

