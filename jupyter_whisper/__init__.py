from .__version__ import __version__
from .search import search_online

__all__ = ['search_online', '__version__']
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
DEBUG = False  # Set this to True to enable debug output

# Add OpenAI client initialization
client = OpenAI()  # Will use OPENAI_API_KEY from environment  # Will use OPENAI_API_KEY from environment

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
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not found in environment")
    
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
        "max_tokens": 1024
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

def run_server():
    import asyncio
    from uvicorn.config import Config
    from uvicorn.server import Server
    
    port = 5000
    max_retries = 3
    
    # Check if server already exists
    if check_existing_server(port):
        return
    
    # Add lock file to prevent race conditions
    lock_file = f"/tmp/jchat_server_{port}.lock"
    try:
        if os.path.exists(lock_file):
            # Check if the lock file is stale (older than 1 minute)
            if time.time() - os.path.getctime(lock_file) > 60:
                os.remove(lock_file)
            else:
                if DEBUG:
                    print("Another server startup in progress, waiting...")
                time.sleep(2)
                # Recheck server after waiting
                if check_existing_server(port):
                    return
                
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
            
        if DEBUG:
            print(f"Starting new FastAPI server on port {port}...")
            print(f"API Key present: {'ANTHROPIC_API_KEY' in os.environ}")
        
        # Shutdown any existing non-responsive server
        shutdown_existing_server()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        nest_asyncio.apply()
        
        config = Config(
            app=app, 
            host="0.0.0.0", 
            port=port, 
            log_level="info" if DEBUG else "warning",
            timeout_keep_alive=30,  # Reduce keep-alive timeout
            limit_concurrency=100   # Limit concurrent connections
        )
        server = Server(config=config)
        
        try:
            loop.run_until_complete(server.serve())
            if DEBUG:
                print("Server started successfully!")
        except Exception as e:
            if DEBUG:
                print(f"Failed to start server: {e}")
            raise
    finally:
        # Clean up lock file
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except Exception as e:
            if DEBUG:
                print(f"Error removing lock file: {e}")

@app.get("/status")
async def status():
    """Health check endpoint"""
    return {
        "status": "ok",
        "pid": os.getpid(),
        "timestamp": time.time(),
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
        package_dir = os.path.dirname(os.path.abspath(__file__))
        static_dir = os.path.join(package_dir, 'static')
        
        with open(os.path.join(static_dir, 'main.js'), 'r') as f:
            main_js = f.read()
        with open(os.path.join(static_dir, 'voicerecorder.js'), 'r') as f:
            voice_js = f.read()
            
        # Combine the JS code
        js_code = voice_js + "\n\n" + main_js  # Load voice recorder first
        
        # Replace debug value
        js_code = js_code.replace('{debug_value}', 'true' if DEBUG else 'false')
        
        display(Javascript(js_code))
        
    except FileNotFoundError as e:
        print(f"Error: Could not find JavaScript files: {e}")
    except Exception as e:
        print(f"Error loading JavaScript files: {e}")

# Modify the server startup section to include the JS injection
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
inject_js()  # Add this line to inject the JavaScript when module is loaded