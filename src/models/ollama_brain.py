"""
VigilAI Ollama Integration
Context-aware moderation with:
- Per-user behavior profiling
- Game category awareness (Just Chatting vs Games)
- Chat history context
"""

import ollama
from typing import Optional
from collections import defaultdict

class OllamaBrain:
    """
    Context-aware moderation using local LLM.
    Considers: user history, game category, and chat context.
    """
    
    # Categories where comments are likely about the streamer
    STREAMER_FOCUSED_CATEGORIES = [
        "just chatting", "pools, hot tubs, and beaches", "asmr",
        "irl", "talk shows & podcasts", "music", "dj",
        "beauty & body art", "fitness & health"
    ]
    
    # Critical patterns that BERT misses - always TOXIC
    CRITICAL_PATTERNS = [
        # Suicide/violence incitement
        "suicídate", "suicidate", "mátate", "matate", "muérete", "muerete",
        "ojalá te mueras", "ojala te mueras",
        # Doxxing/real threats
        "encontrar tu dirección", "encontrar tu direccion", "sé dónde vives",
        "te voy a matar irl", "matarte irl",
        # CP/illegal content
        "porno infantil", "cp ", "menores de edad",
        # Sexist phrases (Spanish specific)
        "vete a la cocina", "enseña más", "solo tienes viewers por ser mujer",
        "estás muy buena", "estas muy buena", "fregona", "limpiar",
    ]

    # Suspicious patterns - Force Ollama analysis even if BERT is low
    # Catches soft harassment, flirting, and subtle insults
    SUSPICIOUS_PATTERNS = [
        # Flirting/Harassment
        "novio", "novia", "soltera", "casada", "guapa", "linda", "fea", "gorda",
        "pasa insta", "instagram", "whatsapp", "dm", "privado",
        "enseña", "muestra", "ver más", "ropa",
        "amor", "cita", "salir", "beso",
        # Subtle insults/Meta-comments
        "aburrido", "aburrida", "cierra", "cállate", "callate",
        "streamer de mierda", "das pena", "te odio",
        "nadie te ve", "nadie te quiere",
        "bot", "npc", "manco", "manca", "noob",
    ]

    def __init__(self, model: str = "gemma4:31b-cloud"):
        self.model = model
        self.user_history = defaultdict(list)
        self.user_warnings = defaultdict(int)
        self.recent_chat = []
        self.max_user_history = 20
        self.current_game = "Unknown"  # Current stream category
        print(f"🧠 Initializing Context-Aware Brain (Ollama: {self.model})...")
        
        try:
            models_info = ollama.list()
            # Handle both object and list response formats
            if isinstance(models_info, dict) and 'models' in models_info:
               available_models = [m['name'] for m in models_info['models']]
            else:
               available_models = [m['name'] for m in models_info]
            print(f"📋 Available Ollama models: {available_models}")
        except Exception as e:
            print(f"⚠️ Could not verify Ollama models: {e}")

    def set_game_category(self, game_name: str):
        """Update the current game/category for context"""
        self.current_game = game_name
        print(f"🎮 Game category updated: {game_name}")

    def _is_streamer_focused(self) -> bool:
        """Check if current category is streamer-focused (vs game-focused)"""
        return self.current_game.lower() in self.STREAMER_FOCUSED_CATEGORIES

    def check_critical_patterns(self, text: str) -> bool:
        """Check if message contains critical dangerous patterns that BERT misses"""
        text_lower = text.lower()
        for pattern in self.CRITICAL_PATTERNS:
            if pattern in text_lower:
                return True
        return False

    def check_suspicious_patterns(self, text: str) -> bool:
        """Check if message contains suspicious keywords that require context analysis"""
        text_lower = text.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in text_lower:
                return True
        return False

    def _get_user_profile(self, user_name: str) -> str:
        """Generate a profile summary for the user"""
        history = self.user_history.get(user_name, [])
        warnings = self.user_warnings.get(user_name, 0)
        
        if not history:
            return "Usuario nuevo, sin historial previo."
        
        msg_count = len(history)
        profile_parts = [f"Mensajes anteriores: {msg_count}"]
        
        if warnings > 0:
            profile_parts.append(f"⚠️ Advertencias previas: {warnings}")
        
        recent_msgs = history[-5:] if len(history) > 5 else history
        profile_parts.append("Últimos mensajes:")
        for msg in recent_msgs:
            profile_parts.append(f"  - \"{msg}\"")
        
        return "\n".join(profile_parts)

    def _build_context_prompt(self) -> str:
        """Build the context-aware system prompt"""
        
        # Determine category context
        if self._is_streamer_focused():
            category_context = f"""
CATEGORÍA ACTUAL: "{self.current_game}" (STREAMER EN CÁMARA)
⚠️ En esta categoría, los comentarios sobre físico/apariencia son sobre el STREAMER REAL.
- Comentarios sexuales o sobre el cuerpo -> TOXIC (acoso a persona real)
- "Estás muy guapa/o hoy" -> SAFE (cumplido inocente)
- "Menudas tetas" -> TOXIC (cosificación directa)
"""
        else:
            category_context = f"""
CATEGORÍA ACTUAL: "{self.current_game}" (VIDEOJUEGO)
En esta categoría hay personajes ficticios en pantalla.
- Comentarios sobre personajes del juego -> Generalmente SAFE
- "Menudas tetas tiene ese personaje" -> SAFE (comentario sobre ficción)
- Pero si dicen "streamer, enseña tetas" -> TOXIC (acoso al streamer)
- Clave: ¿Hablan del juego/personaje o del streamer directamente?
"""

        return f"""Eres un moderador de chat de Twitch en España/Latinoamérica.

CONTEXTO DEL STREAM:
{category_context}

CULTURA DE TWITCH:
- Los chats son INFORMALES con mucho humor negro, sarcasmo e ironía
- Las palabrotas (joder, mierda, hostia) son vocabulario NORMAL
- Criticar el gameplay con humor ácido es parte de la diversión
- "Trolear" al streamer de forma amistosa es común

SIEMPRE TOXIC (sin importar contexto):
- Insultos directos con intención de dañar
- Ataques a la familia del streamer
- Incitación al suicidio/violencia
- Slurs discriminatorios
- Acoso sexual HACIA EL STREAMER
- Contenido sobre abuso de menores

ANÁLISIS:
1. ¿El comentario es sobre el JUEGO/PERSONAJE o sobre el STREAMER?
2. ¿Hay intención de hacer daño o es humor de la comunidad?
3. ¿El historial del usuario sugiere que es un troll o un participante normal?
"""

    def _add_to_context(self, user: str, message: str, was_moderated: bool = False):
        """Add message to context"""
        prefix = "[MOD] " if was_moderated else ""
        self.recent_chat.append(f"[{user}]: {prefix}{message}")
        if len(self.recent_chat) > 20:
            self.recent_chat.pop(0)
        
        self.user_history[user].append(f"{prefix}{message}")
        if len(self.user_history[user]) > self.max_user_history:
            self.user_history[user].pop(0)

    async def generate_response(self, user_name: str, message: str, context: str = "general_chat") -> Optional[str]:
        """Generate a witty/sarcastic response"""
        system_prompt = (
            "Eres VigilAI, un moderador de Twitch cibernético y sarcástico. "
            "Responde BREVE (1 frase), con humor ácido. Terminología gamer/hacker."
        )

        try:
            client = ollama.AsyncClient()
            response = await client.chat(model=self.model, messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f"Usuario: {user_name}\nMensaje: {message}"},
            ])
            return response['message']['content']
        except Exception as e:
            print(f"❌ Error generating Ollama response: {e}")
            return None

    async def analyze_complex_sentiment(self, text: str, user_name: str = "Unknown") -> str:
        """
        Analyze with full context: user profile, game category, chat history.
        Returns: 'safe' or 'toxic'
        """
        user_profile = self._get_user_profile(user_name)
        recent_context = "\n".join(self.recent_chat[-5:]) if self.recent_chat else "No hay chat previo."
        system_prompt = self._build_context_prompt()
        
        try:
            client = ollama.AsyncClient()
            response = await client.chat(model=self.model, messages=[
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': f"""PERFIL DEL USUARIO:
{user_profile}

CHAT RECIENTE:
{recent_context}

MENSAJE A ANALIZAR:
Usuario: {user_name}
Mensaje: "{text}"

Considerando la categoría del stream ({self.current_game}), el historial del usuario, y el contexto del chat:
¿Este mensaje es SAFE o TOXIC?

Responde SOLO con: SAFE o TOXIC"""
                },
            ])
            
            content = response['message']['content'].strip().upper()
            result = 'toxic' if 'TOXIC' in content else 'safe'
            
            if result == 'toxic':
                self.user_warnings[user_name] += 1
            
            self._add_to_context(user_name, text, was_moderated=(result == 'toxic'))
            
            return result
            
        except Exception as e:
            print(f"❌ Error analyzing with Ollama: {e}")
            return 'toxic'

    async def analyze_with_reasoning(self, text: str, user_name: str = "Unknown") -> dict:
        """
        Analyze with FULL reasoning output for debugging/logging.
        Returns: dict with verdict, reasoning, and all context used
        """
        user_profile = self._get_user_profile(user_name)
        recent_context = "\n".join(self.recent_chat[-5:]) if self.recent_chat else "No hay chat previo."
        system_prompt = self._build_context_prompt()
        
        # Build the full prompt for logging
        user_prompt = f"""PERFIL DEL USUARIO:
{user_profile}

CHAT RECIENTE:
{recent_context}

MENSAJE A ANALIZAR:
Usuario: {user_name}
Mensaje: "{text}"

Considerando la categoría del stream ({self.current_game}), el historial del usuario, y el contexto del chat:

1. Primero, EXPLICA tu razonamiento paso a paso:
   - ¿De qué habla el mensaje?
   - ¿Hay intención de dañar o es humor?
   - ¿El historial del usuario sugiere algo?
   - ¿El contexto del juego importa?

2. Después, da tu VEREDICTO FINAL: SAFE o TOXIC"""

        result = {
            "user": user_name,
            "message": text,
            "game": self.current_game,
            "user_profile": user_profile,
            "recent_chat": recent_context,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_response": "",
            "reasoning": "",
            "verdict": "toxic"
        }
        
        try:
            client = ollama.AsyncClient()
            response = await client.chat(model=self.model, messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ])
            
            raw = response['message']['content']
            result["raw_response"] = raw
            result["reasoning"] = raw
            
            # Extract verdict
            if 'TOXIC' in raw.upper():
                result["verdict"] = 'toxic'
            else:
                result["verdict"] = 'safe'
            
            if result["verdict"] == 'toxic':
                self.user_warnings[user_name] += 1
            
            self._add_to_context(user_name, text, was_moderated=(result["verdict"] == 'toxic'))
            
            return result
            
        except Exception as e:
            result["reasoning"] = f"Error: {e}"
            return result
