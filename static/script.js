document.addEventListener('DOMContentLoaded', function() {
    
    // Tab management
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    let currentTab = 'general';
    
    // Initialize tabs
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tab = button.dataset.tab;
            switchTab(tab);
        });
    });
    
    function switchTab(tab) {
        // Update active tab button
        tabButtons.forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
        
        // Update active tab content
        tabContents.forEach(content => content.classList.remove('active'));
        document.getElementById(`${tab}Tab`).classList.add('active');
        
        currentTab = tab;
        
        // Tab switched successfully
    }
    
    // Handle suggestion button clicks
    document.querySelectorAll('.suggestion-button').forEach(button => {
        button.addEventListener('click', async function() {
            const mode = this.dataset.mode;
            const prompt = this.dataset.prompt;
            
            if (!prompt) return;

            // Get current tab's message containers
            const smollm2Messages = document.getElementById(`${mode}Smollm2Messages`);
            const smollmMessages = document.getElementById(`${mode}SmollmMessages`);

            // Debug logging
            console.log(`Mode: ${mode}`);
            console.log(`SmolLM2 container:`, smollm2Messages);
            console.log(`SmolLM container:`, smollmMessages);

            // Clear existing chat history
            clearChatHistory(smollm2Messages);
            clearChatHistory(smollmMessages);

            // Add user message to both chat panels
            addMessage(prompt, 'user', smollm2Messages);
            addMessage(prompt, 'user', smollmMessages);
            
            // Disable all suggestion buttons
            document.querySelectorAll('.suggestion-button').forEach(btn => {
                btn.disabled = true;
            });

            // Show loading indicators in chat panels

            try {
                // Add loading indicators to both panels
                const smollm2LoadingId = addLoadingMessage(smollm2Messages);
                const smollmLoadingId = addLoadingMessage(smollmMessages);
                
                // Send individual requests to each model
                const smollm2Promise = fetchModelResponse(prompt, mode, 'smollm2');
                const smollmPromise = fetchModelResponse(prompt, mode, 'smollm');
                
                // Handle SmolLM2 response when ready
                smollm2Promise.then(response => {
                    removeLoadingMessage(smollm2Messages, smollm2LoadingId);
                    if (response.success) {
                        addMessage(response.data.html, 'assistant', smollm2Messages, true);
                    } else {
                        addMessage('Sorry, SmolLM2 encountered an error. Please try again.', 'assistant', smollm2Messages);
                    }
                }).catch(error => {
                    console.error('SmolLM2 Error:', error);
                    removeLoadingMessage(smollm2Messages, smollm2LoadingId);
                    addMessage('Sorry, SmolLM2 encountered an error. Please try again.', 'assistant', smollm2Messages);
                });
                
                // Handle SmolLM response when ready
                smollmPromise.then(response => {
                    removeLoadingMessage(smollmMessages, smollmLoadingId);
                    if (response.success) {
                        addMessage(response.data.html, 'assistant', smollmMessages, true);
                    } else {
                        addMessage('Sorry, SmolLM encountered an error. Please try again.', 'assistant', smollmMessages);
                    }
                }).catch(error => {
                    console.error('SmolLM Error:', error);
                    removeLoadingMessage(smollmMessages, smollmLoadingId);
                    addMessage('Sorry, SmolLM encountered an error. Please try again.', 'assistant', smollmMessages);
                });
                
                // Wait for both to complete before re-enabling buttons
                Promise.allSettled([smollm2Promise, smollmPromise]).then(() => {
                    document.querySelectorAll('.suggestion-button').forEach(btn => {
                        btn.disabled = false;
                    });
                });
                
            } catch (error) {
                console.error('Error:', error);
                addMessage('Sorry, I encountered an error. Please try again.', 'assistant', smollm2Messages);
                addMessage('Sorry, I encountered an error. Please try again.', 'assistant', smollmMessages);
                document.querySelectorAll('.suggestion-button').forEach(btn => {
                    btn.disabled = false;
                });
            }
        });
    });



    // Clear chat history completely
    function clearChatHistory(container) {
        const messages = container.querySelectorAll('.message');
        messages.forEach((message) => {
            message.remove();
        });
    }

    // Fetch response from individual model
    async function fetchModelResponse(prompt, mode, modelKey) {
        try {
            const response = await fetch('/chat_single', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `message=${encodeURIComponent(prompt)}&mode=${encodeURIComponent(mode)}&model=${encodeURIComponent(modelKey)}`
            });

            const data = await response.json();
            return { success: data.status === 'success', data: data.response };
        } catch (error) {
            console.error(`Error fetching ${modelKey} response:`, error);
            return { success: false, error: error.message };
        }
    }

    // Add loading message and return its ID for removal
    function addLoadingMessage(container) {
        const loadingId = 'loading-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        messageDiv.id = loadingId;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const messageText = document.createElement('div');
        messageText.className = 'message-text loading-message';
        messageText.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>Generating...';
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = new Date().toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        content.appendChild(messageText);
        content.appendChild(messageTime);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;
        
        return loadingId;
    }

    // Remove loading message by ID
    function removeLoadingMessage(container, loadingId) {
        const loadingMessage = document.getElementById(loadingId);
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    // Add message to specified chat container
    function addMessage(text, sender, container, isHTML = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? '👤' : '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        
        if (isHTML) {
            // Render HTML content (from markdown)
            messageText.innerHTML = text;
        } else {
            // Plain text content
            messageText.textContent = text;
        }
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = new Date().toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        content.appendChild(messageText);
        content.appendChild(messageTime);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        container.appendChild(messageDiv);
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    // Check model status on load
    async function checkModelStatus() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            // Update status for all tabs
            ['general', 'correction', 'extraction'].forEach(mode => {
                const smollm2Status = document.getElementById(`${mode}Smollm2Status`);
                const smollmStatus = document.getElementById(`${mode}SmollmStatus`);
                
                if (smollm2Status) {
                    if (data.models.smollm2.loaded) {
                        smollm2Status.textContent = 'Ready';
                        smollm2Status.className = 'model-status ready';
                    } else {
                        smollm2Status.textContent = 'Loading...';
                        smollm2Status.className = 'model-status loading';
                    }
                }
                
                if (smollmStatus) {
                    if (data.models.smollm.loaded) {
                        smollmStatus.textContent = 'Ready';
                        smollmStatus.className = 'model-status ready';
                    } else {
                        smollmStatus.textContent = 'Loading...';
                        smollmStatus.className = 'model-status loading';
                    }
                }
            });
        } catch (error) {
            ['general', 'correction', 'extraction'].forEach(mode => {
                const smollm2Status = document.getElementById(`${mode}Smollm2Status`);
                const smollmStatus = document.getElementById(`${mode}SmollmStatus`);
                
                if (smollm2Status) {
                    smollm2Status.textContent = 'Error';
                    smollm2Status.className = 'model-status error';
                }
                if (smollmStatus) {
                    smollmStatus.textContent = 'Error';
                    smollmStatus.className = 'model-status error';
                }
            });
        }
    }

    // Check status every 5 seconds
    checkModelStatus();
    setInterval(checkModelStatus, 5000);

    // Initialize the interface - no input to focus anymore
});
