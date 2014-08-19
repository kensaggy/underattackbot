#!/bin/bash

# Absolute path to bot.pid (and underattackbot.py)
# or relative path to user's home directory when running with crontab
BOT_PID=/home/bot/bot.pid

check_bot() {
    if [[ ! -f $BOT_PID ]];then
        # PID file not found - need to start the script again
        echo "Restarting bot"
        nohup /home/bot/underattackbot.py > /dev/null 2>&1 &
    fi
}

check_bot

