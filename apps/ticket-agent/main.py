"""Entry point — loads .env and starts the Telegram bot."""
import sys
import os

# Add ticket-agent root to path so all imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from bot.telegram_bot import run_bot

if __name__ == "__main__":
    run_bot()
