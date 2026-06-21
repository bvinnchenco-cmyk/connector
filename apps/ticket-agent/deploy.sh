#!/bin/bash
# Auto-deploy webhook — вызывается GitHub при каждом push
cd /opt/concert-agent
git pull origin claude/cool-pasteur-tlqvge
systemctl restart concert-bot
echo "Bot restarted via systemd"
