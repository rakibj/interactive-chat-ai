/**
 * ui.js - DOM manipulation and visual updates
 * Handles all UI rendering based on state changes
 */

class UIManager {
    /**
     * Update speaker indicator with animation
     */
    static updateSpeakerIndicator(speaker) {
        const indicator = document.getElementById('speaker-indicator');
        if (!indicator) return;
        
        const icons = {
            'human': { icon: '🎤', text: `You're speaking` },
            'ai': { icon: '🤖', text: 'AI Speaking' },
            'silence': { icon: '⏸️', text: 'Listening' },
        };
        
        const config = icons[speaker] || icons.silence;
        
        // Update text
        const textEl = indicator.querySelector('.speaker-text');
        if (textEl) textEl.textContent = config.text;
        
        const iconEl = indicator.querySelector('.speaker-icon');
        if (iconEl) iconEl.textContent = config.icon;
        
        // Update class for styling
        indicator.className = `speaker-indicator speaker-${speaker}`;
    }
    
    /**
     * Stream AI response word by word
     */
    static streamAIResponse(textChunk) {
        const chatBox = document.getElementById('chat-messages');
        if (!chatBox) return;
        
        let aiMessage = chatBox.querySelector('.ai-message:last-child');
        
        // Create new AI message if needed
        if (!aiMessage || chatBox.querySelector('.human-message:last-child') === aiMessage) {
            aiMessage = document.createElement('div');
            aiMessage.className = 'ai-message';
            chatBox.appendChild(aiMessage);
        }
        
        // Append text (streaming effect)
        aiMessage.textContent += textChunk;
        
        // Auto-scroll to bottom
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    /**
     * Add human message to chat
     */
    static addHumanMessage(text, metadata = {}) {
        const chatBox = document.getElementById('chat-messages');
        if (!chatBox) return;
        
        // Remove welcome message on first turn
        const welcome = chatBox.querySelector('.welcome-message');
        if (welcome) welcome.remove();
        
        const message = document.createElement('div');
        message.className = 'message human-message';
        
        let content = `<div>${this.escapeHtml(text)}</div>`;
        if (metadata.latency_ms) {
            content += `<div class="message-meta">⏱️ ${Math.round(metadata.latency_ms)}ms</div>`;
        }
        
        message.innerHTML = content;
        chatBox.appendChild(message);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    /**
     * Add AI message to chat
     */
    static addAIMessage(text, metadata = {}) {
        const chatBox = document.getElementById('chat-messages');
        if (!chatBox) return;
        
        // Remove welcome message on first turn
        const welcome = chatBox.querySelector('.welcome-message');
        if (welcome) welcome.remove();
        
        const message = document.createElement('div');
        message.className = 'message ai-message';
        
        let content = `<div>${this.escapeHtml(text)}</div>`;
        if (metadata.latency_ms) {
            content += `<div class="message-meta">🤖 ${Math.round(metadata.latency_ms)}ms</div>`;
        }
        
        message.innerHTML = content;
        chatBox.appendChild(message);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    /**
     * Display turn latency metrics
     */
    static displayTurnMetrics(metrics) {
        const latency = document.getElementById('latency-display');
        if (!latency || !metrics) return;
        
        let display = '⏱️ ';
        if (metrics.transcription_ms) {
            display += `ASR: ${Math.round(metrics.transcription_ms)}ms`;
        }
        if (metrics.llm_generation_ms) {
            display += ` | LLM: ${Math.round(metrics.llm_generation_ms)}ms`;
        }
        if (metrics.total_latency_ms) {
            display += ` | Total: ${Math.round(metrics.total_latency_ms)}ms`;
        }
        
        latency.textContent = display;
    }
    
    /**
     * Update phase information and tracker
     */
    static updatePhaseInfo(phaseData) {
        console.log('📋 updatePhaseInfo called with:', phaseData);
        
        const phaseTitle = document.getElementById('phase-title');
        const phaseProgress = document.getElementById('phase-progress');
        const phaseTracker = document.getElementById('phase-tracker');
        const phaseSection = document.querySelector('.phase-section');
        const infoPanel = document.querySelector('.info-panel');
        
        console.log('Elements found:');
        console.log('  - phase-title:', !!phaseTitle);
        console.log('  - phase-progress:', !!phaseProgress);
        console.log('  - phase-tracker:', !!phaseTracker);
        console.log('  - phase-section:', !!phaseSection);
        console.log('  - info-panel:', !!infoPanel);
        
        if (infoPanel) {
            console.log('  - info-panel display:', window.getComputedStyle(infoPanel).display);
            console.log('  - info-panel visibility:', window.getComputedStyle(infoPanel).visibility);
        }
        if (phaseSection) {
            console.log('  - phase-section display:', window.getComputedStyle(phaseSection).display);
            console.log('  - phase-section height:', phaseSection.offsetHeight);
        }
        
        if (phaseTitle) {
            const newText = phaseData.current_phase_id || 'Unknown Phase';
            phaseTitle.textContent = newText;
            console.log('✅ Phase title set to:', newText);
        }
        
        if (phaseProgress) {
            const newText = `${phaseData.phase_index || 0}/${phaseData.total_phases || 0} phases`;
            phaseProgress.textContent = newText;
            console.log('✅ Phase progress set to:', newText);
        }
        
        if (phaseTracker && Array.isArray(phaseData.progress)) {
            console.log('📍 Populating phase tracker with', phaseData.progress.length, 'phases');
            phaseTracker.innerHTML = '';
            phaseData.progress.forEach((phase, idx) => {
                const phaseEl = document.createElement('div');
                phaseEl.className = `phase-item ${phase.status || 'upcoming'}`;
                
                // Get status badge
                const statusBadge = {
                    'completed': '✅',
                    'active': '🔵',
                    'upcoming': '⭕'
                }[phase.status] || '❓';
                
                // Display name or ID
                const displayName = phase.name || phase.id || 'Unknown';
                let durationText = '';
                if (phase.duration_sec) {
                    durationText = `<span class="phase-duration">${phase.duration_sec.toFixed(1)}s</span>`;
                }
                
                phaseEl.innerHTML = `
                    <span class="phase-status-badge">${statusBadge}</span>
                    <span class="phase-display-name">${this.escapeHtml(displayName)}</span>
                    ${durationText}
                `;
                phaseTracker.appendChild(phaseEl);
                if (idx === 0) {
                    console.log('   Created first item:', phaseEl.className, phaseEl.textContent);
                }
            });
            console.log('✅ Phase tracker populated with content length:', phaseTracker.innerHTML.length);
            console.log('   Children count in tracker:', phaseTracker.children.length);
            
            // Check tracker visibility
            console.log('   Tracker display:', window.getComputedStyle(phaseTracker).display);
            console.log('   Tracker visibility:', window.getComputedStyle(phaseTracker).visibility);
        } else if (!Array.isArray(phaseData.progress)) {
            console.warn('⚠️ phaseData.progress is not an array:', phaseData.progress);
        }
    }
    
    /**
     * Update turn summary
     */
    static updateTurnSummary(turns) {
        const summary = document.getElementById('turn-summary');
        if (!summary) return;
        
        if (!turns || turns.length === 0) {
            summary.innerHTML = '<p>No turns yet</p>';
            return;
        }
        
        const lastTurn = turns[turns.length - 1];
        let html = `<p><strong>Turn #${lastTurn.turn_id}:</strong></p>`;
        html += `<p>Last: ${formatTime(lastTurn.timestamp)}</p>`;
        
        if (lastTurn.speaker) {
            html += `<p>Speaker: ${getSpeakerName(lastTurn.speaker)}</p>`;
        }
        
        if (lastTurn.latency_ms) {
            html += `<p>Latency: ${Math.round(lastTurn.latency_ms)}ms</p>`;
        }
        
        summary.innerHTML = html;
    }
    
    /**
     * Update connection status indicator
     */
    static updateConnectionStatus(connected) {
        const indicator = document.getElementById('ws-indicator');
        const text = document.getElementById('connection-text');
        const wsStatus = document.getElementById('ws-status');
        
        if (indicator) {
            indicator.className = `indicator ${connected ? 'connected' : 'disconnected'}`;
        }
        
        if (text) {
            text.textContent = connected ? 'Connected' : 'Disconnected';
        }
        
        if (wsStatus) {
            wsStatus.textContent = connected ? '✅ Live' : '❌ Offline';
        }
    }
    
    /**
     * Update backend health status
     */
    static updateBackendStatus(healthy) {
        const status = document.getElementById('backend-status');
        if (status) {
            status.textContent = healthy ? '✅ Running' : '⚠️ Unavailable';
            status.style.color = healthy ? '#22c55e' : '#f59e0b';
        }
    }
    
    /**
     * Update session ID display
     */
    static updateSessionId(sessionId) {
        const sessionEl = document.getElementById('session-id');
        if (sessionEl) {
            sessionEl.textContent = sessionId ? sessionId.substring(0, 8) + '...' : '—';
            sessionEl.title = sessionId || 'No session';
        }
    }
    
    /**
     * Update last update timestamp
     */
    static updateLastEventTime() {
        const timeEl = document.getElementById('last-update');
        if (timeEl) {
            timeEl.textContent = formatTime(new Date());
        }
    }
    
    /**
     * Clear all messages
     */
    static clearMessages() {
        const chatBox = document.getElementById('chat-messages');
        if (chatBox) {
            chatBox.innerHTML = `
                <div class="welcome-message">
                    <p>👋 Welcome to Interactive Chat AI</p>
                    <p>Waiting for conversation to start...</p>
                </div>
            `;
        }
    }
    
    /**
     * Show error message
     */
    static showError(message) {
        console.error('UI Error:', message);
        const chatBox = document.getElementById('chat-messages');
        if (chatBox) {
            const errorEl = document.createElement('div');
            errorEl.style.cssText = 'background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; padding: 12px; margin: 8px 0; border-radius: 4px;';
            errorEl.innerHTML = `<strong>❌ Error:</strong> ${this.escapeHtml(message)}`;
            chatBox.appendChild(errorEl);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }
    
    /**
     * HTML escape utility
     */
    static escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;',
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Subscribe to state changes and update UI
on('speakerChanged', speaker => {
    UIManager.updateSpeakerIndicator(speaker);
    UIManager.updateLastEventTime();
});

on('phaseChanged', phaseData => {
    UIManager.updatePhaseInfo(phaseData);
});

on('turnAdded', turn => {
    UIManager.updateTurnSummary(appState.turns);
    UIManager.updateLastEventTime();
});

on('connectionChanged', ({ connected, sessionId }) => {
    UIManager.updateConnectionStatus(connected);
    if (sessionId) UIManager.updateSessionId(sessionId);
});

on('backendStatusChanged', healthy => {
    UIManager.updateBackendStatus(healthy);
});
// Export UIManager globally
window.UIManager = UIManager;