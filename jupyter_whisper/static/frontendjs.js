%%javascript
// Function to get XSRF token from cookies
function getXSRFToken() {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === '_xsrf') {
            return value;
        }
    }
    return '';
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

// Main event listener for keyboard shortcut
document.addEventListener('keydown', async function(event) {
    if (event.ctrlKey && event.shiftKey && event.key === 'A') {
        event.preventDefault();
        console.log("here we go...!")

        const activeElement = document.activeElement;
        let selectedText = window.getSelection().toString();
        
        // If no text is selected, try to get from clipboard
        if (!selectedText) {
            selectedText = await getClipboardText();
        }
        
        if (selectedText) {
            try {
                console.log(selectedText)
                const response = await fetch('http://localhost:5000/proxy', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        selectedText: selectedText
                    }),
                    credentials: 'include'
                });
                console.log("should be done")
                // Check for response status and handle errors
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                // Parse the JSON response from the server
                const data = await response.json();

                // Extract the response text from the API result
                const newText = data.content[0].text;

                // Replace the selected text with the response text
                const pasteEvent = new ClipboardEvent('paste', {
                    bubbles: true,
                    cancelable: true,
                    clipboardData: new DataTransfer()
                });
                pasteEvent.clipboardData.setData('text/plain', newText);
                activeElement.dispatchEvent(pasteEvent);

            } catch (error) {
                console.error('Error:', error);
            }
        } else {
            console.log('No text selected or in clipboard');
        }
    }
});

console.log('Keyboard shortcut handler installed. Press Ctrl+Shift+A to trigger the API request.');
