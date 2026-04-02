<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Ollama-Local_LLM-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama">
  <img src="https://img.shields.io/badge/BERT-Toxicity-FF6F00?style=for-the-badge&logo=huggingface&logoColor=white" alt="BERT">
  <img src="https://img.shields.io/badge/Twitch-Bot-9146FF?style=for-the-badge&logo=twitch&logoColor=white" alt="Twitch">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Cost-$0-00C853?style=for-the-badge" alt="$0 Cost">
</p>

<h1 align="center">🛡️ VigilAI</h1>

<p align="center">
  <strong>Autonomous AI-Powered Moderation System for Twitch</strong><br>
  <em>Protects your chat and entertains your stream — 100% local, $0 API costs.</em>
</p>

<p align="center">
  <img src="0402.gif" alt="VigilAI Demo" width="800">
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-web-console">Web Console</a> •
  <a href="#-deployment">Deployment</a> •
  <a href="#-roadmap">Roadmap</a>
</p>

---

## ⚡ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Hybrid AI Moderation** | Two-stage pipeline: fast BERT scoring + deep LLM reasoning |
| 🎭 **Context-Aware Analysis** | Understands sarcasm, slang, game context, and user history |
| 🤖 **Active Personality** | Responds to users with witty, in-character messages before timing them out |
| 🔒 **100% Private** | All models run locally — chat data never leaves your machine |
| 💸 **$0 Cost** | No API keys, no subscriptions. Open-source models on your hardware |
| 📺 **Live Web Console** | Real-time CRT-styled dashboard with WebSocket streaming |
| 🐳 **Docker Ready** | One-command deployment with containerized setup |
| 🌍 **Multilingual** | XLM-RoBERTa model supports toxicity detection across multiple languages |

---

## 🏗️ Architecture

VigilAI uses a **multi-layered AI pipeline** inspired by a traffic light metaphor. Each layer acts as a filter, escalating only when necessary:

```
   Message Received
         │
         ▼
  ┌──────────────┐
  │  🟢 GREEN    │  Whitelist — Mods, VIPs, Subs skip analysis
  │  FILTER      │  Cost: $0  |  Latency: 0ms
  └──────┬───────┘
         │ Not whitelisted
         ▼
  ┌──────────────┐
  │  🔴 RED      │  BERT (XLM-RoBERTa) — Local toxicity scoring
  │  FILTER      │  Score > 95% → Immediate timeout
  └──────┬───────┘  Cost: $0  |  Latency: ~5ms
         │ Score 30-95% or suspicious pattern
         ▼
  ┌──────────────┐
  │  🟡 YELLOW   │  Ollama LLM (Gemma 3 12B) — Contextual analysis
  │  FILTER      │  Considers: user history, game category, chat context
  └──────┬───────┘  Cost: $0  |  Latency: ~2-5s
         │ Verdict: toxic
         ▼
  ┌──────────────┐
  │  🔵 BLUE     │  Personality Response — Witty reply before timeout
  │  FILTER      │  "It's not just a mod — it's a personality"
  └──────────────┘  Cost: $0
```

### Key Design Decisions

- **BERT first, LLM second**: BERT runs in ~5ms and catches obvious toxicity. The LLM is only consulted for ambiguous cases, keeping inference costs low.
- **Per-user profiling**: The LLM tracks user behavior over time (repeat offenders, escalation patterns).
- **Game-aware context**: A message in "Just Chatting" is evaluated differently than in a competitive game lobby.
- **Critical pattern detection**: Regex-based pre-filter catches dangerous content (doxxing, self-harm, etc.) that ML models might miss.

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11+ | Core runtime |
| **Ollama** | Latest | Local LLM inference engine |
| **Git** | Any | To clone the repo |

### 1. Install Ollama & Pull Model

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama and pull the model
ollama serve
ollama pull gemma3:12b
```

### 2. Clone & Setup

```bash
git clone https://github.com/joorgecamacho/vigilai.git
cd vigilai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (~1GB first download for BERT model)
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your Twitch credentials:

```env
# Twitch API Credentials
TWITCH_CLIENT_ID=your_client_id          # From https://dev.twitch.tv/console
TWITCH_CLIENT_SECRET=your_client_secret
TWITCH_TOKEN=oauth:your_token            # From https://twitchtokengenerator.com
BOT_NICK=vigilai_bot
INITIAL_CHANNEL=your_channel

# AI Configuration
TOXICITY_THRESHOLD=0.85
TIMEOUT_DURATION=600
```

> **Required OAuth Scopes:** `chat:read`, `chat:edit`, `moderator:manage:banned_users`

### 4. Run

```bash
# CLI Mode — Direct Twitch connection
python main.py

# Web Console Mode — Dashboard with real-time logs
python web_server.py
```

---

## 🖥️ Web Console

VigilAI includes a **CRT-styled real-time web console** built with FastAPI + WebSockets.

### Features

- 🎯 **Live message analysis** with toxicity scores
- 📊 **Detection feed** showing flagged messages
- ⏱️ **60-second demo sessions** with auto-disconnect
- 🔌 **WebSocket streaming** for zero-latency log updates

### Running the Console

```bash
python web_server.py
# Open http://localhost:8000 in your browser
```

Enter any **live Twitch channel** name, click **INITIALIZE**, and watch the AI analyze messages in real time.

---

## 🧪 Testing

### Mock Chat Simulator (No Twitch Required)

Test the full AI pipeline locally without connecting to Twitch:

```bash
# Normal mode
python mock_chat.py

# Verbose mode — see full LLM reasoning
python mock_chat.py --log
```

#### Simulator Commands

| Command | Description |
|---------|-------------|
| `any text` | Send a message as the current user |
| `MOD: message` | Send as a moderator (bypasses filters) |
| `GAME: game name` | Change the simulated game category |
| `USER: username` | Change the simulated username |
| `exit` / `quit` | Exit the simulator |

#### Verbose Mode Output

With `--log`, the simulator shows the complete LLM reasoning chain:

```
📋 FULL LLM CONTEXT:
🎮 Game: League of Legends
👤 User Profile: First-time chatter, no prior warnings
💬 Recent Chat: [last 5 messages in context]
🧠 LLM REASONING: "The user said 'gg ez' which in gaming context is..."
```

> ⚠️ **First run** will download the BERT model (~1.1 GB). Subsequent runs are instant.

---

## 🐳 Docker

### Build & Run

```bash
# Build the image
docker build -t vigilai .

# Run with host networking (required for Ollama access)
docker run -it --network host --env-file .env vigilai

# Run Mock Chat inside Docker
docker run -it --network host vigilai python mock_chat.py
```

> **Note:** Ollama must be running on the host machine. The container connects via `localhost:11434`.

---

## 📺 Bot Commands

| Command | Description | Permissions |
|---------|-------------|-------------|
| `!ping` | Check if the bot is alive | Everyone |
| `!status` | Show current configuration and stats | Mods / Broadcaster |
| `@VigilAI` | Chat with the bot's personality | Everyone |

---

## 📂 Project Structure

```
vigilai/
├── main.py                  # CLI entry point (direct Twitch connection)
├── web_server.py            # Web console entry point (FastAPI + WebSockets)
├── mock_chat.py             # Local testing simulator
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container build configuration
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
│
├── src/
│   ├── __init__.py
│   ├── bot/
│   │   ├── __init__.py
│   │   └── main_bot.py      # TwitchIO bot — Traffic Light filter logic
│   └── models/
│       ├── __init__.py
│       ├── local_brain.py   # BERT (XLM-RoBERTa) — Fast toxicity scoring
│       └── ollama_brain.py  # Ollama LLM (Gemma 3) — Context-aware reasoning
│
└── static/
    ├── index.html           # Web console UI (CRT-styled)
    ├── css/
    │   └── styles.css       # Console styling
    └── js/
        └── app.js           # WebSocket client & UI logic
```

---

## 🖧 Edge Deployment

VigilAI is designed to run as an **always-on edge service** on a dedicated mini PC:

| Component | Setup |
|-----------|-------|
| **Hardware** | GMKtec Mini PC (16GB+ RAM, Intel N100 / AMD Ryzen) |
| **OS** | Ubuntu Server 24.04 LTS (headless, SSH-managed) |
| **Ollama** | Native install on host (systemd service, auto-start) |
| **VigilAI** | Docker Compose (`network_mode: host`, `restart: unless-stopped`) |
| **Network** | Cloudflare Tunnel — no open ports, encrypted end-to-end |
| **CI/CD** | Git-based deploy script (`scripts/deploy.sh`) |

### Boot Sequence

```
Power On → Ubuntu boots → systemd starts Ollama
→ Gemma 3 loads into RAM → Docker Compose starts VigilAI
→ Cloudflare Tunnel exposes console
→ Fully autonomous, zero human intervention
```

---

## 🛠️ Tech Stack

| Technology | Role |
|------------|------|
| **Python 3.11+** | Core language — async-first architecture |
| **TwitchIO 2.9** | Async Twitch bot framework |
| **Transformers + XLM-RoBERTa** | Local multilingual toxicity classification (HuggingFace) |
| **Ollama + Gemma 3 12B** | Local LLM for contextual reasoning & personality |
| **FastAPI** | Web console backend |
| **WebSockets** | Real-time log streaming |
| **Jinja2** | HTML templating |
| **Docker** | Containerized deployment |
| **Cloudflare Tunnel** | Secure remote access (no open ports) |

---

## 📈 Roadmap

### ✅ Sprint 1 — Core Security + Local Intelligence
- [x] TwitchIO bot connection
- [x] BERT toxicity model (XLM-RoBERTa)
- [x] Ollama LLM integration (Gemma 3)
- [x] Traffic Light filter architecture
- [x] Mock chat simulator
- [x] Docker containerization
- [x] Web console with real-time logs
- [x] Edge deployment (Mini PC + Cloudflare Tunnel)

### 🔨 Sprint 2 — Entertainment & Engagement
- [ ] Prediction system (`!apuesta`)
- [ ] Mini-game commands
- [ ] Autonomous chat dynamics
- [ ] Custom personality profiles

### 🔮 Sprint 3 — Senses
- [ ] Vision module (OpenCV + Llama Vision / GPT-4o)
- [ ] Voice module (Whisper Local)
- [ ] Screen-aware moderation context

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

1. Fork the repo
2. Create your branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source. See the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built by <a href="https://github.com/joorgecamacho">Jorge Camacho</a></strong><br>
  <em>VigilAI — Because your community deserves an intelligent guardian.</em>
</p>
