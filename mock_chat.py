"""
VigilAI Mock Chat Simulator 🧪
Test your bot's logic locally without connecting to Twitch.

Usage:
  python mock_chat.py         # Normal mode
  python mock_chat.py --log   # Verbose mode (shows LLM reasoning)
"""

import os
import asyncio
import sys
import argparse

# Add src to path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.local_brain import LocalBrain
from src.models.ollama_brain import OllamaBrain

# Mock objects to simulate TwitchIO structures
class MockAuthor:
    def __init__(self, name, is_mod=False, is_broadcaster=False):
        self.name = name
        self.is_mod = is_mod
        self.is_broadcaster = is_broadcaster

class MockMessage:
    def __init__(self, content, author):
        self.content = content
        self.author = author
        self.echo = False

class MockVigilAI:
    def __init__(self, verbose=False):
        self.verbose = verbose
        print("🔧 Initializing Mock VigilAI...")
        
        # Load config (defaults for mock)
        self.toxicity_threshold = 0.90
        self.nick = "vigilai_bot"
        
        # Initialize Brains
        self.brain = LocalBrain()
        self.ollama = OllamaBrain(model="gemma3:12b")
        
        # Set default game category
        self.ollama.set_game_category("League of Legends")
        
        print("\n✅ Mock System Ready!")
        if verbose:
            print("📝 VERBOSE MODE: Showing full LLM reasoning")
        print("Commands:")
        print("  MOD: mensaje  - Simulate mod message")
        print("  GAME: nombre  - Change game category")
        print("  USER: nombre  - Change simulated username")
        print("-" * 60)
        
        self.current_user = "RandomUser"

    async def process_message(self, raw_input):
        # Handle special commands
        if raw_input.upper().startswith("GAME:"):
            game_name = raw_input[5:].strip()
            self.ollama.set_game_category(game_name)
            return
        
        if raw_input.upper().startswith("USER:"):
            self.current_user = raw_input[5:].strip()
            print(f"👤 Now simulating user: {self.current_user}")
            return
        
        # Parse simulated user
        if raw_input.startswith("MOD:"):
            content = raw_input[4:].strip()
            author = MockAuthor("AdminUser", is_mod=True)
        else:
            content = raw_input
            author = MockAuthor(self.current_user)
            
        message = MockMessage(content, author)
        
        print(f"\n📩 Incoming: [{author.name}]: {content}")
        
        # --- PURE BERT + OLLAMA MODERATION ---
        
        # FILTER 1: Whitelist
        if message.author.is_mod or message.author.is_broadcaster:
            print("🟢 FILTER 1: Whitelist passed (User is Mod/VIP)")
            if self.nick.lower() in message.content.lower():
                print("🔵 Generating reply...")
                response = self.ollama.generate_response(message.author.name, message.content)
                print(f"🤖 BOT REPLY: {response}")
            return
        
        # FILTER 0: Critical Patterns (suicide, doxxing, CP, etc.)
        if self.ollama.check_critical_patterns(content):
            print("🚨 FILTER 0: CRITICAL PATTERN DETECTED")
            print(f"🔨 ACTION: Immediate BAN {message.author.name}")
            return
            
        # FILTER 2: BERT Analysis
        score = self.brain.analyze(message.content)
        print(f"🔍 BERT Score: {score:.4f} (Threshold: {self.toxicity_threshold})")
        
        # Check if message mentions bot
        mentions_bot = self.nick.lower() in message.content.lower()
        
        # Any suspicious score (>0.30) OR Suspicious Pattern -> Consult Ollama
        # Lowered from 0.70 because BERT misses Spanish toxicity
        # Suspicious patterns catch soft harassment (flirting, meta-comments)
        is_suspicious = self.ollama.check_suspicious_patterns(message.content)
        
        if score > 0.30 or is_suspicious:
            print(f"🟡 FILTER 3: {'Suspicious Pattern' if is_suspicious else 'High Score'}, consulting Ollama...")
            
            if self.verbose:
                # Use the reasoning version
                result = self.ollama.analyze_with_reasoning(message.content, author.name)
                
                print("\n" + "="*60)
                print("📋 FULL LLM CONTEXT:")
                print("="*60)
                print(f"🎮 Game: {result['game']}")
                print(f"\n👤 User Profile:\n{result['user_profile']}")
                print(f"\n💬 Recent Chat:\n{result['recent_chat']}")
                print("\n" + "-"*60)
                print("🧠 LLM REASONING:")
                print("-"*60)
                print(result['reasoning'])
                print("="*60)
                
                verdict = result['verdict']
            else:
                verdict = self.ollama.analyze_complex_sentiment(message.content, author.name)
            
            print(f"🧠 Ollama Verdict: {verdict.upper()}")
            
            if verdict == 'toxic':
                print(f"🔨 ACTION: Timeout {message.author.name} (600s)")
                return
            else:
                print("✅ Ollama judged as SAFE (Context/Humor).")
        
        # Interaction / Personality
        if mentions_bot:
            print("🔵 Generating reply...")
            response = self.ollama.generate_response(message.author.name, message.content)
            print(f"🤖 BOT REPLY: {response}")
        elif score <= 0.70:
            print("⚪ Message SAFE. No action taken.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VigilAI Mock Chat Simulator')
    parser.add_argument('--log', '-l', action='store_true', 
                        help='Enable verbose logging (shows full LLM reasoning)')
    args = parser.parse_args()
    
    bot = MockVigilAI(verbose=args.log)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            user_input = input("\n👉 Enter message: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input.strip():
                continue
            
            loop.run_until_complete(bot.process_message(user_input))
            
        except KeyboardInterrupt:
            break
            
    print("\n👋 Byte bye!")
