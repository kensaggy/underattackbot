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
from docopt import docopt

__version__ = '0.0.1'

# Modify paths to match your setup
PIDFILE = '/home/bot/bot.pid'
LOGFILE = '/home/bot/bot.log'
logging.basicConfig(filename=LOGFILE,level=logging.DEBUG)

ACCESS_KEY = ''  # Edit these with values after you run get-access-tokens
ACCESS_SECRET = ''  # and this

API_KEY = ''  #Get from dev.twitter.com
API_SECRET = ''  # Same with this

DATA_API_URL = 'http://www.oref.org.il/WarningMessages/alerts.json'
HEADERS = { 'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36' }

TWEET_MSG = '%a, %d %b %Y, Local time is now %H:%M:%S Missiles are being launch against Israel citizens. #IsraelUnderFire'
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

    def __init__(self):
        pass


    def check_for_alarm(self):
        url = DATA_API_URL + '?_=' + str(int(time.time()))  #add cache busting
        request = urllib2.Request(url, None, HEADERS)
        answer = False
        try:
            response = urllib2.urlopen(request)
            data = response.read()
            obj = json.loads(data.decode('utf-16'))
            answer = True if obj['data'] else False
            logging.debug("Requesting url: %s data is: %s returning %s", url, obj['data'], answer)
        except:
            logging.excption('Problem retrieving status')

        return answer


    def tweet_it(self, test=False):
        msg = time.strftime(TWEET_MSG)
        if test:
            msg = "TEST ONLY!! " + msg
        logging.warning("Alarm was set off - tweeting message: %s", msg)
        Bot.api.update_status(msg)

    def run(self):
        try:
            while True:
                is_alarm = self.check_for_alarm()
                if is_alarm:
                    self.tweet_it()
                    time.sleep(30)
                else:
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
        bot.tweet_it(True)
    else:
        pid = str(os.getpid())

        if os.path.isfile(PIDFILE):
            print "%s already exists, exiting" % PIDFILE
            sys.exit(2)
        else:
            try:
                file(PIDFILE, 'w').write(pid)
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

