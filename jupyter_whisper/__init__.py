from .__version__ import __version__
from .search import search_online
from .config import get_config_manager

__all__ = ['search_online', '__version__', 'setup_jupyter_whisper']
from claudette import *
from anthropic.types import Message, TextBlock
from IPython.core.magic import register_cell_magic
from IPython.display import display, update_display, clear_output, Markdown
import time
import re
from .search import search_online
from IPython.display import Javascript
from ipylab import JupyterFrontEnd
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
import uvicorn
import os
import requests
import threading
import nest_asyncio
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import psutil
from contextlib import asynccontextmanager
from datetime import datetime
from io import StringIO
import sys
from IPython.core.interactiveshell import ExecutionResult
from IPython.utils.capture import capture_output

sp = """
You are a general and helpful assistant.

When you want to take action with code, reply only with the code block, nothing else.
Using the code block you can run shell commands, python code, etc.

You can run javascript code using code block. This javascript
will run in the browser in the dev console.

Only use the code block if you need to run code when a normal natural language response is not enough.

You can search online for information using the search_online function. Wait for the user to ask you to search online.
like this:

```python
style = "Be precise and concise. Use markdown code blocks for python code."
question = "How many stars are there in our galaxy?"
search_online(style, question)
```


```python
style = "Be thorough and detailed. Use markdown code blocks for python code."
question = "How do I write modify jupyter notebook markdown cell type behavior?"
search_online(style, question)
```

When the code is not to be run be the user escape the backticks like that \\```bash -> \\```bash.

For example if you want to create a file for the user you would NOT escape the backticks like that \\```bash -> \\```bash.
If you want to create a file for the user you would use ```bash -> ```bash.
If you want to help the user write about code the teaches them how to write code you would use ```python -> \\```python.
"""
#model = "claude-3-haiku-20240307"
model = "claude-3-5-sonnet-20241022"

# Add debug flag at the top with other imports
DEBUG = True  # Set this to True to enable debug output

# Add OpenAI client initialization
config_manager = get_config_manager()
missing_keys = config_manager.ensure_api_keys()
if missing_keys:
    print(f"Warning: Missing API keys: {', '.join(missing_keys)}")
    print("Run setup_jupyter_whisper() to configure your API keys.")

# Modify OpenAI client initialization to be lazy-loaded
client = None  # Initialize as None initially

def get_openai_client():
    global client
    if client is None:
        config_manager = get_config_manager()
        if config_manager.get_api_key('OPENAI_API_KEY'):
            client = OpenAI()  # Will use OPENAI_API_KEY from environment/config
        else:
            print("Warning: OpenAI API key not configured. Audio transcription will be unavailable.")
            print("Run setup_jupyter_whisper() to configure your API keys.")
    return client

# Add global variable to store outputs
cell_outputs = []  # List to store outputs
output_catcher = None  # Global variable to hold the OutputCatcher instance

class OutputCatcher:
    def __init__(self):
        self.stdout = StringIO()
        self.stderr = StringIO()
        self._stdout = sys.stdout
        self._stderr = sys.stderr

    def __enter__(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        return self

    def __exit__(self, *args):
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def get_output(self):
        return {
            'stdout': self.stdout.getvalue(),
            'stderr': self.stderr.getvalue()
        }

def create_assistant_cell():
    a = get_ipython()
    last_response = c.h[-1].content[0].text
    
    # Replace the simple regex split with a more sophisticated parser
    def split_code_blocks(text):
        parts = []
        current_part = ""
        in_code_block = False
        code_lang = None
        i = 0
        
        while i < len(text):
            # Check if we're looking at an escaped backtick
            if text[i:i+4] == '\\```':
                current_part += '```'  # Add as literal backticks
                i += 4
                continue
                
            # Check if we're looking at a commented backtick
            is_commented = False
            if i > 0:
                line_start = text.rfind('\n', 0, i)
                if line_start == -1:
                    line_start = 0
                line_prefix = text[line_start:i].lstrip()
                is_commented = line_prefix.startswith('#') or line_prefix.startswith('//')
            
            if text[i:i+3] == '```' and not in_code_block and not is_commented:
                # Start of code block
                if current_part.strip():
                    parts.append(current_part)
                current_part = text[i:i+3]
                i += 3
                # Check for language identifier
                lang_end = text.find('\n', i)
                if lang_end != -1:
                    code_lang = text[i:lang_end].strip()
                    current_part += code_lang + '\n'
                    i = lang_end + 1
                in_code_block = True
            elif text[i:i+3] == '```' and in_code_block:
                # End of code block
                current_part += text[i:i+3]
                parts.append(current_part)
                current_part = ""
                in_code_block = False
                code_lang = None
                i += 3
            else:
                current_part += text[i]
                i += 1
        
        if current_part.strip():
            parts.append(current_part)
        
        return parts

    parts = split_code_blocks(last_response)
    
    app = JupyterFrontEnd()
    
    count = 0
    for i, part in enumerate(parts):
        if part.strip():  # Skip empty parts
            if part.lstrip().startswith('```'):
                # Handle code block
                code_content = part
                if code_content.startswith('```python'):
                    # Python gets special treatment - no %% prefix needed
                    code_content = code_content.replace('```python\n', '', 1).replace('```', '')
                    code_content = f"\n#%%assistant {len(c.h)-1}\n{code_content}"
                else:
                    # For any other language:
                    # 1. Extract language from ```language pattern
                    # 2. Convert to magic command format
                    match = re.match(r'```(\w+)\n', code_content)
                    if match:
                        lang = match.group(1)
                        # Special case: 'r' needs to be uppercase
                        lang = 'R' if lang.lower() == 'r' else lang
                        # Remove ```language and closing ```
                        code_content = re.sub(r'```\w+\n', '', code_content, 1).replace('```', '')
                        # Format with %%language on first line
                        code_content = f"%%{lang}\n#%%assistant {len(c.h)-1}\n{code_content}"
                
                # Insert code cell
                if count == 0:
                    app.commands.execute('notebook:insert-cell-above')
                    time.sleep(0.2)
                    count += 1
                else:
                    app.commands.execute('notebook:insert-cell-below')
                    time.sleep(0.3)
                    count += 1
                app.commands.execute('notebook:replace-selection', {'text': code_content})
            else:
                # Handle markdown content
                markdown_content = f"%%assistant {len(c.h)-1}\n\n{part}\n"
                if count == 0:
                    app.commands.execute('notebook:insert-cell-above')
                    time.sleep(0.1)
                    count += 1
                else:
                    app.commands.execute('notebook:insert-cell-below')
                    time.sleep(0.3)
                    count += 1
                app.commands.execute('notebook:replace-selection', {'text': markdown_content})
                app.commands.execute('notebook:change-cell-to-markdown')
                app.commands.execute('notebook:run-cell')
            
            time.sleep(0.4)
            # Scroll to make the active cell visible
            app.commands.execute('notebook:scroll-cell-center')
    
    # Create the next user cell
    app.commands.execute('notebook:insert-cell-below')
    time.sleep(0.2)
    app.commands.execute('notebook:replace-selection', {'text': f"%%user {len(c.h)}\n\n"})
    # Ensure the final cell is visible
    app.commands.execute('notebook:scroll-cell-center')
    # clear cell outputs from the last user message
    c.h[-2]['content'][0].text = re.sub(r'<cell_outputs>.*</cell_outputs>', '', c.h[-2]['content'][0].text)

def go(cell):
    # Replace empty cell or whitespace-only cell with 'continue'
    if not cell or cell.isspace():
        cell = 'continue'
        
    # Process any {} expressions in the cell using regex
    pattern = r'\{([^}]+)\}'
    
    def eval_match(match):
        expr = match.group(1)
        try:
            # Get the IPython shell and its user namespace
            shell = get_ipython()
            # Evaluate the expression in the user namespace
            result = eval(expr, shell.user_ns)
            return str(result)
        except Exception as e:
            return f"[Error: {str(e)}]"
    
    cell = re.sub(pattern, eval_match, cell)
    app = JupyterFrontEnd()
    words = 0
    text = ""
    for word_piece in c(cell + f"""<cell_outputs> In here you have all the current jupyter context that we run so far. Use judiciously. {cell_outputs}</cell_outputs>""", stream=True):
        words += 1
        text += word_piece
        if words % 20 == 0:
            clear_output(wait=False)
            display(Markdown(text))
            app.commands.execute('notebook:scroll-cell-center')
    clear_output(wait=False)
    create_assistant_cell()

# Initialize c in the global namespace when module is loaded
c = Chat(model, sp = sp)
get_ipython().user_ns['c'] = c  # Make c available in user's namespace

@register_cell_magic
def user(line, cell):
    global c
    parts = line.split(':')
    index = int(parts[0]) if parts[0] else len(c.h)
    wipe = len(parts) > 1 and parts[1] == 'wipe'
    
    if index == 0:
        c = Chat(model, sp = sp)
        get_ipython().user_ns['c'] = c  # Update c in user's namespace when reset
    
    if index < len(c.h):
        if wipe:
            c.h = c.h[:index]
            go(cell)

        else:
            c.h[index] = {'role': 'user', 'content': cell}
    else:
        go(cell)

@register_cell_magic
def assistant(line, cell):
    parts = line.split(':')
    index = int(parts[0]) if parts[0] else len(c.h) - 1
    wipe = len(parts) > 1 and parts[1] == 'wipe'
    
    if wipe:
        c.h = c.h[:index]
    
    if index < len(c.h):
        c.h[index] = {'role': 'assistant', 'content': cell}
    else:
        c.h.append({'role': 'assistant', 'content': cell})
    
    # Create a new cell below with %%user magic
    new_cell = f"%%user {len(c.h)}\n\n"
    a = get_ipython()
    a.set_next_input(new_cell, replace=False)



a = get_ipython()
# Load R and Julia extensions if available
try:
    a.run_line_magic('load_ext', 'rpy2.ipython')
except:
    pass
try:
    a.run_line_magic('load_ext', 'sql')
except:
    pass

a.set_next_input("%%user 0\n\n", replace=False)

from IPython import get_ipython
from datetime import datetime

ip = get_ipython()

def determine_cell_type(raw_cell):
    """Determine the cell type based on content"""
    if not raw_cell:
        return 'unknown'
    
    # Check for magic commands
    if raw_cell.startswith('%%'):
        magic_type = raw_cell[2:].split('\n')[0].strip()
        return f'magic_{magic_type}'
    
    # Check for markdown cells (usually start with #, >, or contain markdown syntax)
    if raw_cell.lstrip().startswith(('#', '>', '-', '*', '```')):
        return 'markdown'
    
    # Check if it's mostly code
    code_indicators = ['def ', 'class ', 'import ', 'from ', 'print(', 'return ', '    ']
    if any(indicator in raw_cell for indicator in code_indicators):
        return 'code'
        
    return 'text'

def pre_run_cell(info):
    global output_catcher
    output_catcher = OutputCatcher()
    output_catcher.__enter__()  # Start capturing

def post_run_cell(result):
    global cell_outputs, output_catcher

    # Finish capturing
    if output_catcher is not None:
        output_catcher.__exit__()
        outputs = output_catcher.get_output()
        output_catcher = None
    else:
        outputs = {'stdout': '', 'stderr': ''}

    # Get raw cell content
    raw_cell = getattr(result.info, 'raw_cell', '')
    exec_count = getattr(result.info, 'execution_count', None)

    # Initialize output data
    output_data = {
        'execution_count': exec_count,
        'input': raw_cell,
        'output': None,
        'stdout': outputs['stdout'],
        'stderr': outputs['stderr'],
        'error': None,
        'timestamp': datetime.now(),
        'type': determine_cell_type(raw_cell)
    }

    # Display captured stdout/stderr immediately if not empty
    if outputs['stdout']:
        print(outputs['stdout'], end='')
    if outputs['stderr']:
        print(outputs['stderr'], file=sys.stderr, end='')

    # Check for errors
    if hasattr(result, 'error_in_exec') and result.error_in_exec is not None:
        output_data['error'] = str(result.error_in_exec)
        if hasattr(result, 'traceback'):
            output_data['stderr'] += '\n'.join(result.traceback)

    # Get the result of the cell execution
    if hasattr(result, 'result') and result.result is not None:
        output_data['output'] = str(result.result)

    # Collect display outputs
    if hasattr(result, 'display_outputs'):
        for display_output in result.display_outputs:
            if display_output.output_type == 'stream':
                if display_output.name == 'stdout':
                    output_data['stdout'] += display_output.text
                elif display_output.name == 'stderr':
                    output_data['stderr'] += display_output.text
            elif display_output.output_type == 'error':
                output_data['error'] = display_output.evalue
                output_data['stderr'] += '\n'.join(display_output.traceback)
            elif display_output.output_type == 'execute_result':
                if 'text/plain' in display_output.data:
                    output_data['output'] = display_output.data['text/plain']
            elif display_output.output_type == 'display_data':
                # Handle outputs from magic commands like %%bash
                if 'text/plain' in display_output.data:
                    output_data['stdout'] += display_output.data['text/plain']
                elif 'text/html' in display_output.data:
                    output_data['stdout'] += display_output.data['text/html']

    # Append to cell_outputs
    if raw_cell.strip():
        cell_outputs.append(output_data)

    # Debug logging
    if DEBUG:
        print(f"Captured output for cell type {output_data['type']}:")
        print(f"stdout: {output_data['stdout']}")
        print(f"stderr: {output_data['stderr']}")
        print(f"output: {output_data['output']}")
        print(f"error: {output_data['error']}")

# Register the hooks
ip.events.register('pre_run_cell', pre_run_cell)
ip.events.register('post_run_cell', post_run_cell)



def hist():
    """Display the chat history in a nicely formatted markdown view"""
    history_md = "# 💬 Chat History\n\n"
    for i, msg in enumerate(c.h):
        role = msg['role'].title()
        
        # Handle different content structures
        if isinstance(msg['content'], list):
            # Handle list of content blocks (Claude 3 format)
            content = '\n'.join(block.text for block in msg['content'] 
                              if isinstance(block, TextBlock))
        else:
            # Handle direct string content
            content = msg['content']
            
        # Add emoji based on role
        emoji = "🤖" if role == "Assistant" else "👤"
        
        # Add message header with role and index
        history_md += f"### {emoji} {role} [{i}]\n\n"
        
        # Add message content with proper indentation
        content = content.strip()  # Remove extra whitespace
        history_md += f"{content}\n\n"
        
        # Add a subtle separator
        history_md += "<hr style='border-top: 1px solid #ccc'>\n\n"
    
    display(Markdown(history_md))


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import threading
import nest_asyncio

class TextRequest(BaseModel):
    selectedText: str

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/proxy")
async def proxy(request: TextRequest):
    if DEBUG:
        print(f"Received request with text length: {len(request.selectedText)}")
    
    config = get_config_manager()
    api_key = config.get_api_key('ANTHROPIC_API_KEY')
    
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail="ANTHROPIC_API_KEY not found. Please run setup_jupyter_whisper() to configure."
        )
    
    url = 'https://api.anthropic.com/v1/messages'
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }

    data = {
        "model": "claude-3-5-sonnet-20241022",
        "system": """
You are a precise text and code editor. Your task is to:

1. Process provided text/code snippets
2. Make necessary improvements and corrections
3. Instructions are in !!double exclamation!!


Rules:
- Return ONLY the edited text/code
- Remove all double exclamation annotations in the final output
- Keep HTML comments if needed to explain rationale
- Maintain the original format and structure
- Focus on clarity, correctness and best practices

Example:
<example1>
user:
function hello() {
    console.log('hello') !!Add semicolon!!
}
assistant:
function hello() {
    console.log('hello');
}
</example1>

""",
        "messages": [
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
        raise HTTPException(status_code=500, detail=f"Anthropic API error: {str(e)}")
    except requests.exceptions.RequestException as e:
        if DEBUG:
            print(f"Request Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        if DEBUG:
            print(f"Unexpected Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/audio")
async def process_audio(audio: UploadFile = File(...)):
    # Add debug logging
    if DEBUG:
        print("Audio processing request received")
        print(f"Current OpenAI client configuration:")
        print(f"- Environment key: {os.environ.get('OPENAI_API_KEY', 'Not set')[:8]}...")
        
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
    SUPPORTED_FORMATS = ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']
    
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
        #os.remove(temp_file_path)
        
        # Return the actual transcription text
        return {"text": transcription}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        if DEBUG:
            print(f"Audio processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(e)}")
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
            response = requests.get(f"http://localhost:{port}/status", timeout=1)
            if response.status_code == 200:
                # Verify it's our server by checking response format
                data = response.json()
                if "status" in data and "pid" in data:
                    if DEBUG:
                        print(f"Found existing server on port {port} (PID: {data['pid']})")
                    return True
        except requests.exceptions.RequestException:
            if DEBUG and attempt == retries - 1:
                print(f"No existing server found on port {port} after {retries} attempts")
            time.sleep(delay)
            continue
    return False

# Global flag to track server initialization
_server_initialized = False

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
                print(f"Memory usage: {server_info.get('memory_usage', 0):.2f} MB")
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
    # First, inject cleanup code
    cleanup_js = """
    if (window.cleanupAllHandlers) {
        window.cleanupAllHandlers();
        console.log('Cleaned up existing handlers');
    }
    """
    display(Javascript(cleanup_js))
    
    # Then read and inject the main code
    try:
        import os
        import pkg_resources
        
        # Get the package's installed location
        static_dir = pkg_resources.resource_filename('jupyter_whisper', 'static')
        
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
            
        # Combine the JS code
        js_code = voice_js + "\n\n" + main_js
        
        # Replace debug value
        js_code = js_code.replace('{debug_value}', 'true' if DEBUG else 'false')
        
        display(Javascript(js_code))
        
    except Exception as e:
        print(f"Warning: Error loading JavaScript files: {e}")
        print("Some features may be limited.")

# Modify the server startup section to include the JS injection
start_server_if_needed()
inject_js()

def setup_jupyter_whisper():
    """Interactive setup for Jupyter Whisper"""
    config_manager = get_config_manager()
    
    print("Welcome to Jupyter Whisper Setup!")
    print("\nPlease enter your API keys (press Enter to skip):")
    
    keys = {
        'OPENAI_API_KEY': 'OpenAI API Key (for audio transcription)',
        'ANTHROPIC_API_KEY': 'Anthropic API Key (for Claude)',
        'PERPLEXITY_API_KEY': 'Perplexity API Key (for online search)'
    }
    
    for env_key, display_name in keys.items():
        current_value = config_manager.get_api_key(env_key)
        if current_value:
            print(f"\n{display_name} is already set.")
            change = input("Would you like to change it? (y/N): ").lower()
            if change == 'y':
                new_value = input(f"Enter new {display_name}: ").strip()
                if new_value:
                    config_manager.set_api_key(env_key, new_value)
        else:
            new_value = input(f"Enter {display_name}: ").strip()
            if new_value:
                config_manager.set_api_key(env_key, new_value)
    
    print("\nSetup complete! Configuration saved to:", config_manager.config_file)
    print("\nRestart your Jupyter kernel for changes to take effect.")

def ensure_fresh_server():
    """Ensure we have a fresh server running with current configuration"""
    if DEBUG:
        print("Ensuring fresh server instance...")
    
    # Always kill existing server first
    shutdown_existing_server()
    
    # Small delay to ensure port is freed
    time.sleep(0.5)
    
    # Start new server
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to be ready
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get('http://localhost:5000/status', timeout=1)
            if response.status_code == 200:
                if DEBUG:
                    print(f"Fresh server started successfully (PID: {response.json().get('pid')})")
                return True
        except requests.exceptions.RequestException:
            if i < max_retries - 1:  # Don't sleep on last attempt
                time.sleep(0.5)
    
    if DEBUG:
        print("Failed to start fresh server")
    return False

def check_server_status():
    """Check if there's an existing server and its version"""
    try:
        response = requests.get('http://localhost:5000/status', timeout=1)
        if response.status_code == 200:
            server_info = response.json()
            current_version = server_info.get('version')
            if current_version != __version__:
                print(f"\n⚠️ Warning: Using existing server running version {current_version}")
                print(f"Current package version is {__version__}")
                print("To use the latest version, restart the server with: refresh_jupyter_whisper()")
            if DEBUG:
                print(f"Connected to existing server (PID: {server_info.get('pid')})")
            return True
    except requests.exceptions.RequestException:
        return False

def refresh_jupyter_whisper():
    """Manually refresh the Jupyter Whisper server and configuration
    
    This will:
    1. Shutdown any existing server (warning: affects all notebooks using it)
    2. Clear cached configurations
    3. Start a fresh server with current settings
    
    Use with caution as it will impact all notebooks using the server.
    """
    print("⚠️ Warning: This will restart the server and affect all active notebooks.")
    confirm = input("Type 'yes' to continue: ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        return
    
    if DEBUG:
        print("Refreshing Jupyter Whisper...")
    
    # Shutdown existing server
    shutdown_existing_server()
    
    # Clear OpenAI client
    refresh_openai_client()
    
    # Start new server
    run_server()
    
    print("✅ Server refreshed successfully!")
    print("Note: You may need to restart kernels in affected notebooks.")

# Remove automatic initialization during import
def initialize_jupyter_whisper():
    """Initialize Jupyter Whisper components - must be called from within a notebook"""
    try:
        # Check if we're in IPython/Jupyter
        get_ipython()
    except NameError:
        print("Warning: Not running in IPython/Jupyter environment")
        return

    # Check server status first
    check_server_status()
    
    # Initialize components only if needed
    inject_js()
    
    # Make chat instance available
    c = Chat(model, sp=sp)
    get_ipython().user_ns['c'] = c

# Don't auto-initialize on import
# Instead, let users call it explicitly or use magic commands

def set_debug(value: bool):
    """Enable or disable debug mode"""
    global DEBUG
    DEBUG = value
    print(f"Debug mode {'enabled' if DEBUG else 'disabled'}")

def refresh_openai_client():
    """Force refresh the OpenAI client with current configuration"""
    global client
    client = None  # Reset the client
    
    # Force reload environment variables from config
    config_manager = get_config_manager()
    api_key = config_manager.get_api_key('OPENAI_API_KEY')
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
    
    return get_openai_client()  # Get a fresh client with new configuration
