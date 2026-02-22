/**
 * app_new.js - Enhanced app with auto-updates and AI auto-start
 * Handles startup, live polling, auto-updates, and AI auto-start mode
 */

class App {
    constructor() {
        this.pollInterval = 1000; // More frequent updates
        this.liveUpdateInterval = null;
        this.ready = false;
        this.autoStartTriggered = false;
        this.lastStateHash = null;
    }
    
    /**
     * Initialize application
     */
    async init() {
        console.log('🚀 Initializing app with auto-updates...');
        
        try {
            // 1. Check backend health
            await this.checkBackendHealth();
            
            // 2. Load initial state
            await this.loadInitialState();
            
            // 3. Connect WebSocket for real-time updates
            this.connectWebSocket();
            
            // 4. Start AGGRESSIVE live polling for auto-updates
            this.startLivePolling();
            
            // 5. Setup UI listeners
            this.setupUIListeners();
            
            // 6. Check for AI auto-start
            await this.checkAutoStart();
            
            this.ready = true;
            console.log('✅ App initialized with live updates');
            
        } catch (err) {
            console.error('❌ Initialization error:', err);
            UIManager.showError('Failed to initialize application');
            setTimeout(() => this.init(), 5000);
        }
    }
    
    /**
     * Check backend health via REST API
     */
    async checkBackendHealth() {
        try {
            const response = await fetch('http://localhost:8000/api/health', {
                signal: AbortSignal.timeout(5000),
            });
            
            if (!response.ok) throw new Error('Backend returned error');
            
            const data = await response.json();
            console.log('✅ Backend healthy:', data);
            setBackendHealthy(true);
            UIManager.updateBackendStatus(true);
            
        } catch (err) {
            console.warn('⚠️ Backend health check failed:', err.message);
            setBackendHealthy(false);
            UIManager.updateBackendStatus(false);
            throw err;
        }
    }
    
    /**
     * Load initial state from server
     */
    async loadInitialState() {
        try {
            const response = await fetch('http://localhost:8000/api/state', {
                signal: AbortSignal.timeout(5000),
            });
            
            if (!response.ok) throw new Error('Failed to fetch state');
            
            const state = await response.json();
            console.log('📦 Initial state loaded:', state);
            
            // Update app state
            if (state.phase) {
                updatePhase(state.phase);
                UIManager.updatePhaseInfo(state.phase);
            }
            
            if (state.speaker) {
                updateSpeaker(state.speaker.speaker);
                UIManager.updateSpeakerIndicator(state.speaker.speaker);
            }
            
            if (state.history) {
                state.history.forEach(turn => {
                    if (turn.speaker === 'human') {
                        UIManager.addHumanMessage(turn.transcript, turn);
                    } else if (turn.speaker === 'ai') {
                        UIManager.addAIMessage(turn.transcript, turn);
                    }
                });
            }
            
            // Store state hash for change detection
            this.lastStateHash = JSON.stringify(state);
            
        } catch (err) {
            console.warn('⚠️ Failed to load initial state:', err.message);
        }
    }
    
    /**
     * Connect WebSocket for real-time updates
     */
    connectWebSocket() {
        const wsManager = new WebSocketManager();
        wsManager.connect();
    }
    
    /**
     * START AGGRESSIVE LIVE POLLING for auto-updates
     * Polls every 1 second for fresh state
     */
    startLivePolling() {
        console.log('🔄 Starting live polling for auto-updates...');
        
        this.liveUpdateInterval = setInterval(async () => {
            try {
                const response = await fetch('http://localhost:8000/api/state');
                if (!response.ok) return;
                
                const state = await response.json();
                const stateHash = JSON.stringify(state);
                
                // Only update if state changed
                if (stateHash !== this.lastStateHash) {
                    console.log('🔄 State updated, refreshing UI...');
                    this.updateUIFromState(state);
                    this.lastStateHash = stateHash;
                }
            } catch (err) {
                console.warn('⚠️ Polling error:', err.message);
            }
        }, this.pollInterval);
    }
    
    /**
     * Update UI from state (called by live polling)
     */
    updateUIFromState(state) {
        // Update phase
        if (state.phase) {
            updatePhase(state.phase);
            UIManager.updatePhaseInfo(state.phase);
        }
        
        // Update speaker indicator
        if (state.speaker) {
            updateSpeaker(state.speaker.speaker);
            UIManager.updateSpeakerIndicator(state.speaker.speaker);
        }
        
        // Add new messages
        if (state.history && state.history.length > 0) {
            const lastTurn = state.history[state.history.length - 1];
            
            // Check if this is a new message
            const existingMessages = document.querySelectorAll('.message');
            if (existingMessages.length < state.history.length) {
                if (lastTurn.speaker === 'human') {
                    UIManager.addHumanMessage(lastTurn.transcript, lastTurn);
                } else if (lastTurn.speaker === 'ai') {
                    UIManager.addAIMessage(lastTurn.transcript, lastTurn);
                }
            }
            
            // Update latency metrics
            if (lastTurn.metrics) {
                UIManager.displayTurnMetrics(lastTurn.metrics);
            }
        }
        
        // Update turn counter
        if (state.history) {
            const turnCount = Math.ceil(state.history.length / 2);
            const turnCounter = document.getElementById('turn-counter');
            if (turnCounter) {
                turnCounter.textContent = `Turn ${turnCount}`;
            }
        }
    }
    
    /**
     * Check if AI auto-start is enabled
     * If authority is 'ai', start conversation automatically
     */
    async checkAutoStart() {
        try {
            const response = await fetch('http://localhost:8000/api/state');
            if (!response.ok) return;
            
            const state = await response.json();
            
            // Check if authority is 'ai' (AI should start)
            if (state.authority === 'ai' && !this.autoStartTriggered) {
                console.log('🤖 AI auto-start mode detected, triggering conversation...');
                this.autoStartTriggered = true;
                
                // Trigger auto-start by sending a signal
                await this.triggerAIStart();
            }
        } catch (err) {
            console.warn('⚠️ Auto-start check failed:', err.message);
        }
    }
    
    /**
     * Trigger AI to start the conversation
     */
    async triggerAIStart() {
        try {
            const response = await fetch('http://localhost:8000/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ authority: 'ai' })
            });
            
            console.log('✅ AI start triggered:', response.status);
        } catch (err) {
            console.warn('⚠️ Failed to trigger AI start:', err.message);
        }
    }
    
    /**
     * Setup UI event listeners
     */
    setupUIListeners() {
        // Live indicator click
        const liveIndicator = document.getElementById('live-indicator');
        if (liveIndicator) {
            liveIndicator.title = 'Live updates: ' + (this.liveUpdateInterval ? 'ON' : 'OFF');
        }
        
        // Refresh button (manual)
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadInitialState());
        }
    }
    
    /**
     * Cleanup on shutdown
     */
    destroy() {
        if (this.liveUpdateInterval) {
            clearInterval(this.liveUpdateInterval);
        }
    }
}

// ====== UI Manager - Enhanced for live updates ======

class UIManager {
    static updateBackendStatus(healthy) {
        const badge = document.getElementById('backend-status');
        if (badge) {
            badge.className = 'status-badge ' + (healthy ? 'badge-healthy' : 'badge-disconnected');
            badge.textContent = healthy ? 'Healthy' : 'Offline';
        }
    }
    
    static updateSpeakerIndicator(speaker) {
        const indicator = document.getElementById('speaker-indicator');
        if (!indicator) return;
        
        indicator.classList.remove('speaker-silence', 'speaker-human', 'speaker-ai');
        
        let icon = '⏸️';
        let text = 'Ready';
        
        if (speaker === 'human') {
            indicator.classList.add('speaker-human');
            icon = '🎤';
            text = 'Listening to human';
        } else if (speaker === 'ai') {
            indicator.classList.add('speaker-ai');
            icon = '🤖';
            text = 'AI speaking';
        } else {
            indicator.classList.add('speaker-silence');
            icon = '⏸️';
            text = 'Ready to listen';
        }
        
        const iconEl = indicator.querySelector('.speaker-icon');
        const textEl = indicator.querySelector('.speaker-text');
        
        if (iconEl) iconEl.textContent = icon;
        if (textEl) textEl.textContent = text;
    }
    
    static addHumanMessage(text, metadata) {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        // Remove welcome message if exists
        const welcome = container.querySelector('.welcome-message');
        if (welcome) welcome.remove();
        
        const message = document.createElement('div');
        message.className = 'message human';
        
        let html = `<div class="message-bubble">${this.escapeHtml(text)}</div>`;
        
        if (metadata && metadata.timestamp) {
            const time = new Date(metadata.timestamp).toLocaleTimeString();
            html += `<div class="message-meta"><span>${time}</span></div>`;
        }
        
        message.innerHTML = html;
        container.appendChild(message);
        container.scrollTop = container.scrollHeight;
    }
    
    static addAIMessage(text, metadata) {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        // Remove welcome message if exists
        const welcome = container.querySelector('.welcome-message');
        if (welcome) welcome.remove();
        
        const message = document.createElement('div');
        message.className = 'message ai';
        
        let html = `<div class="message-bubble">${this.escapeHtml(text)}</div>`;
        
        if (metadata && metadata.timestamp) {
            const time = new Date(metadata.timestamp).toLocaleTimeString();
            html += `<div class="message-meta"><span>${time}</span></div>`;
        }
        
        message.innerHTML = html;
        container.appendChild(message);
        container.scrollTop = container.scrollHeight;
    }
    
    static displayTurnMetrics(metrics) {
        const asrEl = document.getElementById('latency-asr');
        const llmEl = document.getElementById('latency-llm');
        const totalEl = document.getElementById('latency-total');
        
        if (metrics.asr_latency_ms && asrEl) {
            asrEl.textContent = Math.round(metrics.asr_latency_ms) + 'ms';
        }
        
        if (metrics.llm_latency_ms && llmEl) {
            llmEl.textContent = Math.round(metrics.llm_latency_ms) + 'ms';
        }
        
        if (metrics.total_latency_ms && totalEl) {
            totalEl.textContent = Math.round(metrics.total_latency_ms) + 'ms';
        }
    }
    
    static updatePhaseInfo(phaseData) {
        if (!phaseData) return;
        
        const titleEl = document.getElementById('phase-title');
        const progressEl = document.getElementById('phase-progress');
        const currentEl = document.getElementById('phase-current');
        const totalEl = document.getElementById('phase-total');
        
        if (titleEl && phaseData.name) {
            titleEl.textContent = phaseData.name;
        }
        
        if (currentEl && phaseData.current) {
            currentEl.textContent = phaseData.current;
        }
        
        if (totalEl && phaseData.total) {
            totalEl.textContent = phaseData.total;
        }
    }
    
    static showError(message) {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        const error = document.createElement('div');
        error.className = 'error-message';
        error.textContent = '⚠️ ' + message;
        container.appendChild(error);
        
        setTimeout(() => error.remove(), 5000);
    }
    
    static escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// ====== WebSocket Manager - Enhanced ======

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }
    
    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//localhost:8000/ws`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleSignal(data);
                } catch (err) {
                    console.warn('⚠️ Failed to parse message:', err);
                }
            };
            
            this.ws.onerror = (err) => {
                console.error('❌ WebSocket error:', err);
            };
            
            this.ws.onclose = () => {
                console.log('⚠️ WebSocket disconnected');
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
        } catch (err) {
            console.error('❌ WebSocket connection failed:', err);
        }
    }
    
    handleSignal(signal) {
        console.log('📡 Signal:', signal.signal_type);
        
        if (signal.signal_type === 'VAD_SPEECH_STARTED') {
            UIManager.updateSpeakerIndicator('human');
        } else if (signal.signal_type === 'VAD_SPEECH_ENDED') {
            UIManager.updateSpeakerIndicator('silence');
        } else if (signal.signal_type === 'TTS_SPEAKING_STARTED') {
            UIManager.updateSpeakerIndicator('ai');
        } else if (signal.signal_type === 'TTS_SPEAKING_ENDED') {
            UIManager.updateSpeakerIndicator('silence');
        }
    }
    
    updateConnectionStatus(connected) {
        const indicator = document.getElementById('ws-indicator');
        const text = document.getElementById('connection-text');
        
        if (indicator) {
            indicator.classList.remove('connected', 'disconnected');
            indicator.classList.add(connected ? 'connected' : 'disconnected');
        }
        
        if (text) {
            text.textContent = connected ? 'Connected' : 'Reconnecting';
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            console.log(`🔄 Reconnecting in ${delay}ms...`);
            
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('❌ Max reconnection attempts reached');
        }
    }
}

// ====== Application Startup ======

document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM loaded, initializing app...');
    
    const app = new App();
    app.init();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        app.destroy();
    });
});

// Make App available globally for debugging
window.App = App;
window.UIManager = UIManager;
window.WebSocketManager = WebSocketManager;
