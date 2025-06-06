import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable, Union, Generator  # Added Union and Generator
import threading
from openai import OpenAI

class ConfigManager:
    DEFAULT_CONFIG = {
        'api_keys': {},
        'preferences': {
            'SKIP_SETUP_POPUP': False,
            'MODEL_PROVIDER': 'grok',  # Set default to a custom provider
            'MODEL': 'grok-beta-vision', 
            'ACTIVE_QUICK_EDIT_PROFILE': 'default',
            'MAX_CELL_OUTPUT_LENGTH': 2000,
            'CELL_HISTORY_CONFIG': {
                'KEEP_FIRST_N': 2,      # Keep first N cell outputs
                'KEEP_RECENT_M': 4,    # Keep M most recent outputs
            },
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
                    'provider': 'anthropic',
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
                    'provider': 'anthropic',
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
                        "grok-vision-beta"
                    ],
                    "initialization_code": """
import os
from typing import Optional, List, Generator, Union
from openai import OpenAI
from jupyter_whisper.config import get_config_manager


class Chat:
    def __init__(self, model: Optional[str] = None, sp: str = '', history: Optional[List[dict]] = None):
        self.model = model or "grok-vision-beta"
        self.sp = sp
        self.api_key = self.get_api_key()
        self.client = self.get_client()
        self.h = history if history is not None else []

    def get_api_key(self):
        config = get_config_manager()
        api_key = config.get_api_key('GROK_API_KEY')
        if not api_key:
            raise ValueError("GROK_API_KEY not found in configuration")
        return api_key

    def get_client(self):
        return OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )

    def update_model(self, model_info: dict):
        self.model = model_info.get('model', self.model)

    def update_api_key(self, api_keys: dict):
        self.api_key = self.get_api_key()
        self.client = self.get_client()

    def __call__(self, 
                 message: str, 
                 max_tokens: int = 4096, 
                 stream: bool = True,
                 temperature: float = 0,
                 images: Optional[List[dict]] = None) -> Union[str, Generator[str, None, str]]:
        try:
            # Handle message content based on whether images are present
            if images:
                images.append(  {
                    "type": "text",
                    "text": message
                })
                content = images
            else:
                content = message
            
            # Add user message to history
            self.h.append({"role": "user", "content": content})
            
            # Get response from x.ai
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.sp},
                    *self.h
                ],
                max_tokens=max_tokens,
                stream=stream,
                temperature=temperature
            )
            
            if stream:
                full_response = ""
                try:
                    for chunk in response:
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                            text = chunk.choices[0].delta.content
                            full_response += text
                            yield text
                except Exception as e:
                    print(f"Error during streaming: {e}")
                    raise
                finally:
                    if full_response:
                        self.h.append({"role": "assistant", "content": full_response})
                    print()
                return full_response
            else:
                assistant_message = response.choices[0].message.content
                self.h.append({"role": "assistant", "content": assistant_message})
                return assistant_message 
        except Exception as e:
            print("Error in chat: {}".format(e))
            raise
"""
                },
                "anthropic": {
                    "name": "anthropic",
                    "models": [
                        "claude-3-5-sonnet-20241022"
                    ],
                    "initialization_code": """
import os
from typing import Optional, List, Generator, Union
from anthropic import Anthropic
from jupyter_whisper.config import get_config_manager
import re

class Chat:
    def __init__(self, model: Optional[str] = None, sp: str = '', history: Optional[List[dict]] = None):
        self.model = model or "claude-3-5-sonnet-20241022"
        self.sp = sp
        self.api_key = self.get_api_key()
        self.client = self.get_client()
        self.h = history if history is not None else []

    def get_api_key(self):
        config = get_config_manager()
        api_key = config.get_api_key('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in configuration")
        return api_key

    def get_client(self):
        return Anthropic(api_key=self.api_key)

    def update_model(self, model_info: dict):
        self.model = model_info.get('model', self.model)

    def update_api_key(self, api_keys: dict):
        self.api_key = self.get_api_key()
        self.client = self.get_client()

    def _convert_image_format(self, image_dict):
        if image_dict.get('type') == 'image_url':
            url = image_dict['image_url']['url']
            # Extract mime type and base64 data from data URL
            match = re.match(r'data:(.+);base64,(.+)', url)
            if match:
                media_type, data = match.groups()
                return {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": data,
                    }
                }
        return image_dict

    def __call__(self,
                message: str,
                max_tokens: int = 4096,
                stream: bool = True,
                temperature: float = 0,
                images: Optional[List[dict]] = None) -> Union[str, Generator[str, None, str]]:
        try:
            # Handle message content based on whether images are present
            if images:
                content = [
                    *(self._convert_image_format(img) for img in images),
                    {
                        "type": "text",
                        "text": message
                    }
                ]
            else:
                content = [{"type": "text", "text": message}]

            # Add user message to history
            self.h.append({"role": "user", "content": content})

            # Create messages list from history (excluding system prompt)
            messages = self.h.copy()

            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
                "stream": stream
            }

            # Add system parameter if system prompt exists
            if self.sp:
                api_params["system"] = self.sp

            # Get response from Anthropic
            response = self.client.messages.create(**api_params)

            if stream:
                full_response = ""
                try:
                    content_block_text = ""
                    for chunk in response:
                        if chunk.type == 'content_block_delta' and hasattr(chunk.delta, 'text'):
                            content_block_text += chunk.delta.text
                            yield chunk.delta.text
                        elif chunk.type == 'message_stop':
                            if content_block_text:
                                full_response = content_block_text
                except Exception as e:
                    print(f"Error during streaming: {e}")
                    raise
                finally:
                    if full_response:
                        self.h.append({"role": "assistant", "content": [{"type": "text", "text": full_response}]})
                    print()
                return full_response
            else:
                assistant_message = response.content[0].text
                self.h.append({"role": "assistant", "content": [{"type": "text", "text": assistant_message}]})
                return assistant_message

        except Exception as e:
            print("Error in chat: {}".format(e))
            raise
"""
                },
                "GEMINI": {
                    "name": "GEMINI",
                    "models": [
                        "gemini-exp-1206",
                        "gemini-1.5-pro-002",
                        "gemini-1.5-flash",
                        "gemini-1.5-flash-8b",
                        "gemini-exp-1121"
                    ],
                    "initialization_code": """
import os
from typing import Optional, List, Generator, Union
from openai import OpenAI
from jupyter_whisper.config import get_config_manager


class Chat:
    def __init__(self, model: Optional[str] = None, sp: str = '', history: Optional[List[dict]] = None):
        self.model = model or "gemini-1.5-pro-002"
        self.sp = sp
        self.api_key = self.get_api_key()
        self.client = self.get_client()
        self.h = history if history is not None else []

    def get_api_key(self):
        config = get_config_manager()
        api_key = config.get_api_key('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")
        return api_key

    def get_client(self):
        return OpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    def update_model(self, model_info: dict):
        self.model = model_info.get('model', self.model)

    def update_api_key(self, api_keys: dict):
        self.api_key = self.get_api_key()
        self.client = self.get_client()

    def __call__(self, 
                 message: str, 
                 max_tokens: int = 4096, 
                 stream: bool = True,
                 temperature: float = 0,
                 images: Optional[List[dict]] = None) -> Union[str, Generator[str, None, str]]:
        try:
            # Handle message content based on whether images are present
            if images:
                images.append(  {
                    "type": "text",
                    "text": message
                })
                content = images
            else:
                content = message
            
            # Add user message to history
            self.h.append({"role": "user", "content": content})
            
            # Get response from x.ai
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.sp},
                    *self.h
                ],
                max_tokens=max_tokens,
                stream=stream,
                temperature=temperature
            )
            
            if stream:
                full_response = ""
                try:
                    for chunk in response:
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                            text = chunk.choices[0].delta.content
                            full_response += text
                            yield text
                except Exception as e:
                    print(f"Error during streaming: {e}")
                    raise
                finally:
                    if full_response:
                        self.h.append({"role": "assistant", "content": full_response})
                    print()
                return full_response
            else:
                assistant_message = response.choices[0].message.content
                self.h.append({"role": "assistant", "content": assistant_message})
                return assistant_message 
        except Exception as e:
            print("Error in chat: {}".format(e))
            raise
"""
                },
                "gpt4o-latest": {
                    "name": "gpt4o-latest",
                    "models": [
                        "gpt-4o",
                        "gpt-4o-mini"
                    ],
                    "initialization_code": """
import os
from typing import Optional, List, Generator, Union
from openai import OpenAI
from jupyter_whisper.config import get_config_manager


class Chat:
    def __init__(self, model: Optional[str] = None, sp: str = '', history: Optional[List[dict]] = None):
        self.model = model or "gpt-4o"
        self.sp = sp
        self.api_key = self.get_api_key()
        self.client = self.get_client()
        self.h = history if history is not None else []

    def get_api_key(self):
        config = get_config_manager()
        api_key = config.get_api_key('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in configuration")
        return api_key

    def get_client(self):
        return OpenAI(
            api_key=self.api_key
        )

    def update_model(self, model_info: dict):
        self.model = model_info.get('model', self.model)

    def update_api_key(self, api_keys: dict):
        self.api_key = self.get_api_key()
        self.client = self.get_client()

    def __call__(self, 
                 message: str, 
                 max_tokens: int = 4096, 
                 stream: bool = True,
                 temperature: float = 0,
                 images: Optional[List[dict]] = None) -> Union[str, Generator[str, None, str]]:
        try:
            # Handle message content based on whether images are present
            if images:
                images.append(  {
                    "type": "text",
                    "text": message
                })
                content = images
            else:
                content = message
            
            # Add user message to history
            self.h.append({"role": "user", "content": content})
            
            # Get response from x.ai
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.sp},
                    *self.h
                ],
                max_tokens=max_tokens,
                stream=stream,
                temperature=temperature
            )
            
            if stream:
                full_response = ""
                try:
                    for chunk in response:
                        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                            text = chunk.choices[0].delta.content
                            full_response += text
                            yield text
                except Exception as e:
                    print(f"Error during streaming: {e}")
                    raise
                finally:
                    if full_response:
                        self.h.append({"role": "assistant", "content": full_response})
                    print()
                return full_response
            else:
                assistant_message = response.choices[0].message.content
                self.h.append({"role": "assistant", "content": assistant_message})
                return assistant_message 
        except Exception as e:
            print("Error in chat: {}".format(e))
            raise
"""
                }
            }
        },
        'system_prompt': """
You are a general and helpful assistant.

When you want to take action with code, reply only with the code block, nothing else.
Using the code block you can run shell commands, python code, etc.

You can run javascript code using code block. This javascript
will run in the browser in the dev console.

Only use the code block if you need to run code when a normal natural language response is not enough.

1. Model and Provider Management:
   - Multiple AI providers supported through custom provider system
   - Current providers include: anthropic, grok, gemini, gpt4o-latest, ollama
   - Configure providers and models using ConfigManager:
   ```python
   from jupyter_whisper.config import get_config_manager
   config = get_config_manager()
   
   # List available models for a provider
   models = config.get_available_models('anthropic')
   
   # Set model and provider
   config.set_model('claude-3-5-sonnet-20241022', provider='anthropic')
   
   # Get current model info
   model, provider = config.get_model()
   ```

2. Quick Edit Profiles:
   - Predefined profiles for different editing tasks
   - Manage profiles through ConfigManager:
   ```python
   # Get all profiles
   profiles = config.get_quick_edit_profiles()
   
   # Get active profile
   active = config.get_active_quick_edit_profile()
   
   # Set active profile
   config.set_active_quick_edit_profile('code_review')
   
   # Add new profile
   config.add_quick_edit_profile(
       name='custom_editor',
       display_name='My Custom Editor',
       provider='anthropic',
       model='claude-3-5-sonnet-20241022',
       system_prompt='Your custom prompt here'
   )
   ```

3. API Key Management:
   - Securely store and manage API keys:
   ```python
   # Set API key
   config.set_api_key('ANTHROPIC_API_KEY', 'your-key-here')
   
   # Get API key
   key = config.get_api_key('ANTHROPIC_API_KEY')
   ```

4. Voice Interaction Features:
   - Text between !! marks indicates voice input
   - Voice Commands:
     * Ctrl+Shift+Z: Toggle voice recording
     * Ctrl+Shift+A: Process selected text
   - All voice input appears between !! marks

5. Technical Environment:
   - Running in JupyterLab 4.0+ environment
   - FastAPI server running on port 5000
   - Real-time streaming responses capability

6. Notebook Management:
   - Create notebooks in '~/whispers' folder
   - Magic Commands for chat management:
     * %%user [index]:set - Set/replace user message
     * %%assistant [index]:set - Set/replace assistant message
     * %%assistant [index]:add - Append to assistant message

7. HTML/JavaScript Guidelines:
   - Use unique, static IDs for elements
   - Wrap JavaScript in IIFEs
   - Use var instead of const/let
   - Avoid template literals and complex ES6+ features
   - Use HTML elements for debugging instead of console.log

8. Configuration Management:
   - Control which cell outputs are kept in history:
   ```python
   config = get_config_manager()
   
   # Configure history retention
   config.set_config_value('CELL_HISTORY_CONFIG', {
       'KEEP_FIRST_N': 5,    # Keep first 5 outputs
       'KEEP_RECENT_M': 15   # Keep 15 most recent outputs
   })
   ```
   - Default keeps first 5 and most recent 15 outputs
   - First N outputs are preserved to maintain context
   - Most recent M outputs track current work
   - Total history size = N + M outputs
   - Automatically manages history size while preserving context

9. Search Integration:
   ```python
   from jupyter_whisper import search_online
   
   style = "Be precise and concise"
   question = "Your search query here"
   search_online(style, question)
   ```

10. HTML and JavaScript in Jupyter Notebooks:
   a) Basic Structure:
   ```html
   <canvas id="uniqueID" width="300" height="200" style="border:2px solid #4CAF50; background: #000000;"></canvas>
   <div id="debugID" style="color: white; font-family: monospace;"></div>
   <script>
   (function() {  // Use IIFE to avoid global scope
       var canvas = document.getElementById('uniqueID');
       var ctx = canvas.getContext('2d');
       var debug = document.getElementById('debugID');
       // Your code here
   })();
   </script>
   ```

   b) Best Practices:
   - Always use unique, static IDs for elements
   - Use `var` instead of `const/let` for variable declarations
   - Wrap JavaScript code in IIFE to avoid global scope pollution
   - Use simple string concatenation instead of template literals
   - Display debug information in HTML elements instead of console.log

   c) What Works:
   - Basic DOM manipulation
   - Canvas operations
   - Simple animations with requestAnimationFrame
   - Basic mathematical operations
   - String concatenation
   - RGB color values with simple arithmetic

   d) What to Avoid:
   - Template literals (using backticks and ${})
   - Dynamic ID generation
   - Console.log debugging
   - Complex ES6+ features
   - Reusing IDs across cells
   - Global scope variables

   e) Debugging Example:
   ```html
   <div id="debug_123"></div>
   <script>
   (function() {
       var debug = document.getElementById('debug_123');
       debug.innerHTML = 'Debug info: ' + someValue;
   })();
   </script>
   ```

   f) Animation Example:
   ```html
   <canvas id="canvas_123" width="300" height="200" style="border:2px solid #4CAF50; background: #000000;"></canvas>
   <div id="debug_123"></div>
   <script>
   (function() {
       var canvas = document.getElementById('canvas_123');
       var ctx = canvas.getContext('2d');
       var debug = document.getElementById('debug_123');
       
       var x = 0;
       var y = 100;
       
       function draw() {
           ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
           ctx.fillRect(0, 0, canvas.width, canvas.height);
           
           ctx.beginPath();
           ctx.arc(x, y, 10, 0, Math.PI * 2);
           ctx.fillStyle = 'rgb(255, 0, 0)';
           ctx.fill();
           
           x = (x + 2) % canvas.width;
           
           debug.innerHTML = 'Position: x=' + Math.round(x);
           
           requestAnimationFrame(draw);
       }
       
       draw();
   })();
   </script>
   ```
11. Data Analytics:

If asked to do data analysis and the library are not specified, use DuckDB in python.

DuckDB is a fast, in-memory SQL database that can handle large data sets and is easy to use.
# DuckDB SQL Dialect Cheat Sheet

## Overview

- Based on PostgreSQL dialect.
- Aims for close PostgreSQL compatibility but with some differences (e.g., order preservation by default).

## Indexing

- **1-based indexing** for strings, lists, etc.
- **0-based indexing** for JSON objects.

**Example (1-based):**

```sql
SELECT list[1] AS element
FROM (SELECT ['first', 'second', 'third'] AS list);
-- Output: 'first'
```

**Example (0-based):**

```sql
SELECT json[1] AS element
FROM (SELECT '["first", "second", "third"]'::JSON AS json);
-- Output: "second"
```

## Friendly SQL Features

### Clauses

- **`CREATE OR REPLACE TABLE`**: Avoids `DROP TABLE IF EXISTS`.
- **`CREATE TABLE ... AS SELECT (CTAS)`**: Creates a table from a query's output.
- **`INSERT INTO ... BY NAME`**: Inserts using column names instead of positions.
- **`INSERT OR IGNORE INTO ...`**: Inserts rows, ignoring conflicts with `UNIQUE` or `PRIMARY KEY` constraints.
- **`INSERT OR REPLACE INTO ...`**: Inserts rows, replacing existing rows on conflict.
- **`DESCRIBE`**: Summarizes table or query schema.
- **`SUMMARIZE`**: Provides summary statistics for a table or query.
- **`FROM`-first syntax with optional `SELECT`**: `FROM tbl` is equivalent to `SELECT * FROM tbl`.
- **`GROUP BY ALL`**: Infers group-by columns from the `SELECT` clause.
- **`ORDER BY ALL`**: Orders by all columns.
- **`SELECT * EXCLUDE`**: Excludes specific columns from `*`.
- **`SELECT * REPLACE`**: Replaces specific columns in `*` with different expressions.
- **`UNION BY NAME`**: Performs `UNION` based on column names.
- **`PIVOT`**: Transforms long tables to wide tables.
- **`UNPIVOT`**: Transforms wide tables to long tables.
- **`SET VARIABLE`**: Defines SQL-level variables.
- **`RESET VARIABLE`**: Resets SQL-level variables.

### Query Features

- Column aliases in `WHERE`, `GROUP BY`, and `HAVING` (but not in `JOIN`'s `ON` clause).
- **`COLUMNS()` expression**:
    - Executes the same expression on multiple columns.
    - Supports regular expressions, `EXCLUDE`, `REPLACE`, and lambda functions.
- Reusable column aliases (e.g., `SELECT i + 1 AS j, j + 2 AS k FROM range(0, 3) t(i)`).
- Advanced aggregation:
    - `FILTER` clause.
    - `GROUPING SETS`, `GROUP BY CUBE`, `GROUP BY ROLLUP`.
    - `count()` shorthand for `count(*)`.

### Literals and Identifiers

- Case-insensitive but preserves the case of entities in the catalog.
- Deduplicates identifiers.
- Underscores as digit separators in numeric literals (e.g., `1_000_000`).

### Data Types

- `MAP` data type.
- `UNION` data type.

### Data Import

- Auto-detects headers and schema of CSV files.
- Directly queries CSV and Parquet files.
- Loads from files using `FROM 'my.csv'`, `FROM 'my.parquet'`, etc.
- Filename expansion (globbing) (e.g., `FROM 'my-data/part-*.parquet'`).

### Functions and Expressions

- Dot operator for function chaining (e.g., `SELECT ('hello').upper()`).
- String formatters: `format()` (with `fmt` syntax) and `printf()`.
- List comprehensions.
- List and string slicing.
- `STRUCT.*` notation.
- Simple `LIST` and `STRUCT` creation.

### Join Types

- `ASOF` joins.
- `LATERAL` joins.
- `POSITIONAL` joins.

### Trailing Commas

- Allowed when listing entities and constructing `LIST` items.

**Example:**

```sql
SELECT
    42 AS x,
    ['a', 'b', 'c',] AS y,
    'hello world' AS z,
;
```

### "Top-N in Group" Queries

- Efficiently get the top N rows in a group using:
    - `max(arg, n)`
    - `min(arg, n)`
    - `arg_max(arg, val, n)`
    - `arg_min(arg, val, n)`
    - `max_by(arg, val, n)`
    - `min_by(arg, val, n)`

**Example:**

```sql
-- Get top 3 values in each group
SELECT max(val, 3) FROM t1 GROUP BY grp;
```

## Keywords and Identifiers

### Identifiers

- **Unquoted identifiers:**
    - Must not be a reserved keyword.
    - Must not start with a number or special character.
    - Cannot contain whitespaces.
- **Quoted identifiers (using double quotes):**
    - Can use any keyword, whitespace, or special character.
    - Double quotes can be escaped by repeating them (e.g., `"IDENTIFIER ""X""`").

### Deduplicating Identifiers

- Automatically renames duplicate identifiers:
    - First instance: `⟨name⟩`
    - Subsequent instances: `⟨name⟩_⟨count⟩` (where `⟨count⟩` starts at 1).

### Database Names

- Follow identifier rules.
- Avoid internal schema names `system` and `temp`.
- Use aliases if necessary (e.g., `ATTACH 'temp.db' AS temp2;`).

### Case Sensitivity

- **Keywords and function names:** Case-insensitive.
- **Identifiers:** Case-insensitive (even when quoted), but preserves the original case.
- **Conflicts:** If the same identifier is spelled with different cases, one is selected randomly.
- **Disabling case preservation:** `SET preserve_identifier_case = false;` (turns all identifiers to lowercase).

## Order Preservation

- DuckDB preserves row order for many operations (like data frame libraries).

### Clauses Preserving Order

- `COPY`
- `FROM` (with a single table)
- `LIMIT`
- `OFFSET`
- `SELECT`
- `UNION ALL`
- `WHERE`
- Window functions with an empty `OVER` clause

### Operations NOT Preserving Order

- `FROM` (with multiple tables/subqueries)
- `JOIN`
- `UNION`
- `USING SAMPLE`
- `GROUP BY`
- `ORDER BY`

### Insertion Order

- Preserved by default for:
    - CSV reader (`read_csv`)
    - JSON reader (`read_json`)
    - Parquet reader (`read_parquet`)
- Controlled by `preserve_insertion_order` setting (default: `true`).

## PostgreSQL Compatibility

### Floating-Point Arithmetic

- DuckDB follows IEEE 754 for division by zero and infinity operations.
- PostgreSQL returns an error for division by zero but aligns with IEEE 754 for infinity.

### Division on Integers

- PostgreSQL: Integer division.
- DuckDB: Float division (use `//` for integer division).

### `UNION` of Boolean and Integer

- PostgreSQL: Fails.
- DuckDB: Enforced cast (e.g., `true` becomes `1`).

### Case Sensitivity for Quoted Identifiers

- PostgreSQL: Quoted identifiers are case-sensitive.
- DuckDB: All identifiers are case-insensitive, but case is preserved.

### Double Equality Sign (`==`)

- DuckDB: Supports both `=` and `==` for equality comparison.
- PostgreSQL: Only supports `=`.

### Vacuuming Tables

- PostgreSQL: `VACUUM` garbage collects and analyzes tables.
- DuckDB: `VACUUM` only rebuilds statistics.

### Functions

- **`to_date`**: Use `strptime` in DuckDB.
- **`current_date`, `current_time`, `current_timestamp`**:
    - DuckDB: Returns UTC date/time.
    - PostgreSQL: Returns date/time in the configured local timezone.
    - DuckDB also has `current_localtime()`, `current_localtimestamp()`.

### Type Name Resolution in Schema

- DuckDB resolves type names in the schema where a table is created.
- PostgreSQL may return an error if the type is not found in the default search path.

In python, use duckdb-engine to connect to DuckDB like this:

```python
import duckdb
con = duckdb.connect(':memory:')
con.sql('CREATE TABLE tbl AS SELECT 1 AS col')
# for a pandas dataframe
df = con.sql('SELECT * FROM tbl').df()
# for a polars dataframe
df = con.sql('SELECT * FROM tbl').pl()
# for a list of dictionaries
df = con.sql('SELECT * FROM tbl').to_df()

you can also do things like this:
def get_list_from_duckdb(query, column_name):
  try:
    con = duckdb.connect()  # In-memory database by default
    result = con.execute(query).fetchall()
    con.close()

    if result:
      return [row[result[0].index(column_name)] for row in result]
    else:
      return []  # Return an empty list if the query returns no rows
  except Exception as e:
    print(f"Error executing query: {e}")
    return None
```

Core Guidelines:
- Treat !! marked text as precise voice instructions
- Provide clear, step-by-step guidance
- Focus on creating interactive experiences
- Maintain security and proper error handling
- Consider both voice and text interaction modes

Remember to validate configurations and handle errors appropriately when making changes.
"""
    }

    _ui_refresh_callbacks: Dict[str, List[Callable]] = {
        'model': [],
        'provider': [],
        'system_prompt': [],
        'quick_edit': [],
        'custom_providers': []
    }

    # Add a lock for thread safety
    _config_lock = threading.Lock()

    def __init__(self):
        self.home = Path.home()
        self.config_dir = self.home / '.jupyter_whisper'
        self.config_file = self.config_dir / 'config.json'
        self._config_cache = None  # Add config cache
        self._custom_providers_cache = None  # Add providers cache
        self.ensure_config_dir()
        # Only validate config when actually needed
        self._change_callbacks = {}
        self._ui_refresh_callbacks = {
            'model': [],
            'provider': [],
            'system_prompt': [],
            'quick_edit': [],
            'custom_providers': []
        }

    def validate_config(self) -> None:
        """Lazy validation of configuration"""
        # Only validate when actually accessing the config
        pass

    def ensure_config_dir(self) -> None:
        """Ensure configuration directory exists"""
        self.config_dir.mkdir(exist_ok=True)
        if not self.config_file.exists():
            self.save_config(self.DEFAULT_CONFIG)

    def load_config(self) -> Dict:
        """Load configuration from file with caching"""
        if self._config_cache is None:
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Only set defaults if missing
                    if 'api_keys' not in config:
                        config['api_keys'] = self.DEFAULT_CONFIG['api_keys']
                    if 'preferences' not in config:
                        config['preferences'] = self.DEFAULT_CONFIG['preferences']
                    self._config_cache = config
            except Exception:
                self._config_cache = self.DEFAULT_CONFIG.copy()
        return self._config_cache

    def save_config(self, config: Dict) -> None:
        """Save configuration to file and update cache"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
        self._config_cache = config  # Update cache

    def set_api_key(self, key: str, value: str) -> None:
        """Set an API key in the configuration and trigger server restart if needed"""
        with self._config_lock:
            config = self.load_config()
            config['api_keys'][key] = value
            self.save_config(config)
            os.environ[key] = value
            
            # Notify that API keys have changed
            self.notify_change('api_keys', config['api_keys'])
            
            # Trigger server restart if running
            self.restart_server_if_running()

    def restart_server_if_running(self) -> None:
        """Restart the FastAPI server if it's running"""
        try:
            import requests
            requests.post('http://localhost:5000/restart')
        except:
            pass  # Server not running or restart endpoint not available

    def get_api_key(self, key: str) -> Optional[str]:
        """Get an API key from config or environment"""
        env_value = os.getenv(key)
        if env_value:
            return env_value
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
        required_keys.append(f'{provider.upper()}_API_KEY')
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
        self.notify_ui_update('system_prompt', prompt)

    def get_model(self) -> Tuple[str, str]:
        """Get the currently configured model and provider"""
        config = self.load_config()
        model = config['preferences'].get('MODEL')
        provider = config['preferences'].get('MODEL_PROVIDER', '')

        custom_providers = self.get_custom_providers()
        if provider not in custom_providers:
            raise ValueError(f"Provider '{provider}' is not defined.")

        provider_models = custom_providers[provider]['models']
        if model not in provider_models:
            model = provider_models[0]
            config['preferences']['MODEL'] = model
            self.save_config(config)

        return model, provider


    def set_model(self, model: str, provider: str = None) -> None:
        """Set the model and provider to use"""
        config = self.load_config()
        if provider is None:
            provider = config['preferences'].get('MODEL_PROVIDER')

        custom_providers = self.get_custom_providers()
        if provider not in custom_providers:
            raise ValueError(f"Provider '{provider}' is not defined.")

        if model not in custom_providers[provider]['models']:
            raise ValueError(f"Invalid model '{model}' for provider '{provider}'.")

        config['preferences']['MODEL'] = model
        config['preferences']['MODEL_PROVIDER'] = provider

        self.save_config(config)
        self.notify_ui_update('model', {'model': model, 'provider': provider})
        self.notify_ui_update('provider', provider)

    def get_model_provider(self) -> str:
        """Get the currently configured model provider"""
        config = self.load_config()
        return config['preferences'].get('MODEL_PROVIDER', '')

    def get_available_models(self, provider: Optional[str] = None) -> Dict[str, List[str]]:
        """Get available models from custom providers only"""
        custom_providers = self.get_custom_providers()
        if provider:
            if provider in custom_providers:
                return {provider: custom_providers[provider]['models']}
            else:
                return {}
        else:
            return {name: p['models'] for name, p in custom_providers.items()}
        
    def get_quick_edit_profiles(self) -> Dict:
        """Get all quick edit profiles."""
        config = self.load_config()
        # Provide an empty dict if 'QUICK_EDIT_PROFILES' doesn't exist
        return config['preferences'].get('QUICK_EDIT_PROFILES', {})

    def get_active_quick_edit_profile(self) -> Optional[str]:
        """Get the currently active quick edit profile name."""
        config = self.load_config()
        # Return None if 'ACTIVE_QUICK_EDIT_PROFILE' is not set
        return config['preferences'].get('ACTIVE_QUICK_EDIT_PROFILE')

    def set_active_quick_edit_profile(self, profile_name: str) -> None:
        """Set the active quick edit profile."""
        config = self.load_config()
        profiles = config['preferences'].get('QUICK_EDIT_PROFILES', {})

        if profile_name not in profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist.")

        config['preferences']['ACTIVE_QUICK_EDIT_PROFILE'] = profile_name
        profile = profiles[profile_name]
        config['preferences']['QUICK_EDIT_MODEL'] = profile['model']
        config['preferences']['QUICK_EDIT_SYSTEM_PROMPT'] = profile['system_prompt']
        self.save_config(config)

    def add_quick_edit_profile(
        self, name: str, display_name: str, provider: str, model: str, system_prompt: str
    ) -> None:
        """Add or update a quick edit profile."""
        config = self.load_config()
        profiles = config['preferences'].get('QUICK_EDIT_PROFILES', {})

        profiles[name] = {
            'name': display_name,
            'provider': provider,
            'model': model,
            'system_prompt': system_prompt,
        }
        config['preferences']['QUICK_EDIT_PROFILES'] = profiles
        self.save_config(config)
        self.notify_ui_update('quick_edit', self.get_quick_edit_profiles())

    def remove_quick_edit_profile(self, name: str) -> None:
        """Remove a quick edit profile."""
        config = self.load_config()
        profiles = config['preferences'].get('QUICK_EDIT_PROFILES', {})

        if name in profiles:
            del profiles[name]
            # Reset to None if the active profile is removed
            if config['preferences'].get('ACTIVE_QUICK_EDIT_PROFILE') == name:
                config['preferences']['ACTIVE_QUICK_EDIT_PROFILE'] = None
            self.save_config(config)
            self.notify_ui_update('quick_edit', self.get_quick_edit_profiles())
        else:
            raise ValueError(f"Profile '{name}' does not exist.")
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
        self.save_config(config)
        self.notify_ui_update('custom_providers', self.get_custom_providers())
        self.notify_ui_update('model', {'model': None, 'provider': provider_name})

    def remove_custom_provider(self, provider_name: str) -> None:
        """Remove a custom provider configuration"""
        config = self.load_config()
        if provider_name in config['preferences'].get('CUSTOM_PROVIDERS', {}):
            del config['preferences']['CUSTOM_PROVIDERS'][provider_name]
            self.save_config(config)
            self.notify_ui_update('custom_providers', self.get_custom_providers())
            self.notify_ui_update('model', {'model': None, 'provider': None})

    def get_custom_providers(self) -> Dict:
        """Get all custom provider configurations with caching"""
        if self._custom_providers_cache is None:
            config = self.load_config()
            self._custom_providers_cache = config['preferences'].get('CUSTOM_PROVIDERS', {})
        return self._custom_providers_cache

    def get_provider_initialization_code(self, provider_name: str) -> Optional[str]:
        """Get the initialization code for a specific provider"""
        config = self.load_config()
        custom_providers = config['preferences'].get('CUSTOM_PROVIDERS', {})
        provider = custom_providers.get(provider_name, {})
        return provider.get('initialization_code')

    def execute_provider_initialization(self, provider_name, model, system_prompt, history=None):
        """Lazy initialization of provider code"""
        # Only initialize when actually needed
        custom_providers = self.get_custom_providers()
        provider_info = custom_providers.get(provider_name)

        if not provider_info:
            raise ValueError(f"Provider '{provider_name}' not found in custom providers.")

        # Check if Chat class already exists in globals
        if 'Chat' in globals():
            Chat = globals()['Chat']
        else:
            # Execute initialization code only if needed
            initialization_code = provider_info['initialization_code']
            exec(initialization_code, globals())
            Chat = globals().get('Chat')

        if not Chat:
            raise ValueError(f"Chat class not defined in initialization code for provider '{provider_name}'.")

        return Chat(model=model, sp=system_prompt, history=history)

    def validate_initialization_code(self, code: str) -> bool:
        """Validate that the initialization code follows required structure"""
        try:
            namespace = {
                'model': 'test_model',
                'system_prompt': 'test_prompt',
                '__builtins__': __builtins__,
            }
            exec(code, namespace)
            if 'Chat' not in namespace:
                raise ValueError("Code must define a 'Chat' class")
            chat_instance = namespace['Chat']('test_model', sp='test_prompt')
            if not hasattr(chat_instance, 'h'):
                raise ValueError("Chat instance must have an 'h' attribute for message history")
            return True
        except Exception as e:
            raise ValueError(f"Invalid initialization code: {str(e)}")

    def register_ui_callback(self, event_type: str, callback: Callable) -> None:
        """Register a UI callback for specific configuration changes"""
        if event_type not in self._ui_refresh_callbacks:
            raise ValueError(f"Invalid event type. Choose from: {', '.join(self._ui_refresh_callbacks.keys())}")
        self._ui_refresh_callbacks[event_type].append(callback)

    def notify_ui_update(self, event_type: str, data: Any = None) -> None:
        """Notify all registered callbacks for a specific event type"""
        for callback in self._ui_refresh_callbacks.get(event_type, []):
            try:
                if data is not None:
                    callback(data)
                else:
                    callback()
            except Exception as e:
                print(f"Error in UI refresh callback: {str(e)}")

    def register_change_callback(self, key: str, callback: Callable) -> None:
        """Register a callback for changes to a specific configuration key."""
        if key not in self._change_callbacks:
            self._change_callbacks[key] = []
        self._change_callbacks[key].append(callback)

    def notify_change(self, key: str, value: Any = None) -> None:
        """Notify all registered callbacks for a specific configuration key change."""
        if key in self._change_callbacks:
            for callback in self._change_callbacks[key]:
                try:
                    callback(value)
                except Exception as e:
                    print(f"Error in callback for {key}: {e}")

    def set_provider(self, provider: str) -> None:
        """Set the provider and notify listeners."""
        with self._config_lock:
            config = self.load_config()
            if provider not in self.get_custom_providers():
                raise ValueError(f"Provider '{provider}' is not defined.")

            config['preferences']['MODEL_PROVIDER'] = provider
            # Also reset the model to default for the new provider
            new_model = self.get_custom_providers()[provider]['models'][0]
            config['preferences']['MODEL'] = new_model
            self.save_config(config)

        # Notify listeners
        self.notify_change('provider', provider)
        self.notify_change('model', new_model)

    def validate_provider_setup(self, provider: str = None) -> Tuple[bool, str]:
        """Validate that a provider is properly configured"""
        if provider is None:
            provider = self.get_model_provider()
        
        try:
            # Check provider exists
            custom_providers = self.get_custom_providers()
            if provider not in custom_providers:
                return False, f"Provider '{provider}' not found in custom providers"
            
            # Check API key exists
            api_key_name = f"{provider.upper()}_API_KEY"
            api_key = self.get_api_key(api_key_name)
            if not api_key:
                return False, f"Missing API key for provider {provider} ({api_key_name})"
            
            # Check initialization code exists
            init_code = self.get_provider_initialization_code(provider)
            if not init_code:
                return False, f"No initialization code found for provider {provider}"
            
            return True, "Provider setup is valid"
        
        except Exception as e:
            return False, f"Error validating provider setup: {str(e)}"




# Singleton instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get or create config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
