document.addEventListener('DOMContentLoaded', async function() {
    // Load configuration from backend
    let config;
    try {
        const response = await fetch('/api/config');
        config = await response.json();
    } catch (error) {
        console.error('Failed to load configuration:', error);
        return;
    }

    console.log('Loaded configuration:', config);

    // Build dynamic interface
    buildTabs(config.tabs);
    buildTabContents(config.tabs, config.models, config.suggestions);
    
    // Initialize tab functionality
    initializeTabs();
    
    // Initialize other functionality
    initializeControls();
});

function buildTabs(tabs) {
    const tabsContainer = document.getElementById('dynamicTabs');
    tabsContainer.innerHTML = '';
    
    tabs.forEach(tab => {
        const tabButton = document.createElement('button');
        tabButton.className = `tab-button ${tab.active ? 'active' : ''}`;
        tabButton.setAttribute('data-tab', tab.id);
        tabButton.innerHTML = `${tab.icon} ${tab.name}`;
        tabsContainer.appendChild(tabButton);
    });
}

function buildTabContents(tabs, models, suggestions) {
    const contentsContainer = document.getElementById('dynamicTabContents');
    contentsContainer.innerHTML = '';
    
    tabs.forEach(tab => {
        const tabContent = document.createElement('div');
        tabContent.className = `tab-content ${tab.active ? 'active' : ''}`;
        tabContent.id = `${tab.id}Tab`;
        
        // Create chat grid
        const chatGrid = document.createElement('div');
        chatGrid.className = 'chat-grid';
        
        // Create chat panels for each model
        models.forEach(model => {
            const chatPanel = document.createElement('div');
            chatPanel.className = 'chat-panel';
            
            chatPanel.innerHTML = `
                <div class="panel-header">
                    <div class="model-title">
                        <div class="model-avatar">${model.avatar}</div>
                        <h3>${model.display_name}</h3>
                    </div>
                    <div class="model-status" id="${tab.id}${model.key}Status">Ready</div>
                </div>
                <div class="chat-messages" id="${tab.id}${model.key}Messages"></div>
            `;
            
            chatGrid.appendChild(chatPanel);
        });
        
        tabContent.appendChild(chatGrid);
        
        // Create suggestions area
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'suggestions-container';
        
        const suggestionsTitle = document.createElement('h3');
        suggestionsTitle.className = 'suggestions-title';
        suggestionsTitle.textContent = tab.title;
        suggestionsContainer.appendChild(suggestionsTitle);
        
        const suggestionsGrid = document.createElement('div');
        suggestionsGrid.className = 'suggestions-grid';
        
        // Filter suggestions for this tab
        const tabSuggestions = suggestions.filter(s => s.category === tab.id);
        
        tabSuggestions.forEach(suggestion => {
            const button = document.createElement('button');
            button.className = 'suggestion-button';
            button.setAttribute('data-mode', tab.id);
            button.setAttribute('data-prompt', suggestion.key);
            button.textContent = suggestion.title;
            suggestionsGrid.appendChild(button);
        });
        
        suggestionsContainer.appendChild(suggestionsGrid);
        tabContent.appendChild(suggestionsContainer);
        contentsContainer.appendChild(tabContent);
    });
}

function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    let currentTab = 'general';

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // Update active tab
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            button.classList.add('active');
            const targetContent = document.getElementById(`${tabId}Tab`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
            
            currentTab = tabId;
        });
    });

    // Handle suggestion button clicks  
    document.addEventListener('click', async function(e) {
        if (e.target.classList.contains('suggestion-button')) {
            const prompt = e.target.getAttribute('data-prompt');
            const mode = e.target.getAttribute('data-mode');
            
            await handleSuggestionClick(prompt, mode);
        }
    });
}

async function handleSuggestionClick(prompt, mode) {
    // Get all model message containers for current tab
    const config = await getConfig();
    const models = config.models;
    
    const containers = models.map(model => ({
        key: model.key,
        container: document.getElementById(`${mode}${model.key}Messages`)
    })).filter(item => item.container);
    
    if (containers.length === 0) {
        console.error('No message containers found for mode:', mode);
        return;
    }

    // Clear existing chat history
    containers.forEach(item => clearChatHistory(item.container));

    // Get the display text for the user message
    const displayText = await getPromptDisplayText(prompt);
    
    // Add user message to all chat panels
    containers.forEach(item => addMessage(displayText, 'user', item.container));
    
    // Disable all suggestion buttons
    document.querySelectorAll('.suggestion-button').forEach(btn => {
        btn.disabled = true;
    });

    try {
        // Check if demo mode is enabled
        const demoMode = document.getElementById('demoModeToggle').checked;
        
        // Send streaming requests to each model
        const promises = containers.map(item => 
            fetchStreamingResponse(prompt, mode, item.key, item.container, demoMode)
        );
        
        // Wait for all streams to complete before re-enabling buttons
        await Promise.allSettled(promises);
        
    } catch (error) {
        console.error('Error:', error);
        containers.forEach(item => 
            addMessage('Sorry, I encountered an error. Please try again.', 'assistant', item.container)
        );
    } finally {
        // Re-enable suggestion buttons
        document.querySelectorAll('.suggestion-button').forEach(btn => {
            btn.disabled = false;
        });
    }
}

async function getConfig() {
    const response = await fetch('/api/config');
    return await response.json();
}

async function getPromptDisplayText(suggestionKey) {
    const config = await getConfig();
    const suggestion = config.suggestions.find(s => s.key === suggestionKey);
    return suggestion ? suggestion.prompt : suggestionKey;
}

// Fetch streaming response from individual model
async function fetchStreamingResponse(prompt, mode, modelKey, container, demoMode = false) {
    try {
        const url = `/chat_stream?message=${encodeURIComponent(prompt)}&mode=${encodeURIComponent(mode)}&model=${encodeURIComponent(modelKey)}&demo=${demoMode}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullText = '';
        let demoFullText = ''; // For demo mode to track complete response
        
        // Create the message container for streaming
        const messageId = addStreamingMessage(container);
        const messageElement = document.getElementById(messageId);
        const textElement = messageElement.querySelector('.message-text');
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.error) {
                            textElement.textContent = `Error: ${data.error}`;
                            return { success: false, error: data.error };
                        }
                        
                        if (data.done) {
                            // Convert final text to markdown
                            const finalText = demoMode ? demoFullText : fullText;
                            
                            // Remove shuffled styling for final display to match regular formatting
                            textElement.classList.remove('shuffled-text');
                            
                            const htmlContent = typeof marked !== 'undefined' ? 
                                marked.parse(finalText) : 
                                finalText;
                            textElement.innerHTML = htmlContent;
                            return { success: true, data: { html: htmlContent, text: finalText } };
                        }
                        
                        if (data.token) {
                            // Check if this is a shuffled update
                            if (data.token.startsWith('__SHUFFLED_UPDATE__')) {
                                // Extract the complete response text
                                const shuffledText = data.token.substring('__SHUFFLED_UPDATE__'.length);
                                
                                // Apply special styling for shuffled text
                                textElement.classList.add('shuffled-text');
                                
                                // Use the text as-is (with blank spaces for unfilled positions)
                                textElement.textContent = shuffledText;
                                
                                demoFullText = shuffledText; // Update demo full text
                                fullText = shuffledText; // Update full text
                            } else {
                                // Normal token streaming
                                textElement.classList.remove('shuffled-text'); // Remove shuffled styling for normal text
                                
                                if (demoMode) {
                                    demoFullText += data.token;
                                    textElement.textContent = demoFullText;
                                } else {
                                    fullText += data.token;
                                    textElement.textContent = fullText;
                                }
                            }
                            container.scrollTop = container.scrollHeight;
                        }
                    } catch (e) {
                        console.error('Error parsing JSON:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error(`Error fetching ${modelKey} streaming response:`, error);
        return { success: false, error: error.message };
    }
}

// Add loading message and return its ID for removal
function addLoadingMessage(container) {
    const loadingId = 'loading-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message loading-message';
    messageDiv.id = loadingId;
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-text">
                <div class="loading-indicator">
                    <div class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <span class="loading-text">Generating...</span>
                </div>
            </div>
        </div>
    `;
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    return loadingId;
}

// Add streaming message and return its ID
function addStreamingMessage(container) {
    const messageId = 'message-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    messageDiv.id = messageId;
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-text"></div>
            <div class="message-time">Just now</div>
        </div>
    `;
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    return messageId;
}

// Add message to chat
function addMessage(text, sender, container) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const avatar = sender === 'user' ? '👤' : '🤖';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-text">${text}</div>
            <div class="message-time">Just now</div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

// Clear chat history completely
function clearChatHistory(container) {
    const messages = container.querySelectorAll('.message');
    messages.forEach((message) => {
        message.remove();
    });
}

function initializeControls() {
    // Demo mode toggle
    const demoModeToggle = document.getElementById('demoModeToggle');
    if (demoModeToggle) {
        demoModeToggle.addEventListener('change', function() {
            console.log('Demo mode:', this.checked ? 'enabled' : 'disabled');
        });
    }

    // Refresh button functionality
    const refreshButton = document.getElementById('refreshButton');
    if (refreshButton) {
        refreshButton.addEventListener('click', async function() {
            const config = await getConfig();
            
            // Clear all chat messages from all tabs
            config.tabs.forEach(tab => {
                config.models.forEach(model => {
                    const messageContainer = document.getElementById(`${tab.id}${model.key}Messages`);
                    if (messageContainer) {
                        clearChatHistory(messageContainer);
                    }
                });
            });
            
            // Add a subtle animation to the refresh icon
            const refreshIcon = refreshButton.querySelector('.refresh-icon');
            refreshIcon.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                refreshIcon.style.transform = 'rotate(0deg)';
            }, 300);
            
            console.log('All chat history cleared');
        });
    }
}
