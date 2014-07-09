#!/bin/sh

BOT_PID=./bot.pid

check_bot() {
    if [[ ! -f $BOT_PID ]];then
        # PID file not found - need to start the script again
        echo "Restarting bot"
        nohup ./underattackbot.py > /dev/null 2>&1 &
    fi
}

check_bot

