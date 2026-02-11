"""
VigilAI - AI Copilot for Streamers
Entry point for the application
"""

import os
import asyncio
from dotenv import load_dotenv
from src.bot.main_bot import VigilAIBot

def main():
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ['TWITCH_TOKEN', 'BOT_NICK', 'INITIAL_CHANNEL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please configure your .env file (see .env.example for reference)")
        return
    
    # Get configuration from environment
    token = os.getenv('TWITCH_TOKEN')
    nick = os.getenv('BOT_NICK')
    channels = [os.getenv('INITIAL_CHANNEL')]
    
    print("🚀 Initializing VigilAI...")
    print(f"🤖 Bot: {nick}")
    print(f"📺 Channel: {channels[0]}")
    
    # Create and run bot
    # Fix for environments where no loop is set by default
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    bot = VigilAIBot(token=token, nick=nick, channels=channels)
    bot.run()

if __name__ == "__main__":
    main()
