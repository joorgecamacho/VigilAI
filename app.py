import asyncio
import logging
import os
import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from collections import deque
import json
from src.bot.main_bot import VigilAIBot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebServer")

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# Multitenant Architecture
LOG_BUFFER_SIZE = 50

class Session:
    def __init__(self):
        self.bot_instance: VigilAIBot = None
        self.bot_task = None
        self.active_connections: list[WebSocket] = []
        self.log_buffer = deque(maxlen=LOG_BUFFER_SIZE)
        self.lock = asyncio.Lock()

sessions: dict[str, Session] = {}

def get_session(session_id: str) -> Session:
    if session_id not in sessions:
        sessions[session_id] = Session()
    return sessions[session_id]

async def broadcast_log(session_id: str, event: dict):
    """Send log event to all connected clients in a specific session"""
    session = get_session(session_id)
    session.log_buffer.append(event)
    
    if not session.active_connections:
        return
    
    data = json.dumps(event)
    for connection in session.active_connections:
        try:
            await connection.send_text(data)
        except Exception:
            pass

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.websocket("/ws/logs/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = get_session(session_id)
    session.active_connections.append(websocket)
    
    # Send history
    for event in session.log_buffer:
        await websocket.send_text(json.dumps(event))
        
    try:
        while True:
            # Keep connection alive headers
            await websocket.receive_text()
    except Exception:
        if websocket in session.active_connections:
            session.active_connections.remove(websocket)

def create_bot_event_callback(session_id: str):
    async def bot_event_callback(event_type: str, data: dict):
        event = {
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await broadcast_log(session_id, event)
    return bot_event_callback

@app.post("/api/start")
async def start_bot(channel: str, session_id: str):
    session = get_session(session_id)
    
    async with session.lock:
        if session.bot_instance:
             return {"status": "error", "message": "Bot is already running for this session"}
        
        logger.info(f"Starting bot for channel: {channel} (Session: {session_id})")
        
        # Validate env vars
        token = os.getenv("TWITCH_TOKEN")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        
        if not token:
            return {"status": "error", "message": "Missing TWITCH_TOKEN"}

        # Initialize Bot
        try:
            session.bot_instance = VigilAIBot(
                token=token,
                client_secret=client_secret,
                nick=os.getenv("BOT_NICK", "vigilai_bot"),
                channels=[channel],
                event_callback=create_bot_event_callback(session_id)
            )
            
            # Run bot in background task
            session.bot_task = asyncio.create_task(session.bot_instance.start())
            
            # Schedule auto-stop after 60 seconds
            asyncio.create_task(stop_bot_after_timeout(60, session_id))
            
            return {"status": "success", "message": f"Bot started for channel {channel}"}
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            session.bot_instance = None
            return {"status": "error", "message": str(e)}

async def stop_bot_after_timeout(seconds: int, session_id: str):
    await asyncio.sleep(seconds)
    await stop_bot(session_id)

@app.post("/api/stop")
async def stop_bot(session_id: str):
    session = get_session(session_id)
    
    async with session.lock:
        if not session.bot_instance:
            return {"status": "ignored", "message": "Bot not running for this session"}
            
        logger.info(f"Stopping bot (Session: {session_id})...")
        try:
            await session.bot_instance.close()
        except Exception as e:
            logger.error(f"Error closing bot: {e}")
        
        if session.bot_task:
            session.bot_task.cancel()
            try:
                await session.bot_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Bot task exited with error: {e}")
        
        session.bot_instance = None
        session.bot_task = None
        
        # Notify UI
        callback = create_bot_event_callback(session_id)
        await callback("system", {"message": "Session Ended. Bot disconnected."})
        
        return {"status": "success", "message": "Bot stopped"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
