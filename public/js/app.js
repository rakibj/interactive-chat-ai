/**
 * app.js - Application initialization and orchestration
 * Handles startup, polling, error recovery
 */

class App {
    constructor() {
        this.refreshInterval = null;
        this.pollInterval = 2000;
        this.ready = false;
    }
    
    /**
     * Initialize application
     */
    async init() {
        console.log('🚀 Initializing app...');
        
        try {
            // 1. Check backend health
            await this.checkBackendHealth();
            
            // 2. Load initial state
            await this.loadInitialState();
            
            // 3. Connect WebSocket for real-time updates
            this.connectWebSocket();
            
            // 4. Start polling as fallback
            this.startPolling();
            
            // 5. Setup UI listeners
            this.setupUIListeners();
            
            this.ready = true;
            console.log('✅ App initialized');
            
        } catch (err) {
            console.error('❌ Initialization error:', err);
            UIManager.showError('Failed to initialize application');
            // Try again after delay
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
            }
            
            if (state.speaker) {
                updateSpeaker(state.speaker.speaker);
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
            
            UIManager.updateLastEventTime();
            
        } catch (err) {
            console.warn('⚠️ Failed to load initial state:', err.message);
            // This is not critical - WebSocket will provide updates
        }
    }
    
    /**
     * Connect to WebSocket server
     */
    connectWebSocket() {
        console.log('🔌 Connecting to WebSocket...');
        wsManager.connect();
    }
    
    /**
     * Start polling REST API as fallback
     */
    startPolling() {
        this.refreshInterval = setInterval(async () => {
            // Only poll if WebSocket is disconnected
            if (appState.wsConnected) return;
            
            try {
                const response = await fetch('http://localhost:8000/api/state', {
                    signal: AbortSignal.timeout(2000),
                });
                
                if (!response.ok) return;
                
                const state = await response.json();
                
                // Update speaker if changed
                if (state.speaker && state.speaker.speaker !== appState.activeSpeaker) {
                    updateSpeaker(state.speaker.speaker);
                    UIManager.updateSpeakerIndicator(state.speaker.speaker);
                }
                
                // Update phase if changed
                if (state.phase && state.phase.current_phase_id !== appState.currentPhase) {
                    updatePhase(state.phase);
                }
                
                UIManager.updateLastEventTime();
                
            } catch (err) {
                // Silently fail - we're just polling for update
            }
        }, this.pollInterval);
    }
    
    /**
     * Setup UI event listeners
     */
    setupUIListeners() {
        // Manual refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                refreshBtn.style.animation = 'spin 1s linear';
                await this.loadInitialState();
                setTimeout(() => {
                    refreshBtn.style.animation = 'none';
                }, 1000);
            });
        }
        
        // Add spin animation
        if (!document.querySelector('style[data-spin]')) {
            const style = document.createElement('style');
            style.setAttribute('data-spin', 'true');
            style.textContent = `
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    /**
     * Cleanup on page unload
     */
    cleanup() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (wsManager.ws) {
            wsManager.ws.close();
        }
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Note: app_live.js handles initialization with polling instead
        // Do NOT initialize app.js as it tries to use WebSocket
        console.log('⏳ Skipping legacy app.js - using app_live.js (polling) instead');
    });
} else {
    // DOM is already ready
    // Note: app_live.js handles initialization with polling instead
    console.log('⏳ Skipping legacy app.js - using app_live.js (polling) instead');
}
