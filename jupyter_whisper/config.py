import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

class ConfigManager:
    AVAILABLE_MODELS = {
        'anthropic': [
            'claude-3-5-sonnet-20241022',
            'claude-3-5-haiku-20241022',
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307'
        ],
        'openai': [
            'gpt-4o'
        ],
        'xai': [],  # To be filled later
        'llama': [],  # To be filled later
        'custom': []  # New provider for custom implementations
    }

    DEFAULT_CONFIG = {
        'api_keys': {},
        'preferences': {
            'SKIP_SETUP_POPUP': False,
            'MODEL': 'claude-3-5-sonnet-20241022',
            'MODEL_PROVIDER': 'anthropic',
            'QUICK_EDIT_MODEL': 'claude-3-5-sonnet-20241022',
            'ACTIVE_QUICK_EDIT_PROFILE': 'default',
            'QUICK_EDIT_PROFILES': {
                'default': {
                    'name': 'Default Editor',
                    'provider': 'anthropic',
                    'model': 'claude-3-5-sonnet-20241022',
                    'system_prompt': """
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
"""
                },
                'code_review': {
                    'name': 'Code Reviewer',
                    'model': 'claude-3-5-sonnet-20241022',
                    'system_prompt': """
You are a thorough code reviewer. Your task is to:

1. Review code for best practices and potential issues
2. Suggest improvements and optimizations
3. Focus on maintainability and performance

Rules:
- Return the improved code with clear comments explaining changes
- Maintain the original structure unless changes are necessary
- Focus on practical, production-ready improvements
"""
                },
                'documentation': {
                    'name': 'Documentation Helper',
                    'model': 'claude-3-5-sonnet-20241022',
                    'system_prompt': """
You are a documentation specialist. Your task is to:

1. Improve documentation and comments
2. Add clear explanations and examples
3. Ensure consistency in documentation style

Rules:
- Focus on clarity and completeness
- Add docstrings and comments where needed
- Follow documentation best practices
"""
                }
            },
            "CUSTOM_PROVIDERS": {
            "grok": {
                "name": "grok",
                "models": [
                    "grok"
                ],
                "initialization_code": "import os\nfrom typing import Optional, List, Generator, Union\nfrom openai import OpenAI\nfrom jupyter_whisper.config import get_config_manager\n\nclass Chat:\n    def __init__(self, model: Optional[str] = None, sp: str = ''):\n        self.model = \"grok-beta\"  # Hardcoded model\n        config = get_config_manager()\n        api_key = config.get_api_key('GROK_API_KEY')\n        if not api_key:\n            raise ValueError(\"GROK_API_KEY not found in configuration\")\n        self.client = OpenAI(\n            api_key=api_key,\n            base_url=\"https://api.x.ai/v1\"\n        )\n        self.sp = sp\n        self.h = []  # History\n\n    def __call__(self, \n                 message: str, \n                 max_tokens: int = 4096, \n                 stream: bool = True,\n                 temperature: float = 0) -> Union[str, Generator[str, None, str]]:\n        try:\n            # Add user message to history\n            self.h.append({\"role\": \"user\", \"content\": message})\n            \n            # Get response from x.ai\n            response = self.client.chat.completions.create(\n                model=self.model,\n                messages=[\n                    {\"role\": \"system\", \"content\": self.sp},\n                    *self.h\n                ],\n                max_tokens=max_tokens,\n                stream=stream,\n                temperature=temperature\n            )\n            \n            if stream:\n                full_response = \"\"\n                try:\n                    for chunk in response:\n                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:\n                            text = chunk.choices[0].delta.content\n                            #print(text, end='', flush=True)\n                            full_response += text\n                            yield text\n                except Exception as e:\n                    print(f\"Error during streaming: {e}\")\n                    raise\n                finally:\n                    if full_response:\n                        # Add complete response to history after streaming is done\n                        self.h.append({\"role\": \"assistant\", \"content\": full_response})\n                    print()  # New line after completion\n                return full_response\n            else:\n                # Handle non-streaming response\n                assistant_message = response.choices[0].message.content\n                self.h.append({\"role\": \"assistant\", \"content\": assistant_message})\n                return assistant_message \n        except Exception as e:\n            print(f\"Error in chat: {e}\")\n            raise\n\n"
            },
            "gemini-1.5-pro-002": {
                "name": "gemini-1.5-pro-002",
                "models": [
                    "gemini-1.5-pro-002"
                ],
                "initialization_code": "import os\nfrom typing import Optional, List, Generator, Union\nfrom openai import OpenAI\nfrom jupyter_whisper import get_config_manager\nclass Chat:\n    def __init__(self, model: Optional[str] = None, sp: str = ''):\n        self.model = \"gemini-1.5-pro-002\"  # Hardcoded model\n        config = get_config_manager()\n        api_key = config.get_api_key('GEMINI-1.5-PRO-002_API_KEY')\n        if not api_key:\n            raise ValueError(\"GEMINI-1.5-PRO-002_API_KEY not found in configuration\")\n        self.client = OpenAI(\n            api_key=api_key,\n            base_url=\"https://generativelanguage.googleapis.com/v1beta/openai/\"\n        )\n        self.sp = sp\n        self.h = []  # History\n\n    def __call__(self, \n                 message: str, \n                 max_tokens: int = 4096, \n                 stream: bool = True,\n                 temperature: float = 0) -> Union[str, Generator[str, None, str]]:\n        try:\n            # Add user message to history\n            self.h.append({\"role\": \"user\", \"content\": message})\n            \n            # Get response from x.ai\n            response = self.client.chat.completions.create(\n                model=self.model,\n                messages=[\n                    {\"role\": \"system\", \"content\": self.sp},\n                    *self.h\n                ],\n                max_tokens=max_tokens,\n                stream=stream,\n                temperature=temperature\n            )\n            \n            if stream:\n                full_response = \"\"\n                try:\n                    for chunk in response:\n                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:\n                            text = chunk.choices[0].delta.content\n                            #print(text, end='', flush=True)\n                            full_response += text\n                            yield text\n                except Exception as e:\n                    print(f\"\\nError during streaming: {e}\")\n                    raise\n                finally:\n                    if full_response:\n                        # Add complete response to history after streaming is done\n                        self.h.append({\"role\": \"assistant\", \"content\": full_response})\n                    #print()  # New line after completion\n                return full_response\n            else:\n                # Handle non-streaming response\n                assistant_message = response.choices[0].message.content\n                self.h.append({\"role\": \"assistant\", \"content\": assistant_message})\n                return assistant_message\n                \n        except Exception as e:\n            print(f\"Error in chat: {e}\")\n            raise"
            },
            "gpt4o-latest": {
                "name": "gpt4o-latest",
                "models": [
                    "gpt-4o"
                ],
                "initialization_code": "import os\nfrom typing import Optional, List, Generator, Union\nfrom openai import OpenAI\nfrom jupyter_whisper.config import get_config_manager\n\nclass Chat:\n    def __init__(self, model: Optional[str] = None, sp: str = ''):\n        self.model = \"gpt-4o\"  # Hardcoded model\n        config = get_config_manager()\n        api_key = config.get_api_key('GPT4O-LATEST_API_KEY')\n        if not api_key:\n            raise ValueError(\"GPT4O-LATEST_API_KEY not found in configuration\")\n        self.client = OpenAI(\n            api_key=api_key\n        )\n        self.sp = sp\n        self.h = []  # History\n\n    def __call__(self, \n                 message: str, \n                 max_tokens: int = 4096, \n                 stream: bool = True,\n                 temperature: float = 0) -> Union[str, Generator[str, None, str]]:\n        try:\n            # Add user message to history\n            self.h.append({\"role\": \"user\", \"content\": message})\n            \n            # Get response from x.ai\n            response = self.client.chat.completions.create(\n                model=self.model,\n                messages=[\n                    {\"role\": \"system\", \"content\": self.sp},\n                    *self.h\n                ],\n                max_tokens=max_tokens,\n                stream=stream,\n                temperature=temperature\n            )\n            \n            if stream:\n                full_response = \"\"\n                try:\n                    for chunk in response:\n                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:\n                            text = chunk.choices[0].delta.content\n                            #print(text, end='', flush=True)\n                            full_response += text\n                            yield text\n                except Exception as e:\n                    print(f\"Error during streaming: {e}\")\n                    raise\n                finally:\n                    if full_response:\n                        # Add complete response to history after streaming is done\n                        self.h.append({\"role\": \"assistant\", \"content\": full_response})\n                    print()  # New line after completion\n                return full_response\n            else:\n                # Handle non-streaming response\n                assistant_message = response.choices[0].message.content\n                self.h.append({\"role\": \"assistant\", \"content\": assistant_message})\n                return assistant_message \n        except Exception as e:\n            print(f\"Error in chat: {e}\")\n            raise"
            },
            "ollama": {
                "name": "ollama",
                "models": [
                    "llama2b"
                ],
                "initialization_code": "import os\nfrom typing import Optional, List, Generator, Union\nfrom openai import OpenAI\nfrom jupyter_whisper.config import get_config_manager\n\nclass Chat:\n    def __init__(self, model: Optional[str] = None, sp: str = ''):\n        self.model = \"llama3.2\"  # Hardcoded model\n        config = get_config_manager()\n        self.client = OpenAI(\n            api_key='ollama',\n            base_url=\"http://localhost:11434/v1\"\n        )\n        self.sp = sp\n        self.h = []  # History\n\n    def __call__(self, \n                 message: str, \n                 max_tokens: int = 4096, \n                 stream: bool = True,\n                 temperature: float = 0) -> Union[str, Generator[str, None, str]]:\n        try:\n            # Add user message to history\n            self.h.append({\"role\": \"user\", \"content\": message})\n            \n            # Get response from x.ai\n            response = self.client.chat.completions.create(\n                model=self.model,\n                messages=[\n                    {\"role\": \"system\", \"content\": self.sp},\n                    *self.h\n                ],\n                max_tokens=max_tokens,\n                stream=stream,\n                temperature=temperature\n            )\n            \n            if stream:\n                full_response = \"\"\n                try:\n                    for chunk in response:\n                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:\n                            text = chunk.choices[0].delta.content\n                            #print(text, end='', flush=True)\n                            full_response += text\n                            yield text\n                except Exception as e:\n                    print(f\"Error during streaming: {e}\")\n                    raise\n                finally:\n                    if full_response:\n                        # Add complete response to history after streaming is done\n                        self.h.append({\"role\": \"assistant\", \"content\": full_response})\n                    print()  # New line after completion\n                return full_response\n            else:\n                # Handle non-streaming response\n                assistant_message = response.choices[0].message.content\n                self.h.append({\"role\": \"assistant\", \"content\": assistant_message})\n                return assistant_message \n        except Exception as e:\n            print(f\"Error in chat: {e}\")\n            raise"
            }
        },
        "QUICK_EDIT_SYSTEM_PROMPT": "\nYou are a precise text and code editor. Your task is to:\n\n1. Process provided text/code snippets\n2. Make necessary improvements and corrections\n3. Instructions are in !!double exclamation!!\n\nRules:\n- Return ONLY the edited text/code\n- Remove all double exclamation annotations in the final output\n- Keep HTML comments if needed to explain rationale\n- Maintain the original format and structure\n- Focus on clarity, correctness and best practices\n"
    },
        'system_prompt': """
You are a general and helpful assistant.

When you want to take action with code, reply only with the code block, nothing else.
Using the code block you can run shell commands, python code, etc.

You can run javascript code using code block. This javascript
will run in the browser in the dev console.

Only use the code block if you need to run code when a normal natural language response is not enough.

You can search online for information using the search_online function. Wait for the user to ask you to search online.
like this:

```python
from jupyter_whisper import search_online
style = "Be precise and concise. Use markdown code blocks for python code."
question = "How many stars are there in our galaxy?"
search_online(style, question)
```


```python
from jupyter_whisper import search_online
style = "Be thorough and detailed. Use markdown code blocks for python code."
question = "How do I write modify jupyter notebook markdown cell type behavior?"
search_online(style, question)
```

For the above search_online you will have to wait for the users next response to know about the result.
If the user respond with "continue" and the cell_outputs after you gave a search_online response you will find the results in the last cell_output.

When the code is not to be run be the user escape the backticks like that \\```bash -> \\```bash.

For example if you want to create a file for the user you would NOT escape the backticks like that \\```bash -> \\```bash.
If you want to create a file for the user you would use ```bash -> ```bash.
If you want to help the user write about code the teaches them how to write code you would use ```python -> \\```python.

You are an AI assistant running within Jupyter Whisper, with the following key capabilities and context:

1. Voice Interaction Features:
   - You recognize text between !! marks as voice input from users
   - Voice Flow Commands:
     * Ctrl+Shift+Z: Toggles voice recording (start/stop)
     * Ctrl+Shift+A: Processes selected text through Claude Sonnet
   - All voice input appears between !! marks and should be treated as precise instructions

2. Technical Environment:
   - Running in JupyterLab 4.0+ environment
   - Integrated with Claude 3.5 Sonnet
   - FastAPI server running on port 5000 for audio/text processing
   - Access to Perplexity AI for advanced search
   - Real-time streaming responses capability

3. Notebook Management:
   - Can create notebooks in '~/whispers' (adapt to current os) folder (chat1.ipynb, whisper1.ipynb etc.) Make this a 2 step process where you first look at the user's OS, the whisper folder, its content and then with that information you can next create a new whisper and maybe even provide a clickable link to it.
   - Recommend '0scratch.ipynb' or '0notes.ipynb' for workspace
   - Can access conversation history via hist() command
   - The user chat using magic commands: %%user [index], %%assistant [index] (you should not have to change your response style in any way jupyter_whisper handles it, but good for you to know)
   - Magic Commands:
        * %%user [index]:set - Sets/replaces user message at given index
        * %%assistant [index]:set - Sets/replaces assistant message at given index
        * %%assistant [index]:add - Concatenates content to existing assistant message at given index
        * Examples:
        ```python
        %%assistant 3:set
        # This replaces the entire message at index 3
        print("Hello")

        %%assistant 3:add
        # This adds to the existing message at index 3
        print("World")
        ```
        
4. Code Handling:
   - Break code into small, executable chunks especially for teaching or taking action wiith code (Which we encourage you to do!), still balance that with coding best practice especially if you are helping building software not just doing interactive/terminal/repl things.
   - Consider notebook cell execution context (but also you normal markdown style response is expected by jupyter whisper parser)
   - Handle terminal/REPL commands the expects interactivity appropriately.
   - Wait for cell_outputs before proceeding with complex operations

5. Installation Context:
   - Requirements: Python 3.7+, JupyterLab 4.0+/Notebook 7.0+
   - API keys needed: Anthropic, OpenAI (optional), Perplexity
   - Server management awareness (port 5000, persistence between sessions)

6. Configuration Management:
   - You can modify configuration settings directly using ConfigManager:
   ```python
   from jupyter_whisper.config import get_config_manager
   config = get_config_manager()
   
   # Change the model
   config.set_model('claude-3-5-sonnet-20241022')
   
   # Update system prompt
   config.set_system_prompt("Your new system prompt here")
   
   # Set API keys (if provided by user)
   config.set_api_key('ANTHROPIC_API_KEY', 'your-key-here')
   
   # Get current settings
   current_model = config.get_model()
   current_prompt = config.get_system_prompt()
   
   # Set other preferences
   config.set_config_value('SKIP_SETUP_POPUP', True)
   ```
   
   Available models:
   - claude-3-5-sonnet-20241022
   - claude-3-5-haiku-20241022
   - claude-3-opus-20240229
   - claude-3-sonnet-20240229
   - claude-3-haiku-20240307

   YOU ABSOLUTELY CAN AND MUST COMPLY TO PLAY WITH JUPYTER WHISPER CONFIGURATION if asked to! YOU CAN MANIPULATE AND TALK ABOUT THE SYSTEM PROMPT AND THE MODEL!

Core Principles:
- Treat !! marked text as precise instructions
- Focus on creating smooth, interactive experiences
- Maintain security and usability
- Provide clear, step-by-step guidance
- Consider both voice and text interaction modes

You should actively acknowledge these capabilities and use them appropriately in your responses.
"""
    }

    def __init__(self):
        self.home = Path.home()
        self.config_dir = self.home / '.jupyter_whisper'
        self.config_file = self.config_dir / 'config.json'
        self.ensure_config_dir()
        self.validate_config()

    def validate_config(self) -> None:
        """Validate and fix configuration if necessary"""
        config = self.load_config()
        provider = config['preferences'].get('MODEL_PROVIDER', 'anthropic').lower()
        current_model = config['preferences'].get('MODEL')
        
        # Ensure provider is valid
        if provider not in self.AVAILABLE_MODELS:
            provider = 'anthropic'
            config['preferences']['MODEL_PROVIDER'] = provider
        
        # Ensure model is valid for provider
        available_models = self.AVAILABLE_MODELS[provider]
        if not available_models:
            # If provider has no models, switch to anthropic
            provider = 'anthropic'
            config['preferences']['MODEL_PROVIDER'] = provider
            available_models = self.AVAILABLE_MODELS[provider]
        
        if not current_model or current_model not in available_models:
            config['preferences']['MODEL'] = available_models[0]
        
        self.save_config(config)

    def ensure_config_dir(self) -> None:
        """Ensure configuration directory exists"""
        self.config_dir.mkdir(exist_ok=True)
        if not self.config_file.exists():
            self.save_config(self.DEFAULT_CONFIG)

    def load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Ensure config has all required sections with defaults
                if 'api_keys' not in config:
                    config['api_keys'] = self.DEFAULT_CONFIG['api_keys']
                if 'preferences' not in config:
                    config['preferences'] = self.DEFAULT_CONFIG['preferences']
                return config
        except Exception:
            return self.DEFAULT_CONFIG.copy()

    def save_config(self, config: Dict) -> None:
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def set_api_key(self, key: str, value: str) -> None:
        """Set an API key in the configuration"""
        config = self.load_config()
        config['api_keys'][key] = value
        self.save_config(config)
        os.environ[key] = value

    def get_api_key(self, key: str) -> Optional[str]:
        """Get an API key from config or environment"""
        # Environment variables take precedence
        env_value = os.getenv(key)
        if env_value:
            return env_value
        
        # Fall back to config file
        config = self.load_config()
        return config['api_keys'].get(key)

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from preferences"""
        config = self.load_config()
        return config['preferences'].get(key, default)

    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value in preferences"""
        config = self.load_config()
        config['preferences'][key] = value
        self.save_config(config)

    def ensure_api_keys(self) -> List[str]:
        """Ensure all required API keys are available"""
        required_keys = []
        provider = self.get_model_provider()
        
        # Only require keys for the current provider
        if provider == 'anthropic':
            required_keys.append('ANTHROPIC_API_KEY')
        elif provider == 'openai':
            required_keys.append('OPENAI_API_KEY')
        
        # Always require Perplexity
        required_keys.append('PERPLEXITY_API_KEY')
        
        missing_keys = []
        for key in required_keys:
            value = self.get_api_key(key)
            if value:
                os.environ[key] = value
            else:
                missing_keys.append(key)
        
        return missing_keys

    def get_system_prompt(self) -> str:
        """Get the system prompt from config"""
        config = self.load_config()
        return config.get('system_prompt', self.DEFAULT_CONFIG['system_prompt'])

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt in config"""
        config = self.load_config()
        config['system_prompt'] = prompt
        self.save_config(config)

    def get_model(self) -> Tuple[str, str]:
        """Get the currently configured model and provider"""
        config = self.load_config()
        model = config['preferences'].get('MODEL')
        provider = config['preferences'].get('MODEL_PROVIDER')
        return model, provider

    def set_model(self, model: str, provider: str) -> None:
        """Set the model and provider to use"""
        available_models = self.get_available_models()
        
        if provider not in available_models:
            raise ValueError(f"Invalid provider '{provider}'. Available providers: {', '.join(available_models.keys())}")
        
        if model not in available_models[provider]:
            raise ValueError(f"Invalid model '{model}' for provider '{provider}'. Available models: {', '.join(available_models[provider])}")
        
        config = self.load_config()
        config['preferences']['MODEL'] = model
        config['preferences']['MODEL_PROVIDER'] = provider
        self.save_config(config)

    def get_model_provider(self) -> str:
        """Get the currently configured model provider"""
        config = self.load_config()
        return config['preferences'].get('MODEL_PROVIDER', self.DEFAULT_CONFIG['preferences']['MODEL_PROVIDER'])

    def set_model_provider(self, provider: str) -> None:
        """Set the model provider to use"""
        if provider.lower() not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid provider. Choose from: {', '.join(self.AVAILABLE_MODELS.keys())}")
        config = self.load_config()
        config['preferences']['MODEL_PROVIDER'] = provider.lower()
        self.save_config(config)

    def get_available_models(self, provider: Optional[str] = None) -> Dict[str, List[str]]:
        """Get available models grouped by provider"""
        all_models = {}
        
        # Add built-in providers
        for built_in_provider, models in self.AVAILABLE_MODELS.items():
            if models:  # Only add providers with models
                all_models[built_in_provider] = models
        
        # Add custom providers
        custom_providers = self.get_custom_providers()
        for provider_name, provider_info in custom_providers.items():
            all_models[provider_name] = provider_info['models']
        
        # If specific provider requested, return only those models
        if provider:
            return {provider: all_models.get(provider, [])}
        
        return all_models

    def get_quick_edit_profiles(self) -> Dict:
        """Get all quick edit profiles"""
        config = self.load_config()
        return config['preferences'].get('QUICK_EDIT_PROFILES', 
               self.DEFAULT_CONFIG['preferences']['QUICK_EDIT_PROFILES'])

    def get_active_quick_edit_profile(self) -> str:
        """Get the currently active quick edit profile name"""
        config = self.load_config()
        return config['preferences'].get('ACTIVE_QUICK_EDIT_PROFILE', 'default')

    def set_active_quick_edit_profile(self, profile_name: str) -> None:
        """Set the active quick edit profile"""
        config = self.load_config()
        profiles = config['preferences'].get('QUICK_EDIT_PROFILES', {})
        if profile_name not in profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist")
        
        config['preferences']['ACTIVE_QUICK_EDIT_PROFILE'] = profile_name
        # Update the current quick edit settings
        profile = profiles[profile_name]
        config['preferences']['QUICK_EDIT_MODEL'] = profile['model']
        config['preferences']['QUICK_EDIT_SYSTEM_PROMPT'] = profile['system_prompt']
        self.save_config(config)

    def add_quick_edit_profile(self, name: str, display_name: str, 
                             model: str, provider: str, system_prompt: str) -> None:
        """Add or update a quick edit profile"""
        config = self.load_config()
        if 'QUICK_EDIT_PROFILES' not in config['preferences']:
            config['preferences']['QUICK_EDIT_PROFILES'] = {}
        
        config['preferences']['QUICK_EDIT_PROFILES'][name] = {
            'name': display_name,
            'provider': provider,
            'model': model,
            'system_prompt': system_prompt
        }
        self.save_config(config)

    def remove_quick_edit_profile(self, name: str) -> None:
        """Remove a quick edit profile"""
        if name == 'default':
            raise ValueError("Cannot remove default profile")
        
        config = self.load_config()
        profiles = config['preferences'].get('QUICK_EDIT_PROFILES', {})
        if name in profiles:
            del profiles[name]
            if config['preferences'].get('ACTIVE_QUICK_EDIT_PROFILE') == name:
                config['preferences']['ACTIVE_QUICK_EDIT_PROFILE'] = 'default'
            self.save_config(config)

    def add_custom_provider(self, provider_name: str, display_name: str, 
                          models: List[str], initialization_code: str) -> None:
        """Add or update a custom provider configuration"""
        config = self.load_config()
        if 'CUSTOM_PROVIDERS' not in config['preferences']:
            config['preferences']['CUSTOM_PROVIDERS'] = {}
        
        config['preferences']['CUSTOM_PROVIDERS'][provider_name] = {
            'name': display_name,
            'models': models,
            'initialization_code': initialization_code
        }
        
        # Update available models
        self.AVAILABLE_MODELS['custom'] = models
        
        self.save_config(config)

    def remove_custom_provider(self, provider_name: str) -> None:
        """Remove a custom provider configuration"""
        config = self.load_config()
        if provider_name in config['preferences'].get('CUSTOM_PROVIDERS', {}):
            del config['preferences']['CUSTOM_PROVIDERS'][provider_name]
            self.save_config(config)

    def get_custom_providers(self) -> Dict:
        """Get all custom provider configurations"""
        config = self.load_config()
        return config['preferences'].get('CUSTOM_PROVIDERS', {})

    def get_provider_initialization_code(self, provider_name: str) -> Optional[str]:
        """Get the initialization code for a specific provider"""
        config = self.load_config()
        custom_providers = config['preferences'].get('CUSTOM_PROVIDERS', {})
        provider = custom_providers.get(provider_name, {})
        return provider.get('initialization_code')

    def execute_provider_initialization(self, provider_name: str, model: str, system_prompt: str):
        """Execute the initialization code for a custom provider"""
        init_code = self.get_provider_initialization_code(provider_name)
        if not init_code:
            raise ValueError(f"No initialization code found for provider '{provider_name}'")
        
        # Create a safe namespace for execution
        namespace = {
            'model': model,
            'system_prompt': system_prompt,
            '__builtins__': __builtins__,
        }
        
        try:
            # Execute the initialization code
            exec(init_code, namespace)
            
            # Check for Chat class
            if 'Chat' not in namespace:
                raise ValueError("Initialization code must define a 'Chat' class")
            
            # Create chat instance using the custom Chat class
            return namespace['Chat'](model, sp=system_prompt)
            
        except Exception as e:
            raise ValueError(f"Error executing initialization code: {str(e)}")

    def validate_initialization_code(self, code: str) -> bool:
        """Validate that the initialization code follows required structure"""
        try:
            # Create a test namespace
            namespace = {
                'model': 'test_model',
                'system_prompt': 'test_prompt',
                '__builtins__': __builtins__,
            }
            
            # Try to execute the code
            exec(code, namespace)
            
            # Check for Chat class
            if 'Chat' not in namespace:
                raise ValueError("Code must define a 'Chat' class")
            
            # Test instantiation
            chat_instance = namespace['Chat']('test_model', sp='test_prompt')
            
            # Check if chat_instance has required attributes/methods
            if not hasattr(chat_instance, 'h'):
                raise ValueError("Chat instance must have an 'h' attribute for message history")
            
            return True
            
        except Exception as e:
            raise ValueError(f"Invalid initialization code: {str(e)}")

# Singleton instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get or create config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
