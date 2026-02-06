/**
 * AdImpact Chatbot - Secure Frontend Component
 * 
 * Features:
 * - Secure communication with FastAPI backend
 * - XSS protection and input validation
 * - Session management
 * - Error handling & user feedback
 * - Conversation history
 * - Rate limiting on client side
 */

class AdImpactChatbot {
    /**
     * Initialize the chatbot widget
     */
    constructor() {
        // Configuration
        this.sessionId = this.generateSecureSessionId();
        this.apiBaseUrl = this.getApiBaseUrl();
        this.maxMessageLength = 5000;
        this.requestTimeout = 30000; // 30 seconds
        
        // DOM Elements
        this.messagesContainer = document.getElementById('messagesContainer');
        this.userInput = document.getElementById('userInput');
        this.chatForm = document.getElementById('chatForm');
        this.sessionInfo = document.getElementById('sessionInfo');
        this.closeBtn = document.getElementById('closeChat');
        
        // State
        this.isLoading = false;
        this.messageCount = 0;
        this.lastMessageTime = 0;
        this.minMessageInterval = 1000; // Min 1 second between messages
        
        // Validate DOM elements
        if (!this.messagesContainer || !this.userInput || !this.chatForm) {
            console.error('❌ Required DOM elements not found');
            throw new Error('Chatbot initialization failed: missing DOM elements');
        }
        
        // Setup event listeners
        this.setupEventListeners();
        this.updateSessionInfo();
        
        console.log('✅ AdImpact Chatbot initialized');
    }

    /**
     * Generate a cryptographically secure session ID
     * @returns {string} Session ID
     */
    generateSecureSessionId() {
        const timestamp = Date.now();
        const random = Array.from(crypto.getRandomValues(new Uint8Array(16)))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
        return `session_${timestamp}_${random}`;
    }

    /**
     * Determine the API base URL dynamically
     * @returns {string} API base URL
     */
    getApiBaseUrl() {
        // Use current origin if available, fallback to localhost
        const protocol = window.location.protocol;
        const hostname = window.location.hostname;
        const port = window.location.port;
        
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            // Development environment
            return `${protocol}//${hostname}:8000/api/chat`;
        } else {
            // Production - use same origin
            return `${protocol}//${hostname}${port ? ':' + port : ''}/api/chat`;
        }
    }

    /**
     * Setup event listeners for form and buttons
     */
    setupEventListeners() {
        this.chatForm.addEventListener('submit', (e) => this.handleSendMessage(e));
        this.closeBtn?.addEventListener('click', () => this.closeChat());
        
        // Prevent XSS via keyboard
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    /**
     * Update session info display
     */
    updateSessionInfo() {
        if (this.sessionInfo) {
            const displayId = this.sessionId.substring(0, 16) + '...';
            this.sessionInfo.textContent = `Session: ${displayId}`;
            this.sessionInfo.setAttribute('title', this.sessionId);
        }
    }

    /**
     * Handle form submission - send message to chatbot
     * @param {Event} e Form submit event
     */
    async handleSendMessage(e) {
        e.preventDefault();
        
        const message = this.userInput.value.trim();
        
        // Validation
        if (!message) {
            this.showError('❌ Please enter a message');
            return;
        }
        
        if (message.length > this.maxMessageLength) {
            this.showError(`❌ Message exceeds ${this.maxMessageLength} characters`);
            return;
        }
        
        // Rate limiting check
        const now = Date.now();
        if (now - this.lastMessageTime < this.minMessageInterval) {
            this.showError('⏱️  Please wait before sending another message');
            return;
        }
        
        if (this.isLoading) {
            this.showError('⏳ Still processing previous message...');
            return;
        }
        
        // Add user message to UI
        this.addMessage(message, 'user');
        this.userInput.value = '';
        this.userInput.focus();
        this.lastMessageTime = now;
        this.messageCount++;
        
        // Show loading indicator
        this.showLoadingIndicator();
        
        // Send to API
        try {
            const response = await this.sendMessageToAPI(message);
            this.removeLoadingIndicator();
            this.addMessage(response.response, 'bot');
            
            console.log(`✅ Message received (Session: ${response.session_id.substring(0, 8)}...)`);
        } catch (error) {
            this.removeLoadingIndicator();
            this.showError(`❌ ${error.message}`);
            console.error('Chat error:', error);
        }
    }

    /**
     * Send message to API with proper error handling
     * @param {string} message User message
     * @returns {Promise<Object>} API response
     */
    async sendMessageToAPI(message) {
        try {
            console.log('📤 Sending message to API...');
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);
            
            const response = await fetch(`${this.apiBaseUrl}/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            // Handle response status
            if (!response.ok) {
                let errorMessage = `API error ${response.status}`;
                
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorMessage;
                    } else {
                        errorMessage = `${response.status} ${response.statusText}`;
                    }
                } catch (e) {
                    // Response is not JSON, use default message
                }
                
                throw new Error(errorMessage);
            }
            
            // Validate response content type
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Invalid response: expected JSON');
            }
            
            const data = await response.json();
            
            // Validate response structure
            if (!data.response || typeof data.response !== 'string') {
                throw new Error('Invalid response: missing message content');
            }
            
            console.log('📥 Response received successfully');
            return data;
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout - please try again');
            }
            throw error;
        }
    }

    /**
     * Add message to chat display with XSS protection
     * @param {string} content Message content
     * @param {string} sender 'user' or 'bot'
     * @param {boolean} isError Whether this is an error message
     */
    addMessage(content, sender, isError = false) {
        if (!content || typeof content !== 'string') {
            console.warn('⚠️  Invalid message content');
            return;
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message${isError ? ' error-message' : ''}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // XSS Protection: Use textContent instead of innerHTML
        // This automatically escapes any HTML content
        contentDiv.textContent = content;
        
        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        
        // Auto-scroll to bottom
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    /**
     * Show error message to user
     * @param {string} message Error message
     */
    showError(message) {
        this.addMessage(message, 'bot', true);
    }

    /**
     * Show loading indicator
     */
    showLoadingIndicator() {
        this.isLoading = true;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.id = 'loadingIndicator';
        messageDiv.setAttribute('aria-label', 'Loading response');
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading';
        
        // Create loading animation
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dot.setAttribute('aria-hidden', 'true');
            loadingDiv.appendChild(dot);
        }
        
        messageDiv.appendChild(loadingDiv);
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    /**
     * Remove loading indicator
     */
    removeLoadingIndicator() {
        this.isLoading = false;
        const loadingIndicator = document.getElementById('loadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }

    /**
     * Get conversation history
     * @returns {Promise<Object>} Conversation history
     */
    async getConversationHistory() {
        try {
            console.log('📋 Fetching conversation history...');
            
            const response = await fetch(`${this.apiBaseUrl}/history`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                let errorMessage = `API error ${response.status}`;
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorMessage;
                    }
                } catch (e) {
                    // Continue with default error message
                }
                throw new Error(errorMessage);
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Invalid response: expected JSON');
            }
            
            const data = await response.json();
            console.log(`✅ History retrieved: ${data.message_count || 0} messages`);
            return data;
        } catch (error) {
            console.error('❌ Error fetching history:', error);
            return null;
        }
    }

    /**
     * Clear current session
     * @returns {Promise<Object>} Clear result
     */
    async clearSession() {
        try {
            console.log('🗑️  Clearing session...');
            
            const response = await fetch(`${this.apiBaseUrl}/session/${this.sessionId}`, {
                method: 'DELETE',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                let errorMessage = `API error ${response.status}`;
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorMessage;
                    }
                } catch (e) {
                    // Continue with default error message
                }
                throw new Error(errorMessage);
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Invalid response: expected JSON');
            }
            
            const data = await response.json();
            console.log('✅ Session cleared');
            return data;
        } catch (error) {
            console.error('❌ Error clearing session:', error);
            return null;
        }
    }

    /**
     * Close the chatbot
     */
    closeChat() {
        console.log('👋 Closing chatbot...');
        // Option 1: Go back to previous page
        window.history.back();
        
        // Uncomment Option 2 to close window instead:
        // window.close();
    }
}

/**
 * Initialize chatbot when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    try {
        window.chatbot = new AdImpactChatbot();
        console.log('🚀 Chatbot ready for interaction');
    } catch (error) {
        console.error('❌ Failed to initialize chatbot:', error);
        const container = document.getElementById('messagesContainer');
        if (container) {
            container.innerHTML = '<div class="message bot-message error-message">' +
                '<div class="message-content">❌ Failed to initialize chatbot. Please refresh the page.</div>' +
                '</div>';
        }
    }
});

// Make chatbot available globally
window.AdImpactChatbot = AdImpactChatbot;
