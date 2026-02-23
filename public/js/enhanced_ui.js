/**
 * enhanced_ui.js - Blueprint 1 & 2 Implementation
 * Enhanced phase visuals, turn summary with details, and interactive features
 */

/**
 * BLUEPRINT 1: Enhanced Phase Visuals Manager
 */
class PhaseVisualsManager {
    /**
     * Update phase progress with duration tracking
     */
    static updatePhaseWithDurations(state) {
        if (!state.phase?.progress) return;

        const phaseContainer = document.getElementById('phase-tracker');
        if (!phaseContainer) return;

        phaseContainer.innerHTML = '';

        state.phase.progress.forEach((phase, index) => {
            const phaseEl = document.createElement('div');
            phaseEl.className = `phase-item ${phase.status}`;
            
            // Status badge
            const statusBadge = {
                'completed': '✅',
                'active': '🔵',
                'upcoming': '⭕'
            }[phase.status] || '❓';

            // Duration display
            const durationText = phase.duration_sec 
                ? `<span class="phase-duration">(${phase.duration_sec.toFixed(1)}s)</span>` 
                : '';

            // Phase info
            const phaseName = phase.name || phase.id || 'Unknown';
            const phaseIndex = `<span class="phase-index">${index + 1}/${state.phase.total_phases}</span>`;

            phaseEl.innerHTML = `
                <span class="phase-status">${statusBadge}</span>
                <span class="phase-name">${escapeHtml(phaseName)}</span>
                ${durationText}
                ${phaseIndex}
            `;

            phaseEl.addEventListener('click', () => {
                this.showPhaseDetails(phase);
            });

            phaseContainer.appendChild(phaseEl);
        });
    }

    /**
     * Show detailed phase information
     */
    static showPhaseDetails(phase) {
        const modal = document.createElement('div');
        modal.className = 'phase-details-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${escapeHtml(phase.name || phase.id || 'Unknown')}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="detail-row">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value">${phase.status}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Duration:</span>
                        <span class="detail-value">${phase.duration_sec?.toFixed(2) || 'N/A'}s</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Phase ID:</span>
                        <span class="detail-value">${phase.id}</span>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.querySelector('.modal-close').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
    }

    /**
     * Draw phase timeline (visual progress bar)
     */
    static drawPhaseTimeline(state) {
        let timelineContainer = document.getElementById('phase-timeline');
        
        if (!timelineContainer) {
            // Create timeline container if it doesn't exist
            const phaseSection = document.querySelector('.phase-section');
            if (phaseSection) {
                timelineContainer = document.createElement('div');
                timelineContainer.id = 'phase-timeline';
                timelineContainer.className = 'phase-timeline';
                phaseSection.appendChild(timelineContainer);
            }
        }
        
        if (!timelineContainer || !state.phase?.progress) return;

        const phases = state.phase.progress;
        const progressPercent = state.phase.phase_index ? 
            (state.phase.phase_index / Math.max(state.phase.total_phases, 1)) * 100 : 0;

        timelineContainer.innerHTML = `
            <div class="timeline-track">
                <div class="timeline-progress" style="width: ${progressPercent}%"></div>
                <div class="timeline-markers">
                    ${phases.map((p, i) => `
                        <div class="timeline-marker ${p.status}" 
                             title="${escapeHtml(p.name || p.id)}"
                             style="left: ${(i / Math.max(phases.length - 1, 1)) * 100}%">
                            <span class="marker-number">${i + 1}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
}

/**
 * BLUEPRINT 2: Enhanced Turn Summary Manager
 */
class TurnSummaryManager {
    /**
     * Update turn summary with all available metrics
     */
    static updateTurnSummaryFull(state) {
        if (!state.history || state.history.length === 0) {
            this.renderEmptyState();
            return;
        }

        const lastTurn = state.history[state.history.length - 1];
        const turnIndex = state.history.length;

        const summaryEl = document.getElementById('turn-summary');
        if (!summaryEl) return;

        const speakerIcon = {
            'human': '🎤',
            'ai': '🤖',
            'silence': '⏸️'
        }[lastTurn.speaker] || '❓';

        const endReasonLabel = {
            'silence': 'Natural pause',
            'safety_timeout': 'Safety timeout',
            'limit_exceeded': 'Speaking limit',
            'user_interrupt': 'User interrupt'
        }[lastTurn.end_reason] || (lastTurn.end_reason || 'Unknown');

        summaryEl.innerHTML = `
            <div class="turn-summary-header">
                <span class="turn-counter">Turn #${turnIndex}</span>
                <span class="turn-timestamp">
                    ${this.formatTime(lastTurn.timestamp)}
                </span>
            </div>
            
            <div class="turn-summary-speaker">
                <span class="speaker-icon">${speakerIcon}</span>
                <span class="speaker-name">${lastTurn.speaker}</span>
            </div>

            <div class="turn-metrics">
                <div class="metric">
                    <span class="metric-label">⏱️ Latency:</span>
                    <span class="metric-value">${lastTurn.latency_ms?.toFixed(1) || 'N/A'}ms</span>
                </div>
                ${lastTurn.end_reason ? `
                    <div class="metric">
                        <span class="metric-label">🔚 Ended by:</span>
                        <span class="metric-value">${endReasonLabel}</span>
                    </div>
                ` : ''}
                ${lastTurn.phase_id ? `
                    <div class="metric">
                        <span class="metric-label">📍 Phase:</span>
                        <span class="metric-value">${lastTurn.phase_id}</span>
                    </div>
                ` : ''}
            </div>

            <div class="turn-transcript">
                <div class="transcript-label">💬 Message:</div>
                <div class="transcript-text">${escapeHtml(lastTurn.transcript)}</div>
            </div>

            <div class="turn-actions">
                <button class="btn-detail" onclick="window.TurnSummaryManager.showTurnDetails(${turnIndex - 1})">
                    View Details
                </button>
            </div>
        `;

        // Attach click listener for collapsible metrics
        this.attachMetricsToggle(summaryEl);
    }

    /**
     * Show full turn details in modal
     */
    static showTurnDetails(turnIndex) {
        // Get turn from global window state or from last rendered state
        const app = window.liveApp;
        if (!app || !app.lastState || !app.lastState.history) return;
        
        const turn = app.lastState.history[turnIndex];
        if (!turn) {
            console.warn('Turn not found at index:', turnIndex);
            return;
        }

        const modal = document.createElement('div');
        modal.className = 'turn-details-modal';
        
        const metricsHtml = this.renderDetailedMetrics(turn);

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Turn #${turnIndex + 1} Details</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    ${metricsHtml}
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.querySelector('.modal-close').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
    }

    /**
     * Render detailed metrics for a turn
     */
    static renderDetailedMetrics(turn) {
        return `
            <div class="details-grid">
                <div class="detail-group">
                    <h4>📊 Timing</h4>
                    <div class="detail-item">
                        <span class="detail-label">Total Latency:</span>
                        <span class="detail-value">${turn.latency_ms?.toFixed(2) || 'N/A'}ms</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Duration:</span>
                        <span class="detail-value">${turn.duration_sec?.toFixed(2) || 'N/A'}s</span>
                    </div>
                </div>

                <div class="detail-group">
                    <h4>📢 Content</h4>
                    <div class="detail-item">
                        <span class="detail-label">Speaker:</span>
                        <span class="detail-value">${turn.speaker}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Text Length:</span>
                        <span class="detail-value">${turn.transcript?.length || 0} chars</span>
                    </div>
                </div>

                <div class="detail-group">
                    <h4>🎯 Turn Info</h4>
                    <div class="detail-item">
                        <span class="detail-label">Turn ID:</span>
                        <span class="detail-value">${turn.turn_id}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Timestamp:</span>
                        <span class="detail-value">${this.formatTime(turn.timestamp)}</span>
                    </div>
                    ${turn.phase_id ? `
                        <div class="detail-item">
                            <span class="detail-label">Phase:</span>
                            <span class="detail-value">${turn.phase_id}</span>
                        </div>
                    ` : ''}
                </div>

                <div class="detail-group full-width">
                    <h4>💬 Full Transcript</h4>
                    <div class="transcript-box">
                        ${escapeHtml(turn.transcript)}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Format timestamp to readable format
     */
    static formatTime(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp * 1000);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
    }

    /**
     * Render empty state
     */
    static renderEmptyState() {
        const summaryEl = document.getElementById('turn-summary');
        if (!summaryEl) return;
        
        summaryEl.innerHTML = `
            <div class="turn-summary-empty">
                <div class="empty-icon">⏳</div>
                <div class="empty-text">No turns yet</div>
                <div class="empty-subtext">Start a conversation to see turn details</div>
            </div>
        `;
    }

    /**
     * Toggle metrics visibility
     */
    static attachMetricsToggle(container) {
        const header = container.querySelector('.turn-summary-header');
        if (!header) return;

        header.style.cursor = 'pointer';
        header.onclick = () => {
            const metrics = container.querySelector('.turn-metrics');
            if (metrics) {
                metrics.style.display = 
                    metrics.style.display === 'none' ? 'block' : 'none';
            }
        };
    }
}

/**
 * HTML escape utility
 */
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Export globally
window.PhaseVisualsManager = PhaseVisualsManager;
window.TurnSummaryManager = TurnSummaryManager;
