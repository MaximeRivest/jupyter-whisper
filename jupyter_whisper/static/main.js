const DEBUG = {debug_value};
    
const style = document.createElement('style');
style.textContent = `
    .ai-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    }
    .ai-modal-content {
        background: white;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
    }
    .ai-spinner {
        display: inline-block;
        width: 50px;
        height: 50px;
        border: 3px solid #f3f3f3;
        border-top: 3px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// Function to show modal
function showModal() {
    const modal = document.createElement('div');
    modal.className = 'ai-modal-overlay';
    modal.innerHTML = `
        <div class="ai-modal-content">
            <div class="ai-spinner"></div>
            <p>Processing with Claude...</p>
        </div>
    `;
    document.body.appendChild(modal);
    return modal;
}


// Function to get text from clipboard
async function getClipboardText() {
    try {
        return await navigator.clipboard.readText();
    } catch (error) {
        console.error('Failed to read clipboard:', error);
        return null;
    }
}

async function keyboardShortcutHandler(event) {
    if (event.ctrlKey && event.shiftKey && event.key === 'A') {
        event.preventDefault();
        if (DEBUG) console.log("here we go...!")

        const activeElement = document.activeElement;
        let selectedText = window.getSelection().toString();
        
        // If no text is selected, try to get from clipboard
        if (!selectedText) {
            selectedText = await getClipboardText();
        }
        
        if (selectedText) {
            const modal = showModal();
            try {
                if (DEBUG) console.log("Sending request to server...");
                const response = await fetch('http://localhost:5000/quick_edit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        selectedText: selectedText
                    })
                });
                
                if (DEBUG) console.log("Response status:", response.status);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    if (DEBUG) console.error("Server error:", errorText);
                    throw new Error(`Server error: ${errorText}`);
                }

                const data = await response.json();
                if (DEBUG) console.log("Received response:", data);
                
                let newText;
                if (data.content && data.content[0] && data.content[0].text) {
                    // Handle Anthropic-like response
                    newText = data.content[0].text;
                } else if (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) {
                    // Handle OpenAI-like response
                    newText = data.choices[0].message.content;
                } else {
                    throw new Error("Invalid or unexpected response format from server");
                }

                // Replace the selected text with the response text
                const pasteEvent = new ClipboardEvent('paste', {
                    bubbles: true,
                    cancelable: true,
                    clipboardData: new DataTransfer()
                });
                pasteEvent.clipboardData.setData('text/plain', newText);
                activeElement.dispatchEvent(pasteEvent);

            } catch (error) {
                if (DEBUG) console.error('Error:', error);
                const errorMessage = error.response ? 
                    await error.response.text() : 
                    'Failed to process request. Please check if the server is running and your API key is set.';
                alert(`Error: ${errorMessage}`);
            } finally {
                modal.remove();
            }
        } else {
            if (DEBUG) console.log('No text selected or in clipboard');
        }
            
        // Modify the voice recording shortcuts
        if (event.ctrlKey && event.shiftKey && event.key === 'Z') {
            event.preventDefault();
            if (VoiceRecorderModule) {
                // Let VoiceRecorderModule handle the recording toggle
                return;  // VoiceRecorderModule will handle this shortcut
            }
        }
    }
}

// Add global instance tracking at the top
let mainInstance = null;

// Modify the initialization function
function initializeKeyboardShortcuts() {
    // Clean up existing instance if it exists
    if (mainInstance) {
        document.removeEventListener('keydown', keyboardShortcutHandler);
        console.log('Cleaned up existing main keyboard handler');
    }

    // Initialize new handler
    document.addEventListener('keydown', keyboardShortcutHandler);
    mainInstance = keyboardShortcutHandler;
    
    if (DEBUG) console.log('Main keyboard handler initialized. Press Ctrl+Shift+A to trigger the API request.');
}

// Modify the cleanup function
window.cleanupAllHandlers = function() {
    // Clean up main handler
    if (mainInstance) {
        document.removeEventListener('keydown', mainInstance);
        mainInstance = null;
        console.log('Main keyboard handler cleaned up');
    }
    
    // Clean up voice recorder
    if (VoiceRecorderModule && typeof VoiceRecorderModule.cleanup === 'function') {
        VoiceRecorderModule.cleanup();
    }
};


// Initialize everything
initializeKeyboardShortcuts();

