'use strict';

// Helper function for modal
function showAudioProcessingModal() {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 20px;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        z-index: 1000;
    `;
    modal.textContent = 'Processing audio...';
    document.body.appendChild(modal);
    return modal;
}

const VoiceRecorderModule = (function() {
    // Static instance (Singleton)
    let globalInstance = null;
    
    // Private variables
    let mediaRecorder;
    let audioChunks = [];
    let keyboardHandler;
    let isInitialized = false;

    // Private functions
    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                await sendAudioToAPI(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            console.log("Recording started");
        } catch (error) {
            console.error("Error accessing microphone:", error);
            alert("Failed to access microphone. Please ensure microphone permissions are granted.");
        }
    }

    async function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            console.log("Recording stopped");
        }
    }

    async function sendAudioToAPI(audioBlob) {
        const modal = showAudioProcessingModal();
        try {
            // Convert audio blob to .wav format
            const formData = new FormData();
            const wavFile = new File([audioBlob], 'recording.wav', {
                type: 'audio/wav'
            });
            formData.append('audio', wavFile);

            const response = await fetch('http://localhost:5000/audio', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("API Response:", data);
            
            // Extract the text and ensure it's a string
            let transcribedText = '';
            if (typeof data.text === 'string') {
                transcribedText = data.text;
            } else if (typeof data.text?.text === 'string') {
                transcribedText = data.text.text;
            } else if (data.text) {
                transcribedText = JSON.stringify(data.text);
            }
            
            // Add !! around the transcribed text
            transcribedText = `!! ${transcribedText} !!`;
            
            if (transcribedText) {
                const activeElement = document.activeElement;
                if (activeElement.tagName === 'TEXTAREA' || activeElement.contentEditable === 'true') {
                    const pasteEvent = new ClipboardEvent('paste', {
                        bubbles: true,
                        cancelable: true,
                        clipboardData: new DataTransfer()
                    });
                    pasteEvent.clipboardData.setData('text/plain', transcribedText);
                    activeElement.dispatchEvent(pasteEvent);
                }
            }
        } catch (error) {
            console.error("Error sending audio to API:", error);
            alert(`Failed to process audio: ${error.message}`);
        } finally {
            modal.remove();
        }
    }

    function keyboardShortcutHandler(event) {
        if (event.ctrlKey && event.shiftKey && event.key === 'Z') {
            event.preventDefault();
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                console.log('Stopping recording...');
                stopRecording();
                // Visual feedback
                alert('Recording stopped - processing audio...');
            } else {
                console.log('Starting recording...');
                startRecording();
                // Visual feedback
                alert('Recording started - press Ctrl+Shift+Z again to stop');
            }
        }
    }

    class VoiceRecorder {
        constructor() {
            if (globalInstance) {
                return globalInstance;
            }
            globalInstance = this;
            this.initialize();
        }

        initialize() {
            // Only set up new handler if not already initialized
            if (!isInitialized) {
                keyboardHandler = keyboardShortcutHandler;
                document.addEventListener('keydown', keyboardHandler);
                isInitialized = true;
                console.log('Voice recorder module initialized. Use Ctrl+Shift+Z to toggle recording.');
            }
        }

        cleanup() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            if (keyboardHandler) {
                document.removeEventListener('keydown', keyboardHandler);
            }
            mediaRecorder = null;
            audioChunks = [];
            isInitialized = false;
            console.log('Voice recorder module cleaned up.');
        }

        // Add public methods for recording
        async startRecording() {
            return startRecording();
        }

        async stopRecording() {
            return stopRecording();
        }
    }

    return new VoiceRecorder();
})();

