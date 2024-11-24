from io import StringIO
import sys
import time
from IPython import get_ipython
import warnings
from io import StringIO
from contextlib import contextmanager
from .config import get_config_manager
from IPython.display import display, HTML, Image, SVG, Markdown, Latex, JSON, Audio, Video, Javascript
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

@dataclass
class CellOutput:
    """
    Represents a single cell's execution output, capturing essential details
    for AI context and user interaction.
    """

    code: str
    stdout: str
    stderr: str
    result: Any
    display_outputs: List[Dict]
    error: Optional[str]
    execution_count: int
    timestamp: datetime

    def to_context_dict(self) -> Dict:
        """Convert to a format suitable for AI context"""
        context = {
            'code': self.code,
            'execution_count': self.execution_count
        }

        # Handle stdout/stderr
        output_parts = []
        if self.stdout:
            stdout = self.stdout.strip()
            if stdout:
                output_parts.append(stdout)
        
        if self.stderr:
            stderr = self.stderr.strip()
            if stderr:
                output_parts.append(f"Stderr:\n{stderr}")

        # Handle result
        if self.result is not None and not isinstance(self.result, type(None)):
            # Skip if it's an assignment
            if not self.code.strip().split('=')[0].strip().isidentifier():
                result_str = str(self.result)
                if result_str not in self.stdout:  # Avoid duplication
                    output_parts.append(result_str)

        # Only add output if we have something
        if output_parts:
            context['output'] = '\n'.join(output_parts)

        # Only add visual outputs if we have them
        if self.display_outputs:
            context['visual_outputs'] = self._format_visual_outputs()

        return context

    def _format_visual_outputs(self) -> List[str]:
        """
        Creates a list of descriptions of visual outputs (images, animations).
        """
        descriptions = []
        for output in self.display_outputs:
            output_type = output.get('type')
            if output.get('is_animated', False):
                desc = f"Animated {output.get('description', output_type)}"
            else:
                desc = f"Static {output_type}"
            descriptions.append(desc)
        return descriptions

class NotebookHistory:
    """
    Manages the history of cell executions, providing context for AI
    while controlling the size of stored data.
    """

    def __init__(self):
        self.outputs: List[CellOutput] = []
        self.config = get_config_manager()
        self._update_history_limits()

    def _update_history_limits(self):
        """Update history limits from config"""
        history_config = self.config.get_config_value('CELL_HISTORY_CONFIG', {
            'KEEP_FIRST_N': 5,
            'KEEP_RECENT_M': 15
        })
        self.keep_first_n = history_config['KEEP_FIRST_N']
        self.keep_recent_m = history_config['KEEP_RECENT_M']

    def add_output(self, output: CellOutput):
        """
        Add output to history, maintaining size limits by keeping
        first N and most recent M outputs.
        """            
        self.outputs.append(output)
        self._update_history_limits()
        
        # If we have more outputs than our total limit
        total_limit = self.keep_first_n + self.keep_recent_m
        if len(self.outputs) > total_limit:
            # Keep first N and last M outputs
            self.outputs = (
                self.outputs[:self.keep_first_n] +  # Keep first N
                self.outputs[-(self.keep_recent_m):]  # Keep last M
            )

    def get_context(self, num_recent: int = None) -> List[Dict]:
        """
        Retrieves cell outputs for AI context.
        If num_recent is specified, returns only that many recent outputs.
        Otherwise, returns all kept outputs (first N + recent M).
        """
        if num_recent is not None:
            return [output.to_context_dict() for output in self.outputs[-num_recent:]]
        return [output.to_context_dict() for output in self.outputs]

class JupyterOutputManager:
    """
    Main interface for managing Jupyter outputs, integrating with IPython
    events to capture and process cell outputs.
    """

    def __init__(self):
        self.capture = OutputCapture()
        self.history = []
        self._register_hooks()

    def _register_hooks(self):
        """
        Registers pre- and post-cell execution hooks with IPython.
        """
        ip = get_ipython()
        if ip:
            ip.events.register('pre_run_cell', self.pre_run_cell)
            ip.events.register('post_run_cell', self.post_run_cell)

    def pre_run_cell(self, info):
        """
        Called before cell execution to reset capture buffers.

        Parameters:
            info (ExecutionInfo): Information about the cell that's about to run.
        """
        try:
            self.capture.start_capture(info.raw_cell)
        except Exception as e:
            print(f"Error in pre_run_cell: {str(e)}")

    def post_run_cell(self, result):
        """Process cell execution results"""
        # Skip recording context calls
        if 'output_manager.history' in result.info.raw_cell:
            self.capture.end_capture()
            return
            
        try:
            captured = self.capture.end_capture()
            
            # NEW: Get the actual result from IPython's Out dictionary
            ip = get_ipython()
            actual_result = None
            if hasattr(ip, 'user_ns') and 'Out' in ip.user_ns:
                actual_result = ip.user_ns['Out'].get(result.execution_count)
            
            output = CellOutput(
                code=result.info.raw_cell,
                stdout=captured['stdout'],
                stderr=captured['stderr'],
                result=actual_result or captured['result'],  # Prefer actual_result if available
                display_outputs=captured['display_outputs'],
                error=str(result.error_in_exec) if result.error_in_exec else None,
                execution_count=result.execution_count,
                timestamp=datetime.now()
            )
            self.history.append(output)
        except Exception as e:
            print(f"Error in post_run_cell: {str(e)}")

class OutputCapture:
    """
    Captures various outputs from Jupyter cell executions, focusing on
    capturing images while skipping large HTML contents.
    """

    def __init__(self):
        self.stdout_io = StringIO()
        self.stderr_io = StringIO()
        self.current_display_outputs = []
        self._last_result = None
        self.current_code = ''  # Add this to store current code

        # Store original streams
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._original_displayhook = sys.displayhook
        self._original_display_pub = get_ipython().display_pub.publish if get_ipython() else None
        self._original_run_line_magic = None
        if get_ipython():
            self._original_run_line_magic = get_ipython().run_line_magic

    def start_capture(self, code: str = ''):
        """Reset capture state and start capturing"""
        self.stdout_io = StringIO()
        self.stderr_io = StringIO()
        self.current_display_outputs = []
        self._last_result = None
        self.current_code = code  # Store the code being executed

        # Set up output redirection
        sys.stdout = TeeIO(self.stdout_io, self._original_stdout)
        sys.stderr = TeeIO(self.stderr_io, self._original_stderr)

        def custom_displayhook(result):
            """Handle regular Python output"""
            if result is not None:
                self._last_result = result

                # Capture the result
                result_str = str(result)
                if result_str not in self.stdout_io.getvalue():
                    self.stdout_io.write(result_str + '\n')

            # Always call original displayhook for normal display
            if self._original_displayhook:
                self._original_displayhook(result)

        sys.displayhook = custom_displayhook

        # Set up display hook if in IPython
        ip = get_ipython()
        if ip and self._original_display_pub:
            def custom_display_pub(data, metadata=None):
                # Show output immediately
                self._original_display_pub(data, metadata)

                # Skip Javascript outputs and only capture meaningful display outputs
                if any(k for k in data.keys() if k.startswith(('image/', 'application/')) 
                      and not k == 'application/javascript'):  # Add this condition
                    self.current_display_outputs.append({
                        'data': data,
                        'metadata': metadata or {}
                    })

            ip.display_pub.publish = custom_display_pub

        # Add magic command capture
        ip = get_ipython()
        if ip:
            def custom_run_line_magic(magic_name, line):
                # Capture output from magic commands
                with self._capture_output():
                    result = self._original_run_line_magic(magic_name, line)
                return result
                
            ip.run_line_magic = custom_run_line_magic

    def end_capture(self):
        """Restore original streams and get output"""
        # Get the outputs before restoring anything
        output = {
            'stdout': self.stdout_io.getvalue(),
            'stderr': self.stderr_io.getvalue(),
            'result': self._last_result,  # This should now have our expression results
            'display_outputs': self.current_display_outputs
        }

        # Restore original streams
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        sys.displayhook = self._original_displayhook

        ip = get_ipython()
        if ip and self._original_display_pub:
            ip.display_pub.publish = self._original_display_pub

        # Restore magic command handling
        if ip and self._original_run_line_magic:
            ip.run_line_magic = self._original_run_line_magic

        return output

    @contextmanager
    def _capture_output(self):
        """Context manager to capture output during magic execution"""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = TeeIO(self.stdout_io, self._original_stdout)
        sys.stderr = TeeIO(self.stderr_io, self._original_stderr)
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

class TeeIO:
    """Write to multiple streams simultaneously"""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

import os
import base64
from typing import List

def simplify_markdown_from_history(history: List[CellOutput], max_output_len: int = 500) -> str:
    """
    Simplifies the history of CellOutput objects into a markdown string, excluding images and HTML.

    Args:
        history: List of CellOutput objects representing the notebook history.
        max_output_len: Maximum length of the output string for any cell.

    Returns:
        A Markdown string representing the simplified history.
    """
    markdown = ""

    for cell in history:
        cell_markdown = f"**In [{cell.execution_count}]:**\n"
        cell_markdown += f"```python\n{cell.code}\n```\n"

        output_parts = []
        if cell.stdout:
            output_parts.append(cell.stdout)
        if cell.stderr:
            output_parts.append(f"Stderr:\n{cell.stderr}")
        if cell.result is not None and not isinstance(cell.result, type(None)):
            result_str = str(cell.result)
            if result_str not in cell.stdout:
                output_parts.append(result_str)

        if output_parts:
            output_str = "\n".join(output_parts)
            if len(output_str) > max_output_len:
                output_str = output_str[:max_output_len] + "... (truncated)"
            cell_markdown += f"**Out [{cell.execution_count}]:**\n"
            cell_markdown += f"```\n{output_str}\n```\n"
        
        if cell.error:
            cell_markdown += f"**Error [{cell.execution_count}]:**\n"
            cell_markdown += f"```\n{cell.error}\n```\n"

        markdown += cell_markdown + "\n"

    return markdown

def extract_new_images(history: List[CellOutput]) -> List[dict]:
    """
    Extracts new (unprocessed) images from the cell outputs and marks them as processed.
    """
    new_images = []

    for cell in history:
        if not hasattr(cell, 'processed_images'):
            cell.processed_images = set()

        if cell.display_outputs:
            for i, display_item in enumerate(cell.display_outputs):
                if ('data' in display_item and i not in cell.processed_images):
                    # Prefer PNG format if available
                    if 'image/png' in display_item['data']:
                        image_data = display_item['data']['image/png']
                        mime_type = 'image/png'
                    elif 'image/jpeg' in display_item['data']:
                        image_data = display_item['data']['image/jpeg']
                        mime_type = 'image/jpeg'
                    else:
                        continue

                    # The image data is already in base64 bytes format
                    if isinstance(image_data, bytes):
                        try:
                            base64_str = image_data.decode('utf-8')
                        except UnicodeDecodeError:
                            import base64
                            base64_str = base64.b64encode(image_data).decode('utf-8')
                    else:
                        base64_str = image_data

                    new_images.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': f"data:{mime_type};base64,{base64_str}",
                            'detail': 'high'
                        }
                    })
                    cell.processed_images.add(i)

    return new_images