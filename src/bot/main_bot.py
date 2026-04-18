"""
VigilAI Twitch Bot
Main bot implementation with TwitchIO
"""

import os
from twitchio.ext import commands
from src.models.local_brain import LocalBrain
from src.models.ollama_brain import OllamaBrain

import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("vigilai.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class VigilAIBot(commands.Bot):
    """
    VigilAI - The Cybernetic Sentinel
    Protects your chat and entertains your stream.
    """
    
    def __init__(self, token: str, nick: str, channels: list, client_secret: str = None, event_callback=None):
        # Initialize parent Bot class
        super().__init__(
            token=token,
            client_secret=client_secret, # Required for some operations
            prefix='!',
            initial_channels=channels
        )
        
        # Callback for web interface
        self.event_callback = event_callback
        
        # Configuration
        self.toxicity_threshold = float(os.getenv('TOXICITY_THRESHOLD', '0.90'))
        self.timeout_duration = int(os.getenv('TIMEOUT_DURATION', '600'))
        
        # Initialize Brains
        self.brain = LocalBrain()
        self.ollama = OllamaBrain(model="gemma4:31b-cloud")
        
    async def _emit_event(self, event_type: str, data: dict):
        """Helper to emit events to callback if it exists"""
        if self.event_callback:
            await self.event_callback(event_type, data)
        
    async def event_ready(self):
        """Called when bot successfully connects to Twitch"""
        logging.info(f'✅ Logged in as | {self.nick}')
        logging.info(f'🎯 Monitoring channels: {", ".join([ch.name for ch in self.connected_channels])}')
        logging.info(f'🛡️ Toxicity threshold: {self.toxicity_threshold * 100}%')
        print('⚡ VigilAI is now online. Security protocol active.')
        
        await self._emit_event("system", {
            "message": f"Connected to Twitch as {self.nick}",
            "channels": [ch.name for ch in self.connected_channels]
        })
    
    async def event_message(self, message):
        """
        Called when a message is sent in chat.
        Implements the 4-filter "Traffic Light" architecture:
          🟢 GREEN  — Whitelist (VIPs, Mods, Subs skip analysis)
          🔴 RED    — BERT score > 95% → immediate action
          🟡 YELLOW — BERT score 70-95% → consult Ollama LLM
          🔵 BLUE   — Personality response before timeout
        """
        # Ignore messages from the bot itself
        if message.echo:
            return
        
        # Process commands first
        await self.handle_commands(message)
        
        text = message.content
        author = message.author
        
        # ═══════════════════════════════════════════
        # 🟢 FILTER 1: GREEN — Whitelist
        # VIPs, Moderators, and Subscribers pass through.
        # ═══════════════════════════════════════════
        is_trusted = getattr(author, 'is_mod', False) or \
                     getattr(author, 'is_vip', False) or \
                     getattr(author, 'is_broadcaster', False)
        
        if is_trusted:
            logging.info(f"🟢 [{message.channel.name}] {author.name}: {text} (WHITELISTED)")
            await self._emit_event("analysis", {
                "user": author.name,
                "message": text,
                "bert_score": 0.0,
                "filter": "GREEN",
                "whitelisted": True,
                "timestamp": datetime.now().isoformat()
            })
            # Still allow personality interaction for trusted users
            if self.nick.lower() in text.lower():
                response = await self.ollama.generate_response(author.name, text)
                if response:
                    await message.channel.send(response)
                    logging.info(f"🤖 Bot Response: {response}")
                    await self._emit_event("bot_response", {
                        "reply": response,
                        "to_user": author.name
                    })
            return
        
        # ═══════════════════════════════════════════
        # 🔴 FILTER 2: RED — BERT Local Analysis
        # Fast toxicity scoring (~5ms). Cost: $0.
        # ═══════════════════════════════════════════
        score = self.brain.analyze(text)
        
        logging.info(f"📩 [{message.channel.name}] {author.name}: {text} (Toxicity: {score:.2%})")
        
        await self._emit_event("analysis", {
            "user": author.name,
            "message": text,
            "bert_score": score,
            "filter": "RED",
            "timestamp": datetime.now().isoformat()
        })
        
        # RED: Extremely toxic (>95%) — immediate action, no Ollama needed
        if score > 0.95:
            logging.warning(f"🔴 CRITICAL TOXICITY ({score:.2%}) from {author.name} — IMMEDIATE ACTION")
            
            await self._emit_event("system", {
                "message": f"🔴 CRITICAL: BERT score {score:.2%} exceeds 95% threshold. Immediate action."
            })
            await self._emit_event("analysis_update", {
                "user": author.name,
                "ollama_verdict": "skipped",
                "final_decision": "TOXIC",
                "filter": "RED"
            })
            
            await self._timeout_user(message, score, "RED")
            return
        
        # ═══════════════════════════════════════════
        # 🟡 FILTER 3: YELLOW — Ollama LLM Consultation
        # Ambiguous messages (70-95%) need context analysis.
        # ═══════════════════════════════════════════
        if score > 0.70:
            logging.warning(f"🟡 Ambiguous message ({score:.2%}) from {author.name} — consulting Ollama...")
            
            await self._emit_event("system", {
                "message": f"🟡 Ambiguous content ({score:.2%}). Consulting LLM for context analysis..."
            })
            
            sentiment = await self.ollama.analyze_complex_sentiment(text)
            logging.info(f"🧠 Ollama Verdict: {sentiment.upper()}")
            
            await self._emit_event("analysis_update", {
                "user": author.name,
                "ollama_verdict": sentiment,
                "final_decision": "TOXIC" if sentiment == 'toxic' else "SAFE",
                "filter": "YELLOW"
            })
            
            if sentiment == 'toxic':
                logging.info(f"🚨 TOXIC VERDICT CONFIRMED by Ollama for {author.name}")
                await self._timeout_user(message, score, "YELLOW")
                return
            else:
                logging.info(f"✅ Ollama judged as SAFE: {text}")
                await self._emit_event("system", {
                    "message": f"✅ {author.name}'s message cleared by LLM (context/humor)."
                })
        
        # ═══════════════════════════════════════════
        # 🔵 FILTER 4: BLUE — Personality / Interaction
        # Bot responds when mentioned.
        # ═══════════════════════════════════════════
        if self.nick.lower() in text.lower():
            response = await self.ollama.generate_response(author.name, text)
            if response:
                await message.channel.send(response)
                logging.info(f"🔵 Bot Response to {author.name}: {response}")
                await self._emit_event("bot_response", {
                    "reply": response,
                    "to_user": author.name
                })

    async def _timeout_user(self, message, score, filter_source="RED"):
        """
        🔵 BLUE FILTER integrated: generates a personality response
        before timing out the user.
        """
        author = message.author
        
        try:
            # 🔵 BLUE: Generate a witty response before timeout
            try:
                roast = await self.ollama.generate_response(
                    author.name,
                    f"This user just said something toxic: '{message.content}'. Give a short, witty roast before they get timed out."
                )
                if roast:
                    await message.channel.send(roast)
                    logging.info(f"🔵 Personality roast: {roast}")
                    await self._emit_event("bot_response", {
                        "reply": roast,
                        "to_user": author.name,
                        "filter": "BLUE"
                    })
            except Exception as e:
                logging.warning(f"⚠️ Could not generate roast: {e}")
            
            # Execute timeout
            await message.channel.send(
                f"/timeout {author.name} {self.timeout_duration} "
                f"Toxicity detected by VigilAI (Score: {score:.2%})"
            )
            await message.channel.send("🛡️ Amenaza neutralizada.")
            
            logging.info(
                f'🚫 ACTION [{filter_source}]: User {author.name} timed out '
                f'for {self.timeout_duration}s. Reason: High Toxicity ({score:.2%})'
            )
            
            await self._emit_event("action", {
                "action": "TIMEOUT",
                "user": author.name,
                "duration": self.timeout_duration,
                "reason": f"High Toxicity ({score:.2%})",
                "filter": filter_source
            })
            
        except Exception as e:
            logging.error(f'❌ Error timing out user {author.name}: {e}')
    
    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context):
        """Test command to check bot responsiveness"""
        latency = round(self.latency * 1000) if self.latency else 0
        await ctx.send(f'🏓 Pong! Latencia: {latency}ms | Estado: Operacional')
    
    @commands.command(name='status')
    async def status(self, ctx: commands.Context):
        """Check VigilAI status and configuration"""
        if not (ctx.author.is_mod or ctx.author.is_broadcaster):
            return
        
        await ctx.send(
            f'🛡️ VigilAI activo | '
            f'Umbral: {self.toxicity_threshold * 100}% | '
            f'Timeout: {self.timeout_duration}s'
        )
