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
# Store active logs in memory (for new connections to see history)
LOG_BUFFER_SIZE = 50
log_buffer = deque(maxlen=LOG_BUFFER_SIZE)
# Active WebSocket connections
active_connections: list[WebSocket] = []
# Global Bot Instance
bot_instance: VigilAIBot = None
bot_task = None
bot_lock = asyncio.Lock()
class WebSocketLogHandler(logging.Handler):
    """Custom logging handler to send logs to WebSockets"""
    def emit(self, record):
        log_entry = self.format(record)
        # We want structured data if possible, but for now just text
        # If the message is a dict or json string, parse it? 
        # For simplicity, we'll send raw text and let frontend handle it, 
        # OR we can update the bot to send structured events.
        
        # Let's try to parse if it looks like our structured log
        msg = record.getMessage()
        
        event = {
            "type": "log",
            "level": record.levelname,
            "message": msg,
            "timestamp": record.created
        }
        
        # Add to buffer
        log_buffer.append(event)
        
        # Broadcast to all
        asyncio.create_task(broadcast_log(event))
async def broadcast_log(event: dict):
    """Send log event to all connected clients"""
    if not active_connections:
        return
    
    data = json.dumps(event)
    for connection in active_connections:
        try:
            await connection.send_text(data)
        except Exception:
            # Connection might be closed
            pass
# Add handler to root logger so we capture everything
ws_handler = WebSocketLogHandler()
ws_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ws_handler.setFormatter(formatter)
logging.getLogger().addHandler(ws_handler)
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    # Send history
    for event in log_buffer:
        await websocket.send_text(json.dumps(event))
        
    try:
        while True:
            # Keep connection alive headers
            await websocket.receive_text()
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)
async def bot_event_callback(event_type: str, data: dict):
    """Callback for the bot to send structured data to UI"""
    event = {
        "type": event_type,  # 'analysis', 'action', 'system'
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    }
    await broadcast_log(event)
@app.post("/api/start")
async def start_bot(channel: str):
    global bot_instance, bot_task
    
    async with bot_lock:
        if bot_instance:
             return {"status": "error", "message": "Bot is already running"}
        logger.info(f"Starting bot for channel: {channel}")
        
        # Validate env vars
        token = os.getenv("TWITCH_TOKEN")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        
        if not token:
            return {"status": "error", "message": "Missing TWITCH_TOKEN"}
        # Initialize Bot
        try:
            bot_instance = VigilAIBot(
                token=token,
                client_secret=client_secret,
                nick=os.getenv("BOT_NICK", "vigilai_bot"),
                channels=[channel],
                event_callback=bot_event_callback # Inject callback
            )
            
            # Run bot in background task
            bot_task = asyncio.create_task(bot_instance.start())
            
            # Schedule auto-stop after 60 seconds
            asyncio.create_task(stop_bot_after_timeout(60))
            
            return {"status": "success", "message": f"Bot started for channel {channel}"}
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            bot_instance = None
            return {"status": "error", "message": str(e)}
async def stop_bot_after_timeout(seconds: int):
    await asyncio.sleep(seconds)
    await stop_bot()
@app.post("/api/stop")
async def stop_bot():
    global bot_instance, bot_task
    
    async with bot_lock:
        if not bot_instance:
            return {"status": "ignored", "message": "Bot not running"}
            
        logger.info("Stopping bot...")
        try:
            await bot_instance.close()
        except Exception as e:
            logger.error(f"Error closing bot: {e}")
        
        if bot_task:
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
        
        bot_instance = None
        bot_task = None
        
        # Notify UI
        await bot_event_callback("system", {"message": "Session Ended. Bot disconnected."})
        
        return {"status": "success", "message": "Bot stopped"}
if __name__ == "__main__":
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)