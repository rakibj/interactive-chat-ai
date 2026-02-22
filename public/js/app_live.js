/**
 * Modern Live Polling App
 * - Auto-updates without page refresh
 * - Compatible with existing HTML structure
 * - Properly uses UIManager for all DOM updates
 * - AI auto-start support
 */

class ModernChatApp {
    constructor() {
        this.lastMessageCount = 0;
        this.stateHash = null;
        this.pollingInterval = null;
        this.isAutoStarted = false;
        this.apiBaseUrl = 'http://localhost:8000';
        
        console.log('🚀 Modern Live Chat App initialized (API: ' + this.apiBaseUrl + ')');
        this.init();
    }
    
    async init() {
        try {
            // Add visual debugging
            console.log('📐 VIEWPORT SIZE:', window.innerWidth, 'x', window.innerHeight);
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                const rect = mainContent.getBoundingClientRect();
                console.log('📐 .main-content position:', {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                });
                const gridStyle = window.getComputedStyle(mainContent);
                console.log('📐 .main-content grid-template-columns:', gridStyle.gridTemplateColumns);
            }
            
            const infoPanel = document.querySelector('.info-panel');
            if (infoPanel) {
                const rect = infoPanel.getBoundingClientRect();
                console.log('📐 .info-panel position:', {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    visible: rect.width > 0
                });
            }
            
            // Initial state load
            await this.updateState();
            
            // Start live polling
            this.startLivePolling();
            
            // Check for auto-start mode
            this.checkAutoStart();
            
            console.log('✅ Modern app ready - polling active every 750ms');
        } catch (error) {
            console.error('❌ Init error:', error);
        }
    }
    
    /**
     * Start live polling - polls every 750ms for state changes
     */
    startLivePolling() {
        this.pollingInterval = setInterval(async () => {
            try {
                await this.updateState();
            } catch (error) {
                console.warn('⚠️ Poll error:', error.message);
            }
        }, 750); // 750ms polling interval
        
        console.log('📡 Live polling started (750ms interval)');
    }
    
    /**
     * Update UI if state has changed
     * Uses hash comparison to detect changes efficiently
     */
    async updateState() {
        try {
            const response = await fetch(this.apiBaseUrl + '/api/state');
            const state = await response.json();
            
            // Calculate hash of current state
            const newHash = this.hashState(state);
            
            // Only update UI if state changed
            if (newHash !== this.stateHash) {
                console.log('🔄 State updated, refreshing UI...');
                this.stateHash = newHash;
                this.renderState(state);
            }
        } catch (error) {
            console.error('❌ State fetch failed:', error);
        }
    }
    
    /**
     * Simple hash function for state comparison
     */
    hashState(state) {
        const json = JSON.stringify(state);
        let hash = 0;
        for (let i = 0; i < json.length; i++) {
            const char = json.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return hash.toString();
    }
    
    /**
     * Render state to UI - uses UIManager for proper DOM updates
     */
    renderState(state) {
        try {
            console.log('🔄🔄🔄 RENDER STATE CALLED - state:', state);
            
            // Update speaker indicator
            if (state.speaker) {
                console.log('📢 Updating speaker:', state.speaker.speaker);
                UIManager.updateSpeakerIndicator(state.speaker.speaker);
            }
            
            // Update messages from history
            if (state.history) {
                this.renderMessages(state.history);
            }
            
            // Update phase info - THIS IS THE KEY PART
            if (state.phase) {
                console.log('🚀🚀🚀 CALLING UIManager.updatePhaseInfo with phase:', state.phase);
                UIManager.updatePhaseInfo(state.phase);
                console.log('✅ Phase info call completed');
            } else {
                console.warn('⚠️ No phase data in state!');
            }
            
            // Update turn summary (includes latency)
            if (state.history) {
                console.log('📊 Updating turn summary, turns count:', state.history.length);
                UIManager.updateTurnSummary(state.history);
                console.log('✅ Turn summary updated');
            }
            
            // Trigger auto-start if needed
            if (!this.isAutoStarted) {
                this.checkAutoStart();
            }
        } catch (error) {
            console.error('❌ Render error:', error);
            console.error('Stack:', error.stack);
        }
    }
    
    /**
     * Render messages - intelligently add new ones without clearing
     */
    renderMessages(history) {
        const chatBox = document.getElementById('chat-messages');
        if (!chatBox) return;
        
        // Remove welcome message on first turn
        const welcome = chatBox.querySelector('.welcome-message');
        if (welcome && history.length > 0) {
            welcome.remove();
        }
        
        // If no history, show welcome
        if (!history || history.length === 0) {
            if (!welcome) {
                chatBox.innerHTML = `
                    <div class="welcome-message">
                        <p>💬 Welcome to Interactive Chat AI</p>
                        <p>Messages will appear here...</p>
                    </div>
                `;
            }
            return;
        }
        
        // Add only new messages since last update
        const currentMessageCount = chatBox.querySelectorAll('.message').length;
        
        if (currentMessageCount < history.length) {
            // We have new messages - add them
            for (let i = currentMessageCount; i < history.length; i++) {
                const turn = history[i];
                
                if (turn.speaker === 'human') {
                    UIManager.addHumanMessage(turn.message, { latency_ms: turn.latency_ms });
                } else if (turn.speaker === 'ai') {
                    UIManager.addAIMessage(turn.message, { latency_ms: turn.latency_ms });
                }
            }
            
            console.log(`✅ Added ${history.length - currentMessageCount} new messages`);
        }
        
        this.lastMessageCount = history.length;
    }
    
    /**
     * Check if AI should auto-start
     */
    checkAutoStart() {
        try {
            const profileSelect = document.querySelector('select[name="profile"]');
            if (!profileSelect) return;
            
            const selectedProfile = profileSelect.value;
            
            // Fetch profile config to check authority
            fetch(this.apiBaseUrl + `/api/profile/${selectedProfile}`)
                .then(r => r.json())
                .then(profile => {
                    if (profile.authority === 'ai' && !this.isAutoStarted) {
                        console.log('🤖 AI authority detected - triggering auto-start...');
                        this.triggerAIStart();
                    }
                })
                .catch(err => console.warn('Could not check profile:', err));
        } catch (error) {
            console.warn('Auto-start check failed:', error);
        }
    }
    
    /**
     * Trigger AI to start conversation
     */
    async triggerAIStart() {
        try {
            const response = await fetch(this.apiBaseUrl + '/api/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                this.isAutoStarted = true;
                console.log('✅ AI auto-start triggered');
                
                // Force immediate update
                await this.updateState();
            } else {
                console.warn('⚠️ Failed to trigger AI start:', response.status);
            }
        } catch (error) {
            console.error('❌ AI start error:', error);
        }
    }
    
    /**
     * Stop polling (cleanup)
     */
    stop() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            console.log('🛑 Live polling stopped');
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.liveApp = new ModernChatApp();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.liveApp) {
        window.liveApp.stop();
    }
});
