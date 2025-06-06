import os
import time
import requests
import threading
import psutil
import nest_asyncio
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from .config import get_config_manager
from IPython.display import display, Javascript
from .__version__ import __version__
from openai import OpenAI
from pathlib import Path
from typing import Optional
import sys

# Add configuration for package paths
PACKAGE_ROOT = Path(__file__).parent.absolute()
SITE_PACKAGES = Path(sys.prefix) / 'lib' / 'python{}.{}'.format(*sys.version_info[:2]) / 'site-packages'

class ServerConfig:
    def __init__(self):
        self.debug: bool = False
        self.allowed_origins: list = ["http://localhost:8888"]  # Restrict CORS
        self.package_paths: list = [str(PACKAGE_ROOT), str(SITE_PACKAGES)]

config = ServerConfig()

# Global flag to track server initialization
_server_initialized = False

client = None  # Initialize as None initially

def get_openai_client() -> Optional[OpenAI]:
    global client
    try:
        if client is None:
            config_manager = get_config_manager()
            api_key = config_manager.get_api_key('OPENAI_API_KEY')
            if api_key:
                client = OpenAI(api_key=api_key)
                return client
            else:
                print("Warning: OpenAI API key not configured. Audio transcription will be unavailable.")
                print("Run setup_jupyter_whisper() to configure your API keys.")
        return client
    except Exception as e:
        print(f"Error initializing OpenAI client: {str(e)}")
        return None


class TextRequest(BaseModel):
    selectedText: str

DEBUG = False  
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if DEBUG:
        print("Server shutting down...")
    # Add any cleanup code here if needed

app = FastAPI(lifespan=lifespan)

# Add CORS middleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=3600,  # Cache preflight requests for 1 hour
)


@app.post("/quick_edit")
async def quick_edit(request: TextRequest):
    if DEBUG:
        print(
            f"Received request with text length: {len(request.selectedText)}")

    config = get_config_manager()
    active_profile_name = config.get_active_quick_edit_profile()
    if not active_profile_name:
        raise HTTPException(
            status_code=400,
            detail="No active quick edit profile found"
        )

    profiles = config.get_quick_edit_profiles()
    active_profile = profiles.get(active_profile_name)
    if not active_profile:
        raise HTTPException(
            status_code=400,
            detail=f"Profile '{active_profile_name}' not found"
        )

    provider = active_profile.get('provider')
    model = active_profile.get('model')
    system_prompt = active_profile.get('system_prompt')

    api_key_name_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "grok": "GROK_API_KEY",
        "GEMINI": "GEMINI_API_KEY",
        "gpt4o-latest": "OPENAI_API_KEY",
    }
    api_key_name = api_key_name_map.get(provider)

    if not provider or not api_key_name:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider}' is not supported for quick edit."
        )

    api_key = config.get_api_key(api_key_name)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"{api_key_name} not found. Please run setup_jupyter_whisper() to configure."
        )

    url, headers, data = None, None, None

    if provider == 'anthropic':
        url = 'https://api.anthropic.com/v1/messages'
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        data = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": request.selectedText}],
            "max_tokens": 8192
        }
    elif provider in ['grok', 'GEMINI', 'gpt4o-latest']:
        base_urls = {
            'grok': 'https://api.x.ai/v1/chat/completions',
            'GEMINI': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
            'gpt4o-latest': 'https://api.openai.com/v1/chat/completions'
        }
        url = base_urls[provider]
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.selectedText}
            ],
            "max_tokens": 8192
        }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if DEBUG:
            print(f"HTTP Error: {str(e)}")
            print(f"Response content: {e.response.text}")
        raise HTTPException(
            status_code=500, detail=f"Anthropic API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        if DEBUG:
            print(f"Request Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        if DEBUG:
            print(f"Unexpected Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/audio")
async def process_audio(audio: UploadFile = File(...)):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    # Add debug logging
    if DEBUG:
        print("Audio processing request received")
        print(f"Current OpenAI client configuration:")
        print(
            f"- Environment key: {os.environ.get('OPENAI_API_KEY', 'Not set')[:8]}...")

    client = get_openai_client()
    if client is None:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key not configured. Please run setup_jupyter_whisper() first."
        )

    # More debug logging
    if DEBUG:
        print(f"OpenAI client initialized with key: {client.api_key[:8]}...")

    # List of supported audio formats
    SUPPORTED_FORMATS = ['flac', 'm4a', 'mp3', 'mp4',
        'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']

    try:
        # Check file extension
        file_extension = audio.filename.split('.')[-1].lower()
        if file_extension not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported formats: {SUPPORTED_FORMATS}"
            )

        # Save the uploaded file temporarily
        temp_file_path = f"temp_{audio.filename}"
        with open(temp_file_path, "wb") as temp_file:
            contents = await audio.read()
            temp_file.write(contents)

        # Open and transcribe the audio file using Whisper
        with open(temp_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        if DEBUG:
            print(f"Transcript: {transcription}")

        # Clean up temporary file
        # os.remove(temp_file_path)

        # Return the actual transcription text
        return {"text": transcription}

    except HTTPException as he:
        raise he
    except Exception as e:
        if DEBUG:
            print(f"Audio processing error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process audio: {str(e)}")
    finally:
        # Ensure temp file is cleaned up even if an error occurs
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def shutdown_existing_server():
    if DEBUG:
        print("Checking for existing server on port 5000...")

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Get connections separately
            connections = proc.net_connections()
            for conn in connections:
                if hasattr(conn, 'laddr') and hasattr(conn.laddr, 'port') and conn.laddr.port == 5000:
                    if DEBUG:
                        print(f"Found process using port 5000: PID {proc.pid}")
                    proc.terminate()
                    proc.wait()  # Wait for the process to terminate
                    if DEBUG:
                        print("Successfully terminated existing server")
                    return
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception as e:
            if DEBUG:
                print(f"Error checking process {proc.pid}: {e}")
            continue


def check_existing_server(port=5000, retries=3, delay=0.5):
    """Check if there's an existing server running with retries"""
    for attempt in range(retries):
        try:
            response = requests.get(
                f"http://localhost:{port}/status", timeout=1)
            if response.status_code == 200:
                # Verify it's our server by checking response format
                data = response.json()
                if "status" in data and "pid" in data:
                    if DEBUG:
                        print(
                            f"Found existing server on port {port} (PID: {data['pid']})")
                    return True
        except requests.exceptions.RequestException:
            if DEBUG and attempt == retries - 1:
                print(
                    f"No existing server found on port {port} after {retries} attempts")
            time.sleep(delay)
            continue
    return False



def start_server_if_needed():
    """Start server only if no server is running"""
    global _server_initialized

    # Prevent multiple initialization attempts
    if _server_initialized:
        return

    try:
        response = requests.get('http://localhost:5000/status', timeout=1)
        if response.status_code == 200:
            server_info = response.json()
            print(f"Using existing server (PID: {server_info.get('pid')})")
            if DEBUG:
                print(f"Server version: {server_info.get('version')}")
                print(
                    f"Memory usage: {server_info.get('memory_usage', 0):.2f} MB")
            _server_initialized = True
            return
    except requests.exceptions.RequestException:
        if DEBUG:
            print("No existing server found, starting new one...")

        # Start new server in a thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Wait for server to be ready
        for _ in range(5):  # Try 5 times
            time.sleep(1)  # Wait a bit between attempts
            try:
                requests.get('http://localhost:5000/status', timeout=1)
                _server_initialized = True
                return
            except requests.exceptions.RequestException:
                continue

        if DEBUG:
            print("Warning: Server may not have started properly")


def run_server():
    """Start the FastAPI server"""
    import asyncio
    from uvicorn.config import Config
    from uvicorn.server import Server

    if DEBUG:
        print("Starting FastAPI server on port 5000...")

    config = Config(
        app=app,
        host="0.0.0.0",
        port=5000,
        log_level="warning",  # Reduce logging noise
        timeout_keep_alive=30,
        limit_concurrency=100
    )

    server = Server(config=config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nest_asyncio.apply()

    try:
        loop.run_until_complete(server.serve())
    except Exception as e:
        if DEBUG:
            print(f"Server error: {e}")


# Initialize only once at import
start_server_if_needed()


@app.get("/status")
async def status():
    """Health check endpoint with server info"""
    return {
        "status": "ok",
        "pid": os.getpid(),
        "timestamp": time.time(),
        "version": __version__,
        "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024  # MB
    }

# Add graceful shutdown handler


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    if DEBUG:
        print("Server shutting down...")
    # Add any cleanup code here if needed

# Add this JavaScript injection function before the server startup


def inject_js():
    # Enhanced cleanup code
    cleanup_js = """
    if (window.cleanupAllHandlers) {
        window.cleanupAllHandlers();
        console.log('Cleaned up existing handlers');
    }
    
    // Ensure any existing popup is properly removed
    if (window.streamingPopup && window.streamingPopup.hide) {
        window.streamingPopup.hide();
    }
    
    // Add delay before new handlers
    setTimeout(() => {
        // Your existing popup initialization code
    }, 100);
    """
    display(Javascript(cleanup_js))

    # Then read and inject the main code
    try:
        import os
        import pkg_resources

        # Get the package's installed location
        static_dir = pkg_resources.resource_filename(
            'jupyter_whisper', 'static')

        # Ensure static directory exists
        os.makedirs(static_dir, exist_ok=True)

        # Define default JS content if files don't exist
        default_main_js = """// Default main.js content
console.log('Using default main.js content');
// Add your default main.js content here
"""
        default_voice_js = """// Default voicerecorder.js content
console.log('Using default voicerecorder.js content');
// Add your default voicerecorder.js content here
"""

        # Try to read files, use defaults if not found
        try:
            with open(os.path.join(static_dir, 'main.js'), 'r') as f:
                main_js = f.read()
        except FileNotFoundError:
            main_js = default_main_js

        try:
            with open(os.path.join(static_dir, 'voicerecorder.js'), 'r') as f:
                voice_js = f.read()
        except FileNotFoundError:
            voice_js = default_voice_js

        streaming_popup_js = """
            // Add streaming popup HTML if it doesn't exist
            if (!document.getElementById('streaming-popup')) {
                const popupHtml = `
                    <div id="streaming-popup" style="display: none; position: fixed; bottom: 20px; right: 20px; 
                        background: white; border: 1px solid #ccc; padding: 10px; border-radius: 5px; 
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 300px; z-index: 1000">
                        <div style="margin-bottom: 5px; font-weight: bold;">Assistant is thinking...</div>
                        <div id="streaming-content" style="font-size: 0.9em; color: #666; max-height: 150px; 
                            overflow-y: auto; white-space: pre-wrap;"></div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', popupHtml);
            }

            // Add streaming popup controls with auto-scroll functionality
            window.streamingPopup = {
                autoScroll: true,
                
                show: function() {
                    const popup = document.getElementById('streaming-popup');
                    const content = document.getElementById('streaming-content');
                    
                    popup.style.display = 'block';
                    
                    // Add scroll event listener to detect manual scrolling
                    content.addEventListener('scroll', () => {
                        const isScrolledToBottom = content.scrollHeight - content.clientHeight <= content.scrollTop + 1;
                        this.autoScroll = isScrolledToBottom;
                    });
                },
                
                hide: function() {
                    document.getElementById('streaming-popup').style.display = 'none';
                    document.getElementById('streaming-content').textContent = '';
                    this.autoScroll = true;  // Reset auto-scroll when hiding
                },
                
                updateContent: function(text) {
                    const content = document.getElementById('streaming-content');
                    content.textContent = text;
                    
                    // Auto-scroll if enabled
                    if (this.autoScroll) {
                        content.scrollTop = content.scrollHeight;
                    }
                }
            };

            // Clean up function
            window.cleanupStreamingPopup = function() {
                const popup = document.getElementById('streaming-popup');
                if (popup) {
                    popup.remove();
                }
            };
            """
            
        # Combine all JavaScript code
        js_code = streaming_popup_js + "\n\n" + voice_js + "\n\n" + main_js

        # Replace debug value
        js_code = js_code.replace(
            '{debug_value}', 'true' if DEBUG else 'false')

        display(Javascript(js_code))

    except Exception as e:
        print(f"Warning: Error loading JavaScript files: {e}")
        print("Some features may be limited.")

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": __version__}

