document.addEventListener('DOMContentLoaded', function() {
    // Map internal keys to actual prompt text that users should see
    const promptDisplayMap = {
        // General Chat
        'general_suggestion1': 'Explain quantum computing in simple terms',
        'general_suggestion2': 'Write a Python function to calculate fibonacci numbers',
        'general_suggestion3': 'What are the benefits of renewable energy?',
        'general_suggestion4': 'How do I start learning machine learning?',
        
        // Correction
        'correction_suggestion1': 'I cant beleive its already december and i havent finished my homwork yet.',
        'correction_suggestion2': 'Their going to there house to get they\'re things.',
        'correction_suggestion3': 'The meeting will be held on Monday, Wenesday, and friday at 3pm.',
        'correction_suggestion4': 'Please find attached the documents you requested. I hope this helps with you\'re project.',
        
        // Extraction
        'extraction_suggestion1': 'John Doe, 123 Main Street, New York, NY 10001, Phone: (555) 123-4567, Email: john.doe@email.com, DOB: 01/15/1985',
        'extraction_suggestion2': 'Invoice #INV-2024-001, Date: March 15, 2024, Total: $1,234.56, Customer: ABC Corp, Items: 5x Laptops ($200 each), 3x Monitors ($150 each)',
        'extraction_suggestion3': 'Meeting scheduled for January 20, 2024 at 2:30 PM EST. Attendees: Sarah Johnson (Manager), Mike Chen (Developer), Lisa Park (Designer). Location: Conference Room B, Duration: 90 minutes',
        'extraction_suggestion4': 'Company: TechStart LLC, Founded: 2020, CEO: David Wilson, Revenue: $2.5M, Employees: 45, Address: 456 Tech Plaza, San Francisco, CA 94105'
    };
    
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

            // Get the display text for the user message (or use prompt if no mapping)
            const displayText = promptDisplayMap[prompt] || prompt;
            
            // Add user message to both chat panels with display text
            addMessage(displayText, 'user', smollm2Messages);
            addMessage(displayText, 'user', smollmMessages);
            
            // Disable all suggestion buttons
            document.querySelectorAll('.suggestion-button').forEach(btn => {
                btn.disabled = true;
            });

            // Show loading indicators in chat panels

            try {
                // Add loading indicators to both panels
                const smollm2LoadingId = addLoadingMessage(smollm2Messages);
                const smollmLoadingId = addLoadingMessage(smollmMessages);
                
                // Check if demo mode is enabled
                const demoMode = document.getElementById('demoModeToggle').checked;
                
                // Send streaming requests to each model
                const smollm2Promise = fetchStreamingResponse(prompt, mode, 'smollm2', smollm2Messages, demoMode);
                const smollmPromise = fetchStreamingResponse(prompt, mode, 'smollm', smollmMessages, demoMode);
                
                // Remove loading messages since streaming will handle display
                removeLoadingMessage(smollm2Messages, smollm2LoadingId);
                removeLoadingMessage(smollmMessages, smollmLoadingId);
                
                // Wait for both streams to complete before re-enabling buttons
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
                buffer = lines.pop(); // Keep incomplete line in buffer
                
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
                                        // For demo mode, accumulate the full response and display it
                                        demoFullText += data.token;
                                        textElement.textContent = demoFullText;
                                    } else {
                                        // For live mode, accumulate tokens
                                        fullText += data.token;
                                        textElement.textContent = fullText;
                                    }
                                }
                                // Auto-scroll to bottom
                                container.scrollTop = container.scrollHeight;
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e);
                        }
                    }
                }
            }
            
            const finalText = demoMode ? demoFullText : fullText;
            return { success: true, data: { html: finalText, text: finalText } };
            
        } catch (error) {
            console.error(`Error fetching ${modelKey} streaming response:`, error);
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

    // Add streaming message container and return its ID
    function addStreamingMessage(container) {
        const messageId = 'streaming-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        messageDiv.id = messageId;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        messageText.textContent = '';
        
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
        
        return messageId;
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

    // Refresh button functionality
    const refreshButton = document.getElementById('refreshButton');
    refreshButton.addEventListener('click', function() {
        // Clear all chat messages from all tabs
        ['general', 'correction', 'extraction'].forEach(mode => {
            const smollm2Messages = document.getElementById(`${mode}Smollm2Messages`);
            const smollmMessages = document.getElementById(`${mode}SmollmMessages`);
            
            if (smollm2Messages) clearChatHistory(smollm2Messages);
            if (smollmMessages) clearChatHistory(smollmMessages);
        });
        
        // Add a subtle animation to the refresh icon
        const refreshIcon = refreshButton.querySelector('.refresh-icon');
        refreshIcon.style.transform = 'rotate(360deg)';
        setTimeout(() => {
            refreshIcon.style.transform = 'rotate(0deg)';
        }, 300);
        
        console.log('All chat history cleared');
    });

    // Remask button functionality
    console.log('Looking for remask button...');
    const remaskButton = document.getElementById('remaskButton');
    console.log('Remask button found:', remaskButton);
    if (remaskButton) {
        remaskButton.addEventListener('click', async function() {
            console.log('Remask button clicked!');
            // Only work when correction tab is active
            if (currentTab !== 'correction') {
                console.log('Remask button only works in correction tab. Current tab:', currentTab);
                return;
            }

            // Get the correction tab's message containers
            const smollm2Messages = document.getElementById('correctionSmollm2Messages');
            const smollmMessages = document.getElementById('correctionSmollmMessages');

            console.log('Message containers found:', { smollm2Messages, smollmMessages });

            if (!smollm2Messages || !smollmMessages) {
                console.error('Message containers not found');
                return;
            }

            // Check if there's a previous assistant message to repeat
            const lastAssistantMessageSmollm2 = smollm2Messages.querySelector('.message.assistant:last-child .message-text');
            const lastAssistantMessageSmollm = smollmMessages.querySelector('.message.assistant:last-child .message-text');
            
            console.log('Previous assistant messages found:', { lastAssistantMessageSmollm2, lastAssistantMessageSmollm });
            
            // Debug: Let's see what's actually in the containers
            console.log('All messages in SmolLM2 container:', smollm2Messages.innerHTML);
            console.log('All messages in SmolLM container:', smollmMessages.innerHTML);
            
            // Try a different selector approach
            const allAssistantMessagesSmollm2 = smollm2Messages.querySelectorAll('.assistant-message');
            const allAssistantMessagesSmollm = smollmMessages.querySelectorAll('.assistant-message');
            
            console.log('All assistant messages found:', { 
                smollm2: allAssistantMessagesSmollm2.length, 
                smollm: allAssistantMessagesSmollm.length 
            });
            
            // Get the previous assistant responses (or use default if none exist)
            let previousResponseSmollm2, previousResponseSmollm;
            
            if (allAssistantMessagesSmollm2.length > 0) {
                const lastAssistantDiv = allAssistantMessagesSmollm2[allAssistantMessagesSmollm2.length - 1];
                const messageText = lastAssistantDiv.querySelector('.message-text');
                previousResponseSmollm2 = messageText ? (messageText.textContent || messageText.innerText) : 
                    "I don't see any previous response to correct. Please try one of the example corrections first.";
            } else {
                previousResponseSmollm2 = "I don't see any previous response to correct. Please try one of the example corrections first.";
            }
            
            if (allAssistantMessagesSmollm.length > 0) {
                const lastAssistantDiv = allAssistantMessagesSmollm[allAssistantMessagesSmollm.length - 1];
                const messageText = lastAssistantDiv.querySelector('.message-text');
                previousResponseSmollm = messageText ? (messageText.textContent || messageText.innerText) : 
                    "I don't see any previous response to correct. Please try one of the example corrections first.";
            } else {
                previousResponseSmollm = "I don't see any previous response to correct. Please try one of the example corrections first.";
            }
            
            console.log('Previous responses:', { previousResponseSmollm2, previousResponseSmollm });
            
            // Disable the remask button during processing
            remaskButton.disabled = true;

            try {
                console.log('Adding new user message...');
                // Add new user message: "Correct the upper answer"
                addMessage("Correct the upper answer", 'user', smollm2Messages);
                addMessage("Correct the upper answer", 'user', smollmMessages);
                
                console.log('Adding assistant responses...');
                // Add assistant responses that repeat the previous answers
                addMessage(previousResponseSmollm2, 'assistant', smollm2Messages);
                addMessage(previousResponseSmollm, 'assistant', smollmMessages);
                
                console.log('Remask completed successfully!');
                
            } catch (error) {
                console.error('Error during remask:', error);
                addMessage('Sorry, I encountered an error during remask. Please try again.', 'assistant', smollm2Messages);
                addMessage('Sorry, I encountered an error during remask. Please try again.', 'assistant', smollmMessages);
            } finally {
                remaskButton.disabled = false;
            }
        });
    } else {
        console.error('Remask button not found in DOM');
    }

    // Initialize the interface - no input to focus anymore
});
