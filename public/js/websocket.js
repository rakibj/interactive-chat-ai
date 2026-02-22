/**
 * websocket.js - Real-time WebSocket event streaming
 * Handles connection, reconnection, and signal dispatch
 */

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.messageQueue = [];
        this.lastMessageId = null;
    }
    
    /**
     * Connect to WebSocket server
     */
    connect() {
        try {
            const wsUrl = `ws://${window.location.hostname}:8000/ws`;
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => this.onOpen();
            this.ws.onmessage = (event) => this.onMessage(event);
            this.ws.onerror = (err) => this.onError(err);
            this.ws.onclose = () => this.onClose();
        } catch (err) {
            console.error('WebSocket connection error:', err);
            this.scheduleReconnect();
        }
    }
    
    /**
     * Handle WebSocket open
     */
    onOpen() {
        console.log('✅ WebSocket connected');
        this.reconnectAttempts = 0;
        setWSConnected(true);
        
        // Send connection request
        const request = {
            phase_profile: 'default',
            user_agent: navigator.userAgent,
        };
        
        try {
            this.ws.send(JSON.stringify(request));
        } catch (err) {
            console.error('Error sending connection request:', err);
        }
    }
    
    /**
     * Handle incoming WebSocket message
     */
    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            const { message_id, event_type, timestamp, payload, phase_id, turn_id } = message;
            
            // Deduplication
            if (message_id === this.lastMessageId) {
                console.log('⚠️ Duplicate message, skipping');
                return;
            }
            this.lastMessageId = message_id;
            
            console.log(`📨 [${event_type}]`, payload);
            
            // Dispatch signal to handlers
            this.handleSignal(event_type, payload, { timestamp, phase_id, turn_id });
            
        } catch (err) {
            console.error('Error processing WebSocket message:', err);
        }
    }
    
    /**
     * Handle WebSocket errors
     */
    onError(err) {
        console.error('❌ WebSocket error:', err);
        UIManager.showError('Lost connection to server');
    }
    
    /**
     * Handle WebSocket close
     */
    onClose() {
        console.log('⚠️ WebSocket disconnected');
        setWSConnected(false);
        this.scheduleReconnect();
    }
    
    /**
     * Reconnect to WebSocket with exponential backoff
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            UIManager.showError('Lost connection to server (max retries reached)');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
        
        console.log(`🔄 Reconnecting in ${Math.round(delay / 1000)}s (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => this.connect(), delay);
    }
    
    /**
     * Dispatch signal handlers based on event type
     */
    handleSignal(eventType, payload, meta) {
        switch (eventType) {
            // Session management
            case 'session_created':
                setWSConnected(true, payload.session_id);
                console.log('📋 Session created:', payload.session_id);
                break;
            
            // Speaker status signals
            case 'VAD_SPEECH_STARTED':
                updateSpeaker('human');
                break;
            
            case 'VAD_SPEECH_ENDED':
                updateSpeaker('silence');
                break;
            
            case 'TTS_SPEAKING_STARTED':
                updateSpeaker('ai');
                if (payload.text_preview) {
                    UIManager.streamAIResponse(payload.text_preview);
                }
                break;
            
            case 'TTS_SPEAKING_ENDED':
                updateSpeaker('silence');
                break;
            
            // Turn processing
            case 'TURN_STARTED':
                setProcessing(true);
                break;
            
            case 'TURN_COMPLETED':
                setProcessing(false);
                if (payload) {
                    UIManager.displayTurnMetrics(payload);
                    const turn = {
                        turn_id: meta.turn_id || appState.currentTurnId,
                        speaker: payload.speaker || 'ai',
                        transcript: payload.ai_transcript || payload.transcript || '',
                        timestamp: meta.timestamp || Date.now() / 1000,
                        phase_id: meta.phase_id,
                        latency_ms: payload.total_latency_ms,
                    };
                    addTurn(turn);
                    UIManager.addAIMessage(turn.transcript, { latency_ms: turn.latency_ms });
                }
                break;
            
            // Phase transitions
            case 'PHASE_TRANSITION_TRIGGERED':
                console.log('🔄 Phase transition triggered:', payload);
                break;
            
            case 'PHASE_TRANSITION_COMPLETE':
                if (payload && payload.phase_id) {
                    updatePhase({
                        current_phase_id: payload.phase_id,
                        phase_index: payload.phase_index || 0,
                        total_phases: payload.total_phases || 1,
                        progress: payload.progress || [],
                    });
                    console.log('✅ Phase transition complete:', payload.phase_id);
                }
                break;
            
            case 'PHASE_PROGRESS_UPDATED':
                if (payload) {
                    updatePhase({
                        current_phase_id: payload.phase_id,
                        phase_index: payload.phases_completed || 0,
                        total_phases: payload.total_phases || 1,
                        progress: payload.progress || [],
                    });
                }
                break;
            
            // Interruptions
            case 'CONVERSATION_INTERRUPTED':
                console.log('🛑 Conversation interrupted');
                updateSpeaker('silence');
                break;
            
            case 'CONVERSATION_SPEAKING_LIMIT_EXCEEDED':
                console.log('⏱️ Speaking limit exceeded');
                UIManager.showError('Speaking time limit exceeded');
                break;
            
            case 'SPEAKER_CHANGED':
                if (payload && payload.to_speaker) {
                    updateSpeaker(payload.to_speaker);
                }
                break;
            
            // Analytics
            case 'ANALYTICS_TURN_METRICS':
                if (payload) {
                    UIManager.displayTurnMetrics(payload);
                }
                break;
            
            case 'ANALYTICS_SESSION_SUMMARY':
                console.log('📊 Session summary:', payload);
                break;
            
            // Error handling
            case 'error':
                console.error('❌ Server error:', payload);
                UIManager.showError(payload.message || 'Server error occurred');
                break;
            
            default:
                console.log(`📌 Unhandled signal: ${eventType}`, payload);
        }
    }
}

// Create global WebSocket manager instance
const wsManager = new WebSocketManager();
