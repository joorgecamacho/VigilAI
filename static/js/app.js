/**
 * VigilAI — Console Application
 * Handles WebSocket communication, terminal logging,
 * detection feed, session timer, and system controls.
 */

// ============================================
// STATE
// ============================================
let isRunning = false;
let ws = null;
let timerInterval = null;
let timeLeft = 60;

// ============================================
// CLOCK
// ============================================
function updateClock() {
    document.getElementById('clock').innerText = new Date().toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// ============================================
// WEBSOCKET
// ============================================
function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws/logs`);

    ws.onopen = () => {
        const el = document.getElementById('conn-status');
        el.textContent = '● CONNECTED';
        el.className = 'conn-status on';
        logToTerminal('system', 'WebSocket connection established.');
    };

    ws.onmessage = (e) => handleEvent(JSON.parse(e.data));

    ws.onclose = () => {
        const el = document.getElementById('conn-status');
        el.textContent = '● DISCONNECTED';
        el.className = 'conn-status off';
    };
}
connectWS();

// ============================================
// EVENT ROUTER
// ============================================
function handleEvent(data) {
    if (data.type === 'log') {
        logToTerminal(data.level.toLowerCase(), data.message);

    } else if (data.type === 'analysis') {
        // ── Chat messages: dim and subtle ──
        const score = (data.data.bert_score * 100).toFixed(1);
        if (data.data.whitelisted) {
            logToTerminal('chat', `🟢 [${data.data.user}] "${data.data.message}"`);
        } else {
            let icon = '🟢';
            let level = 'chat';
            if (data.data.bert_score > 0.95) {
                icon = '🔴'; level = 'chat-danger';
            } else if (data.data.bert_score > 0.70) {
                icon = '🟡'; level = 'chat-warning';
            }
            logToTerminal(level, `${icon} [${data.data.user}] "${data.data.message}" → ${score}%`);
            if (data.data.bert_score > 0.3) {
                addDetection(data.data.user, 'SUSPICIOUS', data.data.message);
            }
        }

    } else if (data.type === 'analysis_update') {
        // ── System decision: bright ──
        const verdict = data.data.final_decision;
        const filter = data.data.filter || '';
        if (filter === 'RED') {
            logToTerminal('error', `🔴 RED FILTER — [${data.data.user}] Immediate action, Ollama skipped`);
        } else {
            logToTerminal(verdict === 'TOXIC' ? 'error' : 'info',
                `🟡 YELLOW FILTER — [${data.data.user}] LLM verdict: ${verdict}`);
        }

    } else if (data.type === 'system') {
        logToTerminal('system', data.data.message);

    } else if (data.type === 'action') {
        // ── Action: very prominent ──
        const filter = data.data.filter || 'RED';
        logToTerminal('action', `⚡ [${filter}] ${data.data.action} → ${data.data.user} | ${data.data.reason}`);
        addDetection(data.data.user, 'BANNED', data.data.reason);

    } else if (data.type === 'bot_response') {
        // ── Bot reply: blue highlight ──
        const icon = data.data.filter === 'BLUE' ? '🔵' : '🤖';
        logToTerminal('bot-reply', `${icon} Reply to ${data.data.to_user}: "${data.data.reply}"`);
    }
}

// ============================================
// TERMINAL LOGGER
// ============================================
function logToTerminal(level, message) {
    const terminal = document.getElementById('terminal-output');
    const empty = terminal.querySelector('.empty-state');
    if (empty) empty.remove();

    // Smart scroll: only auto-scroll if near bottom
    const nearBottom = (terminal.scrollHeight - terminal.scrollTop - terminal.clientHeight) < 60;

    const div = document.createElement('div');
    const ts = new Date().toLocaleTimeString();
    div.className = `log-entry ${level}`;
    div.innerHTML = `<span class="ts">${ts}</span><span class="lvl">[${level.toUpperCase()}]</span> ${message}`;
    terminal.appendChild(div);

    // Cap entries to prevent memory issues
    while (terminal.childElementCount > 500) terminal.removeChild(terminal.firstChild);
    if (nearBottom) terminal.scrollTop = terminal.scrollHeight;
}

// ============================================
// DETECTIONS FEED
// ============================================
function addDetection(user, status, snippet) {
    const list = document.getElementById('detections-list');
    const div = document.createElement('div');
    div.className = 'detection-item';
    const tagClass = status === 'BANNED' ? 'banned' : 'suspicious';
    div.innerHTML = `
        <div class="row">
            <span class="user">${user}</span>
            <span class="tag ${tagClass}">${status}</span>
        </div>
        <div class="snippet">"${snippet}"</div>
    `;
    list.prepend(div);
    // Keep max 15 items
    while (list.childElementCount > 15) list.removeChild(list.lastChild);
}

// ============================================
// SYSTEM CONTROLS
// ============================================
async function toggleSystem() {
    const btn = document.getElementById('btn-connect');
    const channel = document.getElementById('channel-input').value.trim();
    const timerEl = document.getElementById('timer-display');

    if (!isRunning) {
        if (!channel) {
            logToTerminal('error', 'Target channel required.');
            return;
        }

        // Clear everything on start
        document.getElementById('terminal-output').innerHTML = '';
        document.getElementById('detections-list').innerHTML = '';

        logToTerminal('system', `Initializing connection to channel: ${channel}...`);

        try {
            const res = await fetch(`/api/start?channel=${channel}`, { method: 'POST' });
            const json = await res.json();
            if (json.status === 'error') {
                logToTerminal('error', json.message);
                return;
            }

            isRunning = true;
            btn.textContent = 'TERMINATE';
            btn.classList.add('active');
            timerEl.classList.add('active');
            startTimer();
        } catch (e) {
            logToTerminal('error', 'Failed to contact backend.');
        }
    } else {
        logToTerminal('system', 'Terminating session...');
        stopSystem();
    }
}

async function stopSystem() {
    try { await fetch('/api/stop', { method: 'POST' }); } catch (e) { }
    resetUI();
}

function startTimer() {
    timeLeft = 60;
    const el = document.getElementById('timer-display');
    el.textContent = timeLeft;
    timerInterval = setInterval(() => {
        timeLeft--;
        el.textContent = timeLeft;
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            stopSystem();
        }
    }, 1000);
}

function resetUI() {
    isRunning = false;
    clearInterval(timerInterval);
    const btn = document.getElementById('btn-connect');
    const timerEl = document.getElementById('timer-display');
    btn.textContent = 'INITIALIZE';
    btn.classList.remove('active');
    timerEl.classList.remove('active');
    timerEl.textContent = '60';
    logToTerminal('system', 'Session terminated.');
}
