/**
 * app.js - Enhanced with live auto-updates and AI auto-start
 */

class App {
    constructor() {
        this.refreshInterval = null;
        this.pollInterval = 750; // Faster polling for live updates
        this.ready = false;
        this.autoStartTriggered = false;
        this.lastStateHash = null;
    }
    
    /**
     * Initialize application
     */
    async init() {
        console.log('🚀 Initializing app with live updates...');
        
        try {
            // 1. Check backend health
            await this.checkBackendHealth();
            
            // 2. Load initial state
            await this.loadInitialState();
            
            // 3. Connect WebSocket for real-time updates
            this.connectWebSocket();
            
            // 4. Start AGGRESSIVE live polling for auto-updates (replace setInterval polling)
            this.startLivePolling();
            
            // 5. Setup UI listeners
            this.setupUIListeners();
            
            // 6. Check for AI auto-start
            await this.checkAutoStart();
            
            this.ready = true;
            console.log('✅ App initialized with live updates enabled');
            
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
            console.log('✅ Backend healthy');
            setBackendHealthy(true);
            UIManager.updateBackendStatus(true);
            
        } catch (err) {
            console.warn('⚠️ Backend health check failed');
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
            console.log('📦 Initial state loaded');
            
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
            console.warn('⚠️ Failed to load initial state');
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
     * LIVE POLLING - Auto-updates without manual refresh
     * Polls server every 750ms for state changes
     */
    startLivePolling() {
        console.log('🔄 Starting live polling...');
        
        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch('http://localhost:8000/api/state');
                if (!response.ok) return;
                
                const state = await response.json();
                const stateHash = JSON.stringify(state);
                
                // Only update if state changed (prevents unnecessary DOM updates)
                if (stateHash !== this.lastStateHash) {
                    this.updateUILive(state);
                    this.lastStateHash = stateHash;
                }
            } catch (err) {
                // Silent fail - connection will update status
            }
        }, 750); // 750ms for responsive feel
    }
    
    /**
     * Update UI from polled state (live refresh)
     */
    updateUILive(state) {
        // Update phase
        if (state.phase) {
            updatePhase(state.phase);
            UIManager.updatePhaseInfo(state.phase);
        }
        
        // Update speaker
        if (state.speaker) {
            updateSpeaker(state.speaker.speaker);
            UIManager.updateSpeakerIndicator(state.speaker.speaker);
        }
        
        // Add new messages if any
        if (state.history && state.history.length > 0) {
            const messageCount = document.querySelectorAll('.message').length;
            
            // Add any new messages beyond what's displayed
            if (state.history.length > messageCount) {
                const lastTurn = state.history[state.history.length - 1];
                
                if (lastTurn.speaker === 'human') {
                    UIManager.addHumanMessage(lastTurn.transcript, lastTurn);
                } else if (lastTurn.speaker === 'ai') {
                    UIManager.addAIMessage(lastTurn.transcript, lastTurn);
                }
            }
            
            // Update metrics
            const lastTurn = state.history[state.history.length - 1];
            if (lastTurn && lastTurn.metrics) {
                UIManager.displayTurnMetrics(lastTurn.metrics);
            }
        }
    }
    
    /**
     * Check for AI auto-start mode
     * If authority is 'ai', start automatically without user input
     */
    async checkAutoStart() {
        try {
            const response = await fetch('http://localhost:8000/api/state');
            if (!response.ok) return;
            
            const state = await response.json();
            
            if (state.authority === 'ai' && !this.autoStartTriggered) {
                console.log('🤖 AI auto-start mode detected');
                this.autoStartTriggered = true;
                await this.triggerAIStart();
            }
        } catch (err) {
            console.warn('⚠️ Auto-start check failed');
        }
    }
    
    /**
     * Trigger AI to start conversation
     */
    async triggerAIStart() {
        try {
            const response = await fetch('http://localhost:8000/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            console.log('✅ AI start triggered');
        } catch (err) {
            console.warn('⚠️ AI start trigger failed');
        }
    }
    
    /**
     * Setup UI event listeners
     */
    setupUIListeners() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                console.log('🔄 Manual refresh');
                this.loadInitialState();
            });
        }
    }
    
    /**
     * Cleanup on shutdown
     */
    destroy() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
    }
}

// ====== Standalone Utilities ======

/**
 * Utility to update backend status display
 */
function updateBackendStatusDisplay(healthy) {
    const el = document.getElementById('backend-status');
    if (el) {
        el.textContent = healthy ? 'Healthy' : 'Offline';
        el.style.color = healthy ? '#10b981' : '#ef4444';
    }
}

// ====== Startup ======

document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM loaded, initializing...');
    
    const app = new App();
    app.init();
    
    window.addEventListener('beforeunload', () => {
        app.destroy();
    });
});

// Export for debugging
window.App = App;
