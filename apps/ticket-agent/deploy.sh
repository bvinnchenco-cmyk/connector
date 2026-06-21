#!/bin/bash
# Auto-deploy webhook — вызывается GitHub при каждом push
cd /opt/concert-agent
git pull origin claude/cool-pasteur-tlqvge
pkill -f "python3 main.py" || true
cd apps/ticket-agent
nohup python3 main.py > /opt/concert-agent/bot.log 2>&1 &
echo "Bot restarted"
