underattackbot
==============

A twitter bot that tweets whenever missiles are being fired on Israeli citizen population

## Roll your own
There are some basic steps you'll need to do to run your own bot:

1. First you'll need to create a twitter app and get your API key and API secret (google it).
2. Place them inside the python code where appropriate.
3. Then run ```./underattackbot.py gen-access-tokens``` from the terminal and follow the on screen instructions.
4. Save the output generated from the previous step and edit ```underattackbot.py``` and insert your ```ACCESS_KEY``` and ```ACCESS_SECRET```
5. (optional) run a tweet test by running ```./underattackbot.py tweet-test```
6. Added the watchdog.sh path to your crontab:

	```
	echo "* * * * * /path/to/watchdog.sh" > my.cron
	echo "" >> my.cron
	cp my.cron /etc/cron.d
	``` 

### Bot
The bot itself is very simple, only a few dozen lines and should be pretty self explanitory.

###Watchdog
This is a *very* basic watchdog script - it only test's for the existance of the pid file (that should be created by the python script upon start and deleted if closed cleanly (using Ctrl-C)).
If the pid file is not found it will run the python script with nohup and output redirects.

### Modify to your needs
You'll need to update the pid and script path's inside the watchdog.sh script.
Also if you want, you can change the log file name in side the bot code.

