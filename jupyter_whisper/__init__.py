from IPython import get_ipython
from .__version__ import __version__
import ipywidgets as widgets
from IPython.display import display
# Add at the top of the file, after initial imports
def show_loading_progress():
    progress = widgets.FloatProgress(
        value=0,
        min=0,
        max=100,
        description='Loading Jupyter Whisper:',
        bar_style='info',
        style={'bar_color': '#2196F3'},
        orientation='horizontal'
    )
    display(progress)
    return progress

# Initialize progress bar
loading_progress = show_loading_progress()

# After initial imports
loading_progress.value = 20
loading_progress.description = "Loading dependencies..."
from IPython import get_ipython
from .__version__ import __version__
from .search import search_online
from .config import get_config_manager
from IPython.display import display
__all__ = ['search_online', '__version__', 'setup_jupyter_whisper', 'c', "output_manager"]
from anthropic.types import TextBlock
from IPython.core.magic import register_cell_magic
from IPython.display import display,  clear_output, Markdown
import time
import re
from .search import search_online
from ipylab import JupyterFrontEnd
from .cell_outputs import simplify_markdown_from_history, extract_new_images
from openai import OpenAI
from collections import deque
from IPython.display import Javascript
import ipywidgets as widgets


from .search import search_online
from .config import get_config_manager

# After config setup
loading_progress.value = 40
loading_progress.description = "Initializing configuration..."
# Get model from config
config_manager = get_config_manager()
model = config_manager.get_model()

# Add debug flag at the top with other imports
DEBUG = False  # Set this to True to enable debug output

# Add OpenAI client initialization
config_manager = get_config_manager()
missing_keys = config_manager.ensure_api_keys()
if missing_keys:
    print(f"Warning: Missing API keys: {', '.join(missing_keys)}")
    print("Run setup_jupyter_whisper() to configure your API keys.")

# Modify OpenAI client initialization to be lazy-loaded
client = None  # Initialize as None initially



# Add global variable to store outputs
output_catcher = None  # Global variable to hold the OutputCatcher instance

# Replace the simple list with a deque of fixed size
captured_images = deque(maxlen=5)  # Will automatically maintain only the last 5 images

# After server setup
loading_progress.value = 60
loading_progress.description = "Setting up server..."
#----------------------------------------
# For magic cells
#----------------------------------------

def create_markdown_cell(content, app, count, c):
    markdown_content = f"%%assistant {len(c.h)-1}\n\n{content}\n"
    if count == 0:
        app.commands.execute('notebook:insert-cell-above')
        app.commands.execute('notebook:scroll-cell-center')
    else:
        app.commands.execute('notebook:insert-cell-below')
        app.commands.execute('notebook:scroll-cell-center')
    time.sleep(0.1)
    app.commands.execute(
        'notebook:replace-selection', {'text': markdown_content})
    time.sleep(0.1)
    app.commands.execute('notebook:change-cell-to-markdown')
    time.sleep(0.1)
    app.commands.execute('notebook:run-cell')
    time.sleep(0.1)
    
    
def create_code_cell(code_content, code_lang, app, count, c):
    code_content = code_content.strip()
    

    # For other languages (like bash), just use the language as the magic command
    if code_lang == "python":
        code_cell_content = f"#%%assistant {len(c.h)-1}\n{code_content}"
    elif code_lang == "javascript":
        code_cell_content = f"%%{code_lang}\n//%%assistant {len(c.h)-1}\n{code_content}"
    elif code_lang == "r":
        code_cell_content = f"%%R\n#%%assistant {len(c.h)-1}\n{code_content}"
    elif code_lang == "html":
        code_cell_content = f"%%html<!--%%assistant {len(c.h)-1}-->\n{code_content}"
    elif code_lang == "sql":
        code_cell_content = f"%%sql\n--%%assistant {len(c.h)-1}\n{code_content}"
    elif code_lang == "css":
        code_cell_content = f"%%css\n/*%%assistant {len(c.h)-1}*/\n{code_content}"

    else:
        code_cell_content = f"%%{code_lang}\n#%%assistant {len(c.h)-1}\n{code_content}"

    if count == 0:
        app.commands.execute('notebook:insert-cell-above')
        app.commands.execute('notebook:scroll-cell-center')
    else:
        app.commands.execute('notebook:insert-cell-below')
        app.commands.execute('notebook:scroll-cell-center')
    app.commands.execute(
        'notebook:replace-selection', {'text': code_cell_content})
    time.sleep(0.1)
    app.commands.execute('notebook:scroll-cell-center')


def go(cell):
    # Ensure server is running before first chat
    ensure_server()
    # Process expressions within {}
    pattern = r'\{([^}]+)\}'

    def eval_match(match):
        expr = match.group(1)
        try:
            shell = get_ipython()
            result = eval(expr, shell.user_ns)
            return str(result)
        except Exception as e:
            return f"[Error: {str(e)}]"

    cell = re.sub(pattern, eval_match, cell)

    global c, captured_images
    if c is None:
        print("❌ Chat instance not initialized. Please save your configuration.")
        return

    if not cell or cell.isspace():
        cell = 'proceed'

    app = JupyterFrontEnd()
    
    try:
        # Initialize variables for streaming parsing
        buffer = ""
        in_code_block = False
        code_block_lang = None
        cell_count = 0

        # Clear cell outputs from all previous messages
        for msg in c.h:
            if isinstance(msg['content'], str):
                msg['content'] = re.sub(r'<cell_outputs>.*</cell_outputs>', 
                                      '', 
                                      msg['content'], 
                                      flags=re.DOTALL)
            elif isinstance(msg['content'], list):
                for item in msg['content']:
                    if isinstance(item, dict) and 'text' in item:
                        item['text'] = re.sub(r'<cell_outputs>.*</cell_outputs>', 
                                              '', 
                                              item['text'], 
                                              flags=re.DOTALL)

        # Prepare message content with new cell outputs for the current user message
        message_content = {
            "type": "text",
            "text": cell + f"""<cell_outputs> {simplify_markdown_from_history(output_manager.history)}</cell_outputs>"""
        }

        # Stream the assistant's response
        display(Javascript("window.streamingPopup.show();"))
        clear_output(wait=True)
        
        # Add a small delay using time.sleep instead of async
        time.sleep(0.1)
                
        def update_streaming_content(text):
            safe_text = (text.replace('\\', '\\\\')
                            .replace('\n', '\\n')
                            .replace('\r', '\\r')
                            .replace("'", "\\'")
                            .replace('"', '\\"'))
            
            js_code = f"""
                (function() {{
                    if (window.streamingPopup) {{
                        requestAnimationFrame(() => {{
                            window.streamingPopup.updateContent('{safe_text}');
                        }});
                    }}
                }})();
            """
            display(Javascript(js_code))
            clear_output(wait=True)
            # Add small delay to prevent race conditions
            time.sleep(0.01)

        def process_stream_content(buffer, all_word_pieces, in_code_block, code_block_lang, cell_count, app, c):
            """
            Process streaming content and create appropriate cells.
            Args:
                buffer: Current chunk being processed
                all_word_pieces: Complete message received so far
                in_code_block: Whether we're currently in a code block
                code_block_lang: Current code block language if in a code block
                cell_count: Current cell count
                app: Jupyter app instance
                c: Chat instance
            Returns: (new_buffer, new_in_code_block, new_code_block_lang, new_cell_count)
            """
            while True:
                if not in_code_block:
                    code_block_start = buffer.find('```')
                    if code_block_start != -1:
                        # Check if we have enough content after ``` to determine the language
                        remaining = buffer[code_block_start + 3:]
                        if '\n' not in remaining:
                            # Look ahead in all_word_pieces to see if we have more context
                            full_remaining = all_word_pieces[len(all_word_pieces) - len(remaining):]
                            if '\n' not in full_remaining:
                                break
                        
                        markdown_content = buffer[:code_block_start].strip()
                        if markdown_content:
                            markdown_content = markdown_content.replace('`', '\\`')
                            create_markdown_cell(markdown_content, app, cell_count, c)
                            cell_count += 1
                        elif markdown_content == '':
                            create_markdown_cell('<br>', app, cell_count, c)
                            cell_count += 1
                        
                        buffer = buffer[code_block_start + 3:]
                        
                        # Try to find language in complete message if not in buffer
                        if '\n' not in buffer:
                            full_content = all_word_pieces[len(all_word_pieces) - len(buffer):]
                            lang_end = full_content.find('\n')
                            if lang_end != -1:
                                code_block_lang = full_content[:lang_end].strip()
                                buffer = full_content[lang_end + 1:]
                            else:
                                code_block_lang = ''
                        else:
                            lang_end = buffer.find('\n')
                            code_block_lang = buffer[:lang_end].strip()
                            buffer = buffer[lang_end + 1:]
                        
                        in_code_block = True
                    else:
                        break
                else:
                    code_block_end = buffer.find('```')
                    if code_block_end != -1:
                        code_content = buffer[:code_block_end].strip()
                        code_content = code_content.replace('`', '\\`')
                        create_code_cell(code_content, code_block_lang, app, cell_count, c)
                        cell_count += 1
                        buffer = buffer[code_block_end + 3:]
                        in_code_block = False
                        code_block_lang = None
                    else:
                        # Look ahead in complete message for code block end
                        remaining_content = all_word_pieces[len(all_word_pieces) - len(buffer):]
                        if '```' in remaining_content:
                            break  # Wait for more content as we know there's an end coming
                        
                        # If we're at the end of the message, handle incomplete code block
                        if len(buffer.strip()) > 0 and buffer == all_word_pieces:
                            code_content = buffer.strip()
                            code_content = code_content.replace('`', '\\`')
                            create_code_cell(code_content, code_block_lang, app, cell_count, c)
                            cell_count += 1
                            buffer = ""
                            in_code_block = False
                            code_block_lang = None
                        break
            
            return buffer, in_code_block, code_block_lang, cell_count

        buffer = ""
        all_word_pieces = ""
        for word_piece in c(
            message_content["text"],
            images=extract_new_images(output_manager.history),
            stream=True
        ):
            # Append the incoming word_piece
            if isinstance(word_piece, (list, TextBlock)):
                word = word_piece.text if hasattr(word_piece, 'text') else ''
            else:
                word = word_piece
            buffer += word
            all_word_pieces += word
            
            # Process the buffer content with complete message context
            buffer, in_code_block, code_block_lang, cell_count = process_stream_content(
                buffer, all_word_pieces, in_code_block, code_block_lang, cell_count, app, c
            )

            # Update streaming content
            update_streaming_content(all_word_pieces)

        # Ensure all content is processed before hiding popup
        time.sleep(3)
        display(Javascript("""
            requestAnimationFrame(() => {
                window.streamingPopup.hide();
            });
        """))
        clear_output(wait=True)

        # Handle any remaining content in the buffer after streaming completes
        if buffer.strip():
            if in_code_block:
                # Handle unclosed code block
                create_code_cell(buffer.strip(), code_block_lang, app, cell_count, c)
            else:
                create_markdown_cell(buffer.strip(), app, cell_count, c)
        # Create the next user cell
        app.commands.execute('notebook:insert-cell-below')
        time.sleep(0.1)
        app.commands.execute('notebook:replace-selection',
                             {'text': f"%%user {len(c.h)}\n\n"})
        app.commands.execute('notebook:scroll-cell-center')
        captured_images.clear()
    except Exception as e:
        print(f"❌ Error during magic cell execution: {str(e)}")
        
@register_cell_magic
def user(line, cell):
    global c
    parts = line.split(':')
    index = int(parts[0]) if parts[0] else len(c.h)
    action = parts[1] if len(parts) > 1 else None

    if index == 0:
        c = initialize_chat()
        c.h = []
        # Update c in user's namespace when reset
        get_ipython().user_ns['c'] = c

    if action == 'set':
        # Set the content without running or creating next cell
        if index < len(c.h):
            c.h[index] = {'role': 'user', 'content': cell}
        else:
            c.h.append({'role': 'user', 'content': cell})
        return  # Early return

    if index < len(c.h):
        if action == 'wipe':
            c.h = c.h[:index]
            go(cell)
        else:
            c.h[index] = {'role': 'user', 'content': cell}
            go(cell)
    else:
        go(cell)


@register_cell_magic
def assistant(line, cell):
    parts = line.split(':')
    index_str = parts[0]
    action = parts[1] if len(parts) > 1 else None

    # Parse main index
    main_index = int(index_str) if index_str else len(c.h) - 1

    if action == 'add':
        # For add action, concatenate with existing content
        if main_index < len(c.h):
            existing_content = c.h[main_index].get('content', '')
            if isinstance(existing_content, list):
                # Handle Claude 3 format - convert to string first
                existing_content = '\n'.join(block.text for block in existing_content
                                          if hasattr(block, 'text'))

            # Add a newline between existing and new content if both exist
            separator = '\n' if existing_content and cell else ''
            new_content = existing_content + separator + cell

            # Update the content
            c.h[main_index]['content'] = new_content
        else:
            # Append new entry if index doesn't exist
            c.h.append({'role': 'assistant', 'content': cell})
        return  # Early return

    elif action == 'set':
        # For set action, completely replace the content
        if main_index < len(c.h):
            c.h[main_index]['content'] = cell
        else:
            c.h.append({'role': 'assistant', 'content': cell})
        return  # Early return

    # Rest of the function remains unchanged...


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


ip = get_ipython()

#----------------------------------------
# For providing cell outputs to the model
#----------------------------------------
# After output manager setup
loading_progress.value = 80
loading_progress.description = "Configuring outputs..."
from .cell_outputs import JupyterOutputManager

# Initialize the output manager and register hooks
output_manager = JupyterOutputManager()
#----------------------------------------
# For the API
#----------------------------------------



# For the server
#----------------------------------------
from .server import start_server_if_needed, inject_js

# Modify the server startup section to include the JS injection
start_server_if_needed()
inject_js()



# 1. Lazy load the server components
_server_loaded = False

def ensure_server():
    """Lazy load and initialize server components only when needed"""
    global _server_loaded
    if not _server_loaded:
        from .server import start_server_if_needed, inject_js
        start_server_if_needed()
        inject_js()
        _server_loaded = True

# 2. Move server initialization out of main flow
def setup_jupyter_whisper(force_display=False):
    # Ensure server is running before showing setup UI
    ensure_server()
    try:
        import ipywidgets as widgets
        from IPython.display import display, HTML, clear_output

        config_manager = get_config_manager()

        # Global variables
        custom_providers = config_manager.get_custom_providers()
        profiles = config_manager.get_quick_edit_profiles()
        active_profile = config_manager.get_active_quick_edit_profile()
        profile_buttons = {}
        selected_provider = None

        # Event handler functions
        def update_model_options(*args):
            """Update model options in the Model tab when provider changes"""
            provider = provider_dropdown.value
            models = available_models_dict.get(provider, [])
            model_dropdown.options = models

            # Set default value safely
            if model_dropdown.value in models:
                pass
            elif models:
                model_dropdown.value = models[0]
            else:
                model_dropdown.value = None

        def on_provider_changed(change):
            """Handle provider change from the widget."""
            new_provider = change['new']
            update_model_options()
            config_manager.set_provider(new_provider)  # This will trigger the callback

        def on_model_changed(change):
            """Handle model change from the widget."""
            new_model = change['new']
            config_manager.set_model(new_model)  # This will trigger the callback

        def on_profile_button_clicked(button):
            """Handle profile button clicks"""
            profile_id = button._profile_id
            config_manager.set_active_quick_edit_profile(profile_id)
            # Update active button styles
            for btn in profile_buttons.values():
                btn.button_style = 'info' if btn._profile_id == profile_id else ''
            # Load profile settings into UI
            profile_data = profiles[profile_id]
            profile_name_input.value = profile_data['name']
            profile_provider_dropdown.value = profile_data.get('provider', 'grok')
            profile_model_dropdown.value = profile_data['model']
            profile_system_prompt.value = profile_data['system_prompt']

        def update_profile_model_options(*args):
            """Update model options in the Quick Edit tab when provider changes"""
            provider = profile_provider_dropdown.value
            models = available_models_dict.get(provider, [])
            profile_model_dropdown.options = models

            # Set default value safely
            if profile_model_dropdown.value in models:
                pass
            elif models:
                profile_model_dropdown.value = models[0]
            else:
                profile_model_dropdown.value = None

        def on_add_profile_clicked(button):
            """Handle adding a new profile"""
            new_profile_id = f'profile_{len(profiles) + 1}'
            new_profile_data = {
                'name': 'New Profile',
                'provider': provider_options[0] if provider_options else '',
                'model': '',
                'system_prompt': ''
            }
            profiles[new_profile_id] = new_profile_data
            config_manager.add_quick_edit_profile(
                name=new_profile_id,
                display_name=new_profile_data['name'],
                provider=new_profile_data['provider'],
                model=new_profile_data['model'],
                system_prompt=new_profile_data['system_prompt']
            )
            # Update UI
            update_profile_buttons()
            profile_buttons[new_profile_id].click()

        def on_delete_profile_clicked(button):
            """Handle deleting a profile"""
            profile_id = config_manager.get_active_quick_edit_profile()
            if profile_id == 'default':
                with status_output:
                    clear_output()
                    print("Cannot delete the default profile.")
                return
            config_manager.remove_quick_edit_profile(profile_id)
            # Update UI
            update_profile_buttons()
            # Set active profile to default
            profile_buttons['default'].click()

        def on_save_clicked(button):
            """Handle saving configurations"""
            # Save API keys
            for key_name, key_info in keys.items():
                key_value = key_info['widget'].value.strip()
                if key_value:
                    config_manager.set_api_key(key_name, key_value)
            # Save model and provider
            selected_provider = provider_dropdown.value
            selected_model = model_dropdown.value
            config_manager.set_model(selected_model, provider=selected_provider)
            # Save system prompt
            config_manager.set_system_prompt(system_prompt.value)
            # Save skip setup preference
            config_manager.set_config_value('SKIP_SETUP_POPUP', skip_setup_checkbox.value)
            # Save active quick edit profile
            profile_id = config_manager.get_active_quick_edit_profile()
            profile_data = profiles[profile_id]
            profile_data['name'] = profile_name_input.value.strip()
            profile_data['provider'] = profile_provider_dropdown.value
            profile_data['model'] = profile_model_dropdown.value
            profile_data['system_prompt'] = profile_system_prompt.value
            config_manager.add_quick_edit_profile(
                name=profile_id,
                display_name=profile_data['name'],
                provider=profile_data['provider'],
                model=profile_data['model'],
                system_prompt=profile_data['system_prompt']
            )
            with status_output:
                clear_output()
                print("Configuration saved successfully.")

        def on_reset_prompts_clicked(button):
            """Handle resetting prompts to default"""
            config_manager.set_system_prompt(config_manager.DEFAULT_CONFIG['system_prompt'])
            system_prompt.value = config_manager.get_system_prompt()
            with status_output:
                clear_output()
                print("System prompt reset to default.")

        def update_profile_buttons():
            """Update the profile buttons in the UI"""
            # Clear existing buttons
            profile_buttons_container.children = []
            profile_buttons.clear()
            # Recreate buttons
            for profile_id, profile in profiles.items():
                btn = widgets.Button(
                    description=profile['name'],
                    layout=widgets.Layout(margin='2px'),
                    button_style='info' if profile_id == active_profile else ''
                )
                btn._profile_id = profile_id  # Store profile ID
                profile_buttons[profile_id] = btn
                btn.on_click(on_profile_button_clicked)
            profile_buttons_container.children = list(profile_buttons.values())

        def on_custom_provider_selected(change):
            """Handle selection of a custom provider in Advanced Settings"""
            provider_name = change['new']
            if not provider_name:
                return
            provider_data = custom_providers[provider_name]
            provider_name_input.value = provider_name
            display_name_input.value = provider_data['name']
            models_input.value = ', '.join(provider_data['models'])
            initialization_code_input.value = provider_data['initialization_code']

        def on_add_new_provider_clicked(button):
            """Handle adding a new custom provider"""
            provider_name_input.value = ''
            display_name_input.value = ''
            models_input.value = ''
            initialization_code_input.value = ''

        def on_save_provider_clicked(button):
            """Handle saving a custom provider"""
            provider_name = provider_name_input.value.strip()
            display_name = display_name_input.value.strip()
            models = [m.strip() for m in models_input.value.split(',') if m.strip()]
            init_code = initialization_code_input.value
            if not provider_name or not display_name or not models or not init_code:
                with status_output:
                    clear_output()
                    print("Please fill in all fields for the provider.")
                return
            # Validate initialization code
            try:
                config_manager.validate_initialization_code(init_code)
            except ValueError as e:
                with status_output:
                    clear_output()
                    print(str(e))
                return
            config_manager.add_custom_provider(provider_name, display_name, models, init_code)
            # Update UI
            custom_provider_dropdown.options = list(custom_providers.keys())
            custom_provider_dropdown.value = provider_name
            with status_output:
                clear_output()
                print(f"Provider '{provider_name}' saved successfully.")

        def on_delete_provider_clicked(button):
            """Handle deleting a custom provider"""
            provider_name = custom_provider_dropdown.value
            if not provider_name:
                return
            config_manager.remove_custom_provider(provider_name)
            # Update UI
            custom_provider_dropdown.options = list(custom_providers.keys())
            provider_name_input.value = ''
            display_name_input.value = ''
            models_input.value = ''
            initialization_code_input.value = ''
            with status_output:
                clear_output()
                print(f"Provider '{provider_name}' deleted successfully.")

        # Check if setup should be skipped
        if not force_display and config_manager.get_config_value('SKIP_SETUP_POPUP', False):
            return

        # Create status output and buttons first
        status_output = widgets.Output()
        save_button = widgets.Button(
            description='Save Configuration',
            button_style='primary',
            icon='check'
        )
        reset_prompts_button = widgets.Button(
            description='Reset to Default Prompts',
            button_style='warning',
            icon='refresh'
        )
        skip_setup_checkbox = widgets.Checkbox(
            value=config_manager.get_config_value('SKIP_SETUP_POPUP', False),
            description='Don\'t show this setup popup on startup',
            indent=False,
            layout=widgets.Layout(margin='20px 0')
        )

        # Add collapsible container
        accordion = widgets.Accordion()
        main_container = widgets.VBox()

        # Style for the UI remains unchanged...

        display(HTML("""
        <style>
            .widget-label { font-weight: bold; }
            .setup-header { 
                font-size: 1.2em; 
                margin-bottom: 1em; 
                padding: 0.5em;
                background: #f0f0f0;
                border-radius: 4px;
                color: black;
            }
            .key-status {
                margin-top: 0.5em;
                font-style: italic;
            }
            .section-header {
                font-weight: bold;
                margin-top: 1em;
                margin-bottom: 0.5em;
                padding: 0.3em;
                background: #e0e0e0;
                border-radius: 4px;
            }
            .profile-button {
                margin: 2px;
                min-width: 120px;
            }
            .active-profile {
                background-color: #007bff;
                color: white;
            }
        </style>
        """))

        # Create tabs for different settings
        tab = widgets.Tab()
        api_keys_tab = widgets.VBox()
        model_tab = widgets.VBox()
        system_prompt_tab = widgets.VBox()
        quick_edit_tab = widgets.VBox()
        advanced_settings_tab = widgets.VBox()  # Renamed from custom_providers_tab

        # API Keys Section remains unchanged...

        keys = {
            'OPENAI_API_KEY': {
                'display': 'OpenAI API Key (for audio transcription)',
                'validate': lambda x: x.startswith('sk-') and len(x) > 20,
                'widget': None
            },
            # Include API keys for custom providers
        }

        # Include API keys for custom providers
        for provider_name, provider_info in custom_providers.items():
            key_name = f"{provider_name.upper()}_API_KEY"
            keys[key_name] = {
                'display': f'{provider_info["name"]} API Key',
                'validate': lambda x: len(x) > 0,  # Adjust validation as needed
                'widget': None
            }

        api_key_widgets = []
        for key_name, key_info in keys.items():
            current_value = config_manager.get_api_key(key_name)
            masked_value = f"{current_value[:8]}...{current_value[-4:]}" if current_value else ""

            key_input = widgets.Password(
                placeholder=f'Enter {key_info["display"]}',
                value=current_value or '',
                description=key_info['display'],
                style={'description_width': 'initial'},
                layout=widgets.Layout(width='80%')
            )

            keys[key_name]['widget'] = key_input
            api_key_widgets.append(key_input)
            if current_value:
                api_key_widgets.append(widgets.HTML(
                    f'<div class="key-status">Current value: {masked_value}</div>'
                ))

        api_keys_tab.children = api_key_widgets

        # **Model Selection Section**
        current_model, current_provider = config_manager.get_model()

        # Create provider dropdown with only custom providers
        provider_options = list(custom_providers.keys())
        provider_dropdown = widgets.Dropdown(
            options=provider_options,
            value=current_provider,
            description='Provider:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='50%')
        )

        # Create model dropdown
        available_models_dict = config_manager.get_available_models()
        model_dropdown = widgets.Dropdown(
            description='Model:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='50%')
        )

        # Initial update of model options
        update_model_options()

        # Link provider changes to model updates
        provider_dropdown.observe(on_provider_changed, names='value')
        model_dropdown.observe(on_model_changed, names='value')

        # Assemble model tab
        model_tab.children = [
            widgets.HTML('<div class="section-header">Model Selection</div>'),
            provider_dropdown,
            model_dropdown,
            widgets.HTML('<div class="key-status">Select the provider and model to use for chat interactions.</div>')
        ]

        # **System Prompt Section**

        system_prompt = widgets.Textarea(
            value=config_manager.get_system_prompt(),
            placeholder='Enter system prompt...',
            description='System Prompt:',
            disabled=False,
            layout=widgets.Layout(width='95%', height='400px'),
            continuous_update=True  # Enable continuous updates
        )

        # Add keyboard handler for system prompt
        system_prompt._dom_classes = system_prompt._dom_classes + ('jp-mod-accept-enter',)

        system_prompt_tab.children = [
            widgets.HTML('<div class="section-header">System Prompt</div>'),
            system_prompt,
            widgets.HTML('<div class="key-status">Customize the system prompt that defines the assistant\'s behavior.</div>')
        ]

        # **Quick Edit Profiles Section**

        # Profile selection buttons container
        profile_buttons_container = widgets.HBox(
            layout=widgets.Layout(flex_wrap='wrap', margin='10px 0')
        )

        # Create a button for each profile
        for profile_id, profile in profiles.items():
            btn = widgets.Button(
                description=profile['name'],
                layout=widgets.Layout(margin='2px'),
                button_style='info' if profile_id == active_profile else ''
            )
            btn._profile_id = profile_id  # Store profile ID
            profile_buttons[profile_id] = btn
            btn.on_click(on_profile_button_clicked)

        profile_buttons_container.children = list(profile_buttons.values())

        # Profile management buttons
        add_profile_button = widgets.Button(
            description='Add Profile',
            icon='plus',
            button_style='success',
            layout=widgets.Layout(margin='5px')
        )

        delete_profile_button = widgets.Button(
            description='Delete Profile',
            icon='trash',
            button_style='danger',
            layout=widgets.Layout(margin='5px')
        )

        # Profile editing widgets
        profile_name_input = widgets.Text(
            description='Profile Name:',
            layout=widgets.Layout(width='50%')
        )

        # Provider Dropdown for profiles
        profile_provider_dropdown = widgets.Dropdown(
            options=provider_options,
            description='Provider:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='50%')
        )

        profile_model_dropdown = widgets.Dropdown(
            description='Model:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='50%')
        )

        # Load the active profile's provider and model
        profile_data = profiles[active_profile]
        profile_provider = profile_data.get('provider', provider_options[0])  # Default to first provider if not set
        profile_model = profile_data['model']

        # Ensure the provider is valid
        if profile_provider not in provider_options:
            profile_provider = provider_options[0]

        profile_provider_dropdown.value = profile_provider

        # Update models based on provider
        update_profile_model_options()

        # Ensure the model is valid
        if profile_model in profile_model_dropdown.options:
            profile_model_dropdown.value = profile_model
        elif profile_model_dropdown.options:
            profile_model_dropdown.value = profile_model_dropdown.options[0]
        else:
            profile_model_dropdown.value = None

        # Observe changes in provider dropdown to update models
        profile_provider_dropdown.observe(update_profile_model_options, names='value')

        profile_system_prompt = widgets.Textarea(
            value=profile_data['system_prompt'],
            placeholder='Enter Quick Edit system prompt...',
            description='System Prompt:',
            disabled=False,
            layout=widgets.Layout(width='95%', height='200px')
        )

        # Assemble Quick Edit tab
        quick_edit_tab.children = [
            widgets.HTML('<div class="section-header">Quick Edit Profiles</div>'),
            profile_buttons_container,
            widgets.HBox([add_profile_button, delete_profile_button]),
            widgets.HTML('<div class="section-header">Profile Settings</div>'),
            profile_name_input,
            profile_provider_dropdown,
            profile_model_dropdown,
            profile_system_prompt,
            widgets.HTML('<div class="key-status">Configure how the AI processes your selected text when using Ctrl+Shift+A.</div>')
        ]

        # **Advanced Settings Tab (formerly Custom Providers)**
        # Widgets for custom providers
        custom_provider_dropdown = widgets.Dropdown(
            options=list(custom_providers.keys()),
            description='Select Provider:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='50%')
        )

        provider_name_input = widgets.Text(
            description='Provider Name:',
            layout=widgets.Layout(width='50%')
        )

        display_name_input = widgets.Text(
            description='Display Name:',
            layout=widgets.Layout(width='50%')
        )

        models_input = widgets.Text(
            description='Models (comma-separated):',
            layout=widgets.Layout(width='100%')
        )

        initialization_code_input = widgets.Textarea(
            description='Initialization Code:',
            layout=widgets.Layout(width='100%', height='300px')
        )

        add_new_provider_button = widgets.Button(
            description='Add New Provider',
            icon='plus',
            button_style='success',
            layout=widgets.Layout(margin='5px')
        )

        save_provider_button = widgets.Button(
            description='Save Provider',
            icon='save',
            button_style='primary',
            layout=widgets.Layout(margin='5px')
        )

        delete_provider_button = widgets.Button(
            description='Delete Provider',
            icon='trash',
            button_style='danger',
            layout=widgets.Layout(margin='5px')
        )

        provider_buttons = widgets.HBox([
            add_new_provider_button,
            save_provider_button,
            delete_provider_button
        ])

        # Assemble advanced settings tab
        advanced_settings_tab.children = [
            widgets.HTML('<div class="section-header">Advanced Settings</div>'),
            custom_provider_dropdown,
            provider_buttons,
            provider_name_input,
            display_name_input,
            models_input,
            initialization_code_input,
            widgets.HTML('<div class="key-status">Define custom providers with their models and initialization code.</div>')
        ]

        # Update tab children and titles
        tab.children = [api_keys_tab, model_tab, system_prompt_tab, quick_edit_tab, advanced_settings_tab]
        tab.set_title(0, "API Keys")
        tab.set_title(1, "Model")
        tab.set_title(2, "System Prompt")
        tab.set_title(3, "Quick Edit")
        tab.set_title(4, "Advanced Settings")

        # Create the main container with all widgets
        main_container.children = [
            tab,
            skip_setup_checkbox,
            status_output,
            widgets.HBox([save_button, reset_prompts_button])
        ]

        # Add the main container to the accordion
        accordion.children = [main_container]
        accordion.set_title(0, '🔧 Jupyter Whisper Setup')
        accordion.selected_index = 0  # Open by default

        # Display the accordion (which contains all other widgets)
        display(accordion)

        # Bind button events
        add_profile_button.on_click(on_add_profile_clicked)
        delete_profile_button.on_click(on_delete_profile_clicked)
        save_button.on_click(on_save_clicked)
        reset_prompts_button.on_click(on_reset_prompts_clicked)

        # Bind events for custom providers
        custom_provider_dropdown.observe(on_custom_provider_selected, names='value')
        add_new_provider_button.on_click(on_add_new_provider_clicked)
        delete_provider_button.on_click(on_delete_provider_clicked)
        save_provider_button.on_click(on_save_provider_clicked)

        # Initial button setup
        update_profile_buttons()

    except ImportError:
        print("Please install ipywidgets: pip install ipywidgets")
    except Exception as e:
        print(f"\nError during setup: {str(e)}")
        print("Please try again or report this issue if it persists.")

# Call setup on import if needed
setup_jupyter_whisper()

# 3. Defer server initialization until first chat interaction
def initialize_chat():
    """Initialize chat based on configured provider and listen for changes."""
    ensure_server()  # Ensure server is running before chat initialization
    global c
    config_manager = get_config_manager()
    model, provider = config_manager.get_model()
    system_prompt = config_manager.get_system_prompt()
    history = c.h if c else []  # Preserve history if c exists

    try:
        # Get custom providers
        custom_providers = config_manager.get_custom_providers()
        
        
        # Check if current provider is custom

        # Check if current provider is custom
        if provider in custom_providers:
            # Execute provider initialization code
            c = config_manager.execute_provider_initialization(
                provider_name=provider,
                model=model,
                system_prompt=system_prompt,
                history=history  # Pass existing history
            )

            # Register callbacks to reinitialize chat when provider or model changes
            def on_provider_change(new_provider):
                initialize_chat()  # Reinitialize chat with new provider

            def on_model_change(new_model):
                initialize_chat()  # Reinitialize chat with new model

            config_manager.register_change_callback('provider', on_provider_change)
            config_manager.register_change_callback('model', on_model_change)

            # Add Chat class to globals
            globals()['Chat'] = c.__class__
        else:
            raise ValueError(f"Provider '{provider}' is not recognized.")

        # Update the user namespace
        ip = get_ipython()
        ip.user_ns['c'] = c
        ip.user_ns['Chat'] = c.__class__

        return c

    except Exception as e:
        print(f"Error initializing chat: {str(e)}")
        return None

# Initialize global variable
c = None

# Initialize chat when module is loaded
c = initialize_chat()

loading_progress.value = 100
loading_progress.description = "Ready!"

# Clean up
time.sleep(0.5)
loading_progress.close()