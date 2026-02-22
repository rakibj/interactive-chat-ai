/**
 * state.js - Client-side state management
 * Single source of truth for UI state (mirrors server state)
 */

const appState = {
    // Phase information
    currentPhase: null,
    phaseProfile: null,
    phaseProgress: { completed: 0, total: 0 },
    phases: [],
    
    // Speaker status
    activeSpeaker: 'silence',  // 'human' | 'ai' | 'silence'
    isProcessing: false,
    
    // Conversation
    turns: [],
    currentTurnId: 0,
    
    // Connection
    wsConnected: false,
    backendHealthy: false,
    sessionId: null,
    lastEventTime: null,
    
    // Listeners for state changes
    listeners: {},
};

/**
 * Subscribe to state changes
 */
function on(eventName, callback) {
    if (!appState.listeners[eventName]) {
        appState.listeners[eventName] = [];
    }
    appState.listeners[eventName].push(callback);
}

/**
 * Emit state change events
 */
function emit(eventName, data) {
    if (appState.listeners[eventName]) {
        appState.listeners[eventName].forEach(callback => {
            try {
                callback(data);
            } catch (err) {
                console.error(`Error in ${eventName} listener:`, err);
            }
        });
    }
}

/**
 * Update speaker with change detection
 */
function updateSpeaker(newSpeaker) {
    if (appState.activeSpeaker !== newSpeaker) {
        appState.activeSpeaker = newSpeaker;
        appState.lastEventTime = new Date();
        emit('speakerChanged', newSpeaker);
    }
}

/**
 * Update processing status
 */
function setProcessing(isProcessing) {
    if (appState.isProcessing !== isProcessing) {
        appState.isProcessing = isProcessing;
        emit('processingChanged', isProcessing);
    }
}

/**
 * Add a turn to conversation
 */
function addTurn(turn) {
    appState.turns.push(turn);
    appState.currentTurnId = turn.turn_id;
    appState.lastEventTime = new Date();
    emit('turnAdded', turn);
}

/**
 * Update phase information
 */
function updatePhase(phaseData) {
    appState.currentPhase = phaseData.current_phase_id;
    appState.phaseProfile = phaseData.phase_profile;
    appState.phaseProgress = {
        completed: phaseData.phase_index || 0,
        total: phaseData.total_phases || 0,
    };
    appState.phases = phaseData.progress || [];
    appState.lastEventTime = new Date();
    emit('phaseChanged', phaseData);
}

/**
 * Update connection status
 */
function setWSConnected(connected, sessionId = null) {
    appState.wsConnected = connected;
    if (sessionId) appState.sessionId = sessionId;
    emit('connectionChanged', { connected, sessionId });
}

/**
 * Set backend health status
 */
function setBackendHealthy(healthy) {
    if (appState.backendHealthy !== healthy) {
        appState.backendHealthy = healthy;
        emit('backendStatusChanged', healthy);
    }
}

/**
 * Clear all state (for new session)
 */
function clearState() {
    appState.turns = [];
    appState.currentTurnId = 0;
    appState.activeSpeaker = 'silence';
    appState.isProcessing = false;
    appState.currentPhase = null;
    appState.phaseProgress = { completed: 0, total: 0 };
    appState.phases = [];
    emit('stateCleared', null);
}

/**
 * Get formatted speaker name
 */
function getSpeakerName(speaker) {
    const names = {
        'human': '👤 You',
        'ai': '🤖 AI',
        'silence': '⏸️',
    };
    return names[speaker] || speaker;
}

/**
 * Format timestamp as relative time
 */
function formatTime(timestamp) {
    if (!timestamp) return 'Never';
    const now = new Date();
    const time = new Date(timestamp * 1000 || timestamp);
    const diffSeconds = Math.floor((now - time) / 1000);
    
    if (diffSeconds < 60) return 'just now';
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
    return time.toLocaleDateString();
}

/**
 * Format latency metrics
 */
function formatLatency(metrics) {
    if (!metrics || !metrics.total_latency_ms) return null;
    return {
        transcription: Math.round(metrics.transcription_ms || 0),
        llm: Math.round(metrics.llm_generation_ms || 0),
        total: Math.round(metrics.total_latency_ms || 0),
    };
}
