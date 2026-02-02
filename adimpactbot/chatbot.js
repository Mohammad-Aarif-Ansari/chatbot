// app/static/chatbot.js

class AdImpactChatbot {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.apiBaseUrl = 'http://localhost:8000/api/chat';
        this.messagesContainer = document.getElementById('messagesContainer');
        this.userInput = document.getElementById('userInput');
        this.chatForm = document.getElementById('chatForm');
        this.sessionInfo = document.getElementById('sessionInfo');
        this.closeBtn = document.getElementById('closeChat');
        
        this.setupEventListeners();
        this.updateSessionInfo();
    }

    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    setupEventListeners() {
        this.chatForm.addEventListener('submit', (e) => this.handleSendMessage(e));
        this.closeBtn?.addEventListener('click', () => this.closeChat());
    }

    updateSessionInfo() {
        if (this.sessionInfo) {
            this.sessionInfo.textContent = `Session: ${this.sessionId.substr(0, 20)}...`;
        }
    }

    async handleSendMessage(e) {
        e.preventDefault();
        
        const message = this.userInput.value.trim();
        if (!message) return;

        // Add user message to UI
        this.addMessage(message, 'user');
        this.userInput.value = '';
        this.userInput.focus();

        // Show loading indicator
        this.showLoadingIndicator();

        try {
            const response = await this.sendMessageToAPI(message);
            this.removeLoadingIndicator();
            this.addMessage(response.response, 'bot');
        } catch (error) {
            this.removeLoadingIndicator();
            this.addMessage(`Error: ${error.message}`, 'bot', true);
            console.error('Chat error:', error);
        }
    }

    async sendMessageToAPI(message) {
        try {
            console.log('Sending message to API:', message);
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
                })
            });

            if (!response.ok) {
                let errorMessage = `API error: ${response.status}`;
                console.error('API Response Status:', response.status, 'URL:', response.url);
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorMessage;
                    } else {
                        errorMessage = `API error: ${response.status} - ${response.statusText}`;
                    }
                } catch (e) {
                    errorMessage = `API error: ${response.status} - ${response.statusText}`;
                }
                console.error('Final error message:', errorMessage);
                throw new Error(errorMessage);
            }

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Invalid response: expected JSON');
            }

            return await response.json();
        } catch (error) {
            throw error;
        }
    }

    addMessage(content, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message ${isError ? 'error-message' : ''}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;
        
        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        
        // Auto-scroll to bottom
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    showLoadingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.id = 'loadingIndicator';
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading';
        loadingDiv.innerHTML = '<span></span><span></span><span></span>';
        
        messageDiv.appendChild(loadingDiv);
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    removeLoadingIndicator() {
        const loadingIndicator = document.getElementById('loadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }

    async getConversationHistory() {
        try {
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
                let errorMessage = `API error: ${response.status}`;
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorMessage;
                    } else {
                        errorMessage = `API error: ${response.status} - ${response.statusText}`;
                    }
                } catch (e) {
                    // Response is not JSON
                    errorMessage = `API error: ${response.status} - ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Invalid response: expected JSON');
            }

            return await response.json();
        } catch (error) {
            console.error('Error fetching history:', error);
            return null;
        }
    }

    async clearSession() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/session/${this.sessionId}`, {
                method: 'DELETE',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                let errorMessage = `API error: ${response.status}`;
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorMessage;
                    } else {
                        errorMessage = `API error: ${response.status} - ${response.statusText}`;
                    }
                } catch (e) {
                    // Response is not JSON
                    errorMessage = `API error: ${response.status} - ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Invalid response: expected JSON');
            }

            return await response.json();
        } catch (error) {
            console.error('Error clearing session:', error);
            return null;
        }
    }

    closeChat() {
        // Option 1: Go back
        window.history.back();
        
        // Option 2: Or close the tab/window
        // window.close();
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new AdImpactChatbot();
});

// Make chatbot available globally
window.AdImpactChatbot = AdImpactChatbot;
