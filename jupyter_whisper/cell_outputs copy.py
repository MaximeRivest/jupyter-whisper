
from io import StringIO
import sys
import time
from IPython import get_ipython
import warnings
from io import StringIO
from contextlib import contextmanager
from .config import get_config_manager
from IPython.display import display, HTML, Image, SVG, Markdown, Latex, JSON, Audio, Video, Javascript


@contextmanager
def warning_catcher():
    """Catch warnings and convert them to a string."""
    warning_output = StringIO()
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        yield warning_output
        for warning in caught_warnings:
            warning_output.write(f"Warning: {warning.message}\n")
            

class OutputCatcher:
    """Enhanced output catcher with proper context manager implementation."""
    
    def __init__(self):
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.warning_catcher = warning_catcher()
        self.display_outputs = []
        self.execution_count = None
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self.error = None
        self.start_time = None
        self.execution_time = None
        self.images = [] 

    def __enter__(self):
        """Set up output catching."""
        self.start_time = time.time()
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.warning_output = self.warning_catcher.__enter__()
        
        # Get IPython shell
        ip = get_ipython()
        if ip:
            # Save original display hook
            self.original_display_hook = ip.displayhook
            self.execution_count = ip.execution_count
            
            # Override display functions if needed
            if hasattr(ip, 'display_pub'):
                self.original_display_pub = ip.display_pub.publish
                ip.display_pub.publish = self.capture_display
        
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Clean up output catching."""
        # Restore standard outputs
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        
        # Handle warnings
        self.warning_catcher.__exit__(exc_type, exc_value, exc_tb)
        
        # Calculate execution time
        if self.start_time:
            self.execution_time = time.time() - self.start_time
        
        # Store any error that occurred
        if exc_type:
            self.error = exc_value
            
        # Restore IPython display hooks
        ip = get_ipython()
        if ip:
            if hasattr(self, 'original_display_hook'):
                ip.displayhook = self.original_display_hook
            if hasattr(self, 'original_display_pub'):
                ip.display_pub.publish = self.original_display_pub

    def capture_display(self, data, metadata=None, *args, **kwargs):
        """Capture display data with special handling for images."""
        global captured_images
        
        # Store the display output as before
        self.display_outputs.append({
            'data': data,
            'metadata': metadata
        })
        
        # Special handling for images
        if data.get('image/png'):
            image_data = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{data['image/png']}",
                    "detail": "high"
                }
            }
            self.images.append(image_data)  # Store for current execution
            captured_images.append(image_data)  # Add to global rolling window

    def get_output(self):
        """Get all captured outputs."""
        return {
            'stdout': self.stdout.getvalue(),
            'stderr': self.stderr.getvalue(),
            'warnings': self.warning_output.getvalue() if hasattr(self, 'warning_output') else '',
            'error': self.error,
            'display_outputs': self.display_outputs,
            'execution_count': self.execution_count,
            'execution_time': self.execution_time
        }
    

def clean_cell_output(cell_output, truncation_level='normal'):
    """
    Clean cell output with different truncation levels:
    - 'none': Keep everything (for most recent output)
    - 'normal': Truncate to 500 chars (for recent history)
    - 'aggressive': Truncate to 20 chars (for older history)
    """
    if not isinstance(cell_output, dict):
        return cell_output
        
    cleaned = {}
    for key, value in cell_output.items():
        # Skip empty values
        if not value:
            continue
            
        if isinstance(value, list):
            cleaned[key] = [clean_cell_output(item, truncation_level) 
                          for item in value]
        elif isinstance(value, dict):
            if key == 'data' and 'image/png' in value:
                # Always truncate base64 images
                img_data = value['image/png']
                cleaned[key] = {'image/png': img_data[:50] + '...'}
            else:
                cleaned[key] = clean_cell_output(value, truncation_level)
        else:
            if isinstance(value, str):
                if truncation_level == 'aggressive':
                    cleaned[key] = value[:500] + '...' if len(value) > 500 else value
                elif truncation_level == 'normal':
                    cleaned[key] = value[:2000] + '...' if len(value) > 2000 else value
                else:  # 'none'
                    cleaned[key] = value
            else:
                cleaned[key] = value
                
    return cleaned

def summarize_old_outputs(cell_outputs):
    """
    Summarize old cell outputs using the configured LLM.
    Processes outputs in batches of 5 when history gets too long.
    """
    # Get model from config
    try:
        config_manager = get_config_manager()
        model, provider = config_manager.get_model()
        summarizer = config_manager.execute_provider_initialization(
                provider_name=provider,
                model=model,
                system_prompt="Summarize these Jupyter notebook cell executions concisely"
            )
        
        # Process outputs that need summarization (keeping last 20 as is)
        if len(cell_outputs) <= 10:
            return cell_outputs

        # Group older outputs into batches of 5 for summarization
        outputs_to_summarize = cell_outputs[:-10]  # Everything except last 20
        summarized_outputs = []
        
        for i in range(0, len(outputs_to_summarize), 5):
            batch = outputs_to_summarize[i:i+5]
            
            # Create a prompt for the batch
            prompt = "Keep any context or code that is essential to keep working on this notebook, but remove everything else:\n\n"
            for output in batch:
                prompt += f"Input: {output.get('input', '')}...\n"
                prompt += f"Output: {str(output.get('output', ''))}...\n"
                if output.get('error'):
                    prompt += f"Error: {output.get('error')}...\n"
                prompt += "\n"
            
            # Get summary from LLM
            try:
                response = ''.join([item for item in summarizer(prompt)])
                
                # Create a summarized output entry
                summarized_output = {
                    'input': '[Batch Summary]',
                    'output': response,
                    'timestamp': batch[-1].get('timestamp'),
                    'type': 'summary',
                    'original_count': len(batch)
                }
                summarized_outputs.append(summarized_output)
            except Exception as e:
                print(f"Error summarizing batch: {str(e)}")
                # Fall back to aggressive truncation
                for output in batch:
                    summarized_outputs.append(clean_cell_output(output, 'aggressive'))

        # Return summarized outputs + last 20 original outputs
        return summarized_outputs + cell_outputs[-20:]

    except Exception as e:
        print(f"Error in summarize_old_outputs: {str(e)}")
        return cell_outputs
    


def pre_run_cell(info):
    """Pre-cell execution hook that initializes output capture."""
    global output_catcher
    
    try:
        output_catcher = OutputCatcher()
        output_catcher.__enter__()
    except Exception as e:
        print(f"Error in pre_run_cell: {str(e)}")
        output_catcher = None


def post_run_cell(result):
    global cell_outputs, output_catcher

    try:
        # Finish capturing
        if output_catcher is not None:
            output_catcher.__exit__(None, None, None)
            outputs = output_catcher.get_output()
            
            # First handle stdout and stderr
            if outputs.get('stdout'):
                print(outputs['stdout'], end='')
            if outputs.get('stderr'):
                print(outputs['stderr'], file=sys.stderr, end='')
            if outputs.get('warnings'):
                print(outputs['warnings'], file=sys.stderr, end='')
            
            # Store outputs
            if outputs:
                cell_outputs.append(outputs)
            
            # Then handle display outputs
            for display_output in outputs.get('display_outputs', []):
                data = display_output.get('data', {})
                metadata = display_output.get('metadata', {})
                
                # Display based on MIME type
                for mime_type, content in data.items():
                    try:
                        if mime_type == 'text/plain':
                            continue  # Skip text/plain for display outputs as it's usually redundant
                        elif mime_type == 'image/png':
                            import base64
                            img_data = base64.b64decode(content)
                            display(Image(data=img_data, format='png', metadata=metadata))
                        elif mime_type == 'text/html':
                            display(HTML(content))
                        elif mime_type == 'text/markdown':
                            display(Markdown(content))
                        elif mime_type == 'image/svg+xml':
                            display(SVG(content))
                        elif mime_type == 'application/json':
                            display(JSON(content))
                        elif mime_type == 'text/latex':
                            display(Latex(content))
                        elif mime_type == 'application/javascript':
                            display(Javascript(content))
                        elif mime_type.startswith(('audio/', 'video/')):
                            if mime_type.endswith(('mp4', 'webm', 'ogg')):
                                display(Video(data=content))
                            else:
                                display(Audio(data=content))
                    except Exception as e:
                        print(f"Error displaying {mime_type}: {str(e)}")
            
            # Clean up
            output_catcher = None

    except Exception as e:
        print(f"Error in post_run_cell: {str(e)}")
        output_catcher = None

    # Get raw cell content
    raw_cell = getattr(result.info, 'raw_cell', '')
    # Initialize output data
    output_data = {
        'input': raw_cell,
        'output': None,
        'stdout': '',
        'stderr': '',
        'error': None,
        'display_outputs': []
    }

    # Collect display outputs
    if hasattr(result, 'display_outputs'):
        for display_output in result.display_outputs:
            if display_output.output_type == 'stream':
                if display_output.name == 'stdout':
                    output_data['stdout'] += display_output.text
                    print(display_output.text, end='')
                elif display_output.name == 'stderr':
                    output_data['stderr'] += display_output.text
                    print(display_output.text, file=sys.stderr, end='')
            elif display_output.output_type == 'error':
                output_data['error'] = display_output.evalue
                output_data['stderr'] += '\n'.join(display_output.traceback)
                print('\n'.join(display_output.traceback), file=sys.stderr)
            elif display_output.output_type in ('execute_result', 'display_data'):
                # Handle rich display outputs
                data = display_output.data
                metadata = display_output.metadata
                output_data['display_outputs'].append({'data': data, 'metadata': metadata})

                # Now display the output appropriately
                for mime_type, content in data.items():
                    try:
                        if mime_type == 'text/plain':
                            print(content, end='')
                        elif mime_type == 'image/png':
                            # Force immediate display of images/plots
                            display(Image(data=content, format='png', metadata=metadata))
                            continue  # Skip other MIME types for this output
                        elif mime_type == 'text/html':
                            display(HTML(content))
                        elif mime_type == 'text/markdown':
                            display(Markdown(content))
                        elif mime_type == 'image/jpeg':
                            display(Image(data=content))
                        elif mime_type == 'image/svg+xml':
                            display(SVG(content))
                        elif mime_type == 'application/json':
                            display(JSON(content))
                        elif mime_type == 'text/latex':
                            display(Latex(content))
                        elif mime_type == 'application/javascript':
                            display(Javascript(content))
                        elif mime_type == 'application/vnd.plotly.v1+json':
                            display(JSON(content))
                        elif mime_type == 'audio/mpeg' or mime_type == 'audio/wav' or mime_type == 'audio/ogg':
                            display(Audio(data=content))
                        elif mime_type == 'video/mp4' or mime_type == 'video/webm' or mime_type == 'video/ogg':
                            display(Video(data=content))
                        else:
                            print(f'Unrecognized MIME type: {mime_type}')
                    except Exception as e:
                        print(f"Error displaying {mime_type}: {str(e)}")

    # Check for errors
    if hasattr(result, 'error_in_exec') and result.error_in_exec is not None:
        output_data['error'] = str(result.error_in_exec)
        if hasattr(result, 'traceback'):
            output_data['stderr'] += '\n'.join(result.traceback)
            print('\n'.join(result.traceback), file=sys.stderr)

    # Get the result of the cell execution
    if hasattr(result, 'result') and result.result is not None:
        output_data['output'] = str(result.result)

    # Append to cell_outputs if there's content
    if raw_cell.strip():
        cell_outputs.append(output_data)

        # Smart cleaning of cell outputs
    if len(cell_outputs) > 0:
        # Keep the last output complete (except images)
        cell_outputs[-1] = clean_cell_output(cell_outputs[-1], 'none')
        
        # Truncate the previous 5 outputs to 500 chars
        start_idx = max(0, len(cell_outputs) - 6)
        end_idx = len(cell_outputs) - 1
        for i in range(start_idx, end_idx):
            cell_outputs[i] = clean_cell_output(cell_outputs[i], 'normal')
            
        # Aggressively truncate older outputs
        for i in range(0, start_idx):
            cell_outputs[i] = clean_cell_output(cell_outputs[i], 'aggressive')

    #if len(cell_outputs) > 10 and len(cell_outputs) % 5 == 0:
    #    cell_outputs = summarize_old_outputs(cell_outputs)



def clear_cell_outputs(max_size: int = None):
    """
    Clear outputs older than a certain size.

    Parameters:
    - max_size: int
        - Maximum allowable size (in characters) for outputs.
    """
    global cell_outputs
    
    # Process display outputs to properly show images
    for output in cell_outputs:
        if 'display_outputs' in output:
            for display_out in output['display_outputs']:
                if 'data' in display_out:
                    # Display the output using IPython.display
                    display(display_out['data'])
    
    # Then clear based on size if specified
    if max_size:
        cell_outputs = [output for output in cell_outputs if len(str(output)) <= max_size]

def clear_old_cell_outputs(threshold_index: int):
    """
    Clear outputs older than a certain index.

    Parameters:
    - threshold_index: int
        - Outputs with indices less than this will be cleared.
    """
    global cell_outputs
    cell_outputs = cell_outputs[threshold_index:]

def clear_cell_outputs_by_size(max_size: int):
    """
    Clear outputs that exceed a certain size.

    Parameters:
    - max_size: int
        - Maximum allowable size (in characters) for outputs.
    """
    global cell_outputs
    cell_outputs = [output for output in cell_outputs if len(output) <= max_size]

def clear_old_cell_outputs(threshold_index: int):
    """
    Clear outputs older than a certain index.

    Parameters:
    - threshold_index: int
        - Outputs with indices less than this will be cleared.
    """
    global cell_outputs
    cell_outputs = cell_outputs[threshold_index:]