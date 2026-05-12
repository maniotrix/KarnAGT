import json
from typing import Any

# Import our stream events
from app.aicore.core.stream_events import (
    StreamEventUnion, 
    create_text_event,
    create_tool_start_event,  
    create_tool_output_event,
    ToolType,
    ToolStatus
)
from agents.stream_events import RunItemStreamEvent
from agents.items import (
    RunItem,
    ToolCallItem,
    ToolCallOutputItem,
    ToolCallItemTypes
)
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseComputerToolCall,
    ResponseFileSearchToolCall,
    ResponseFunctionWebSearch
)    
from app.logging.logger import get_logger

# Set up logger
logger = get_logger(__name__)

def preview_data(data: Any, max_length: int = 100) -> str:
    """
    Create a preview of data for logging purposes
    
    Args:
        data: The data to preview (could be dict, str, list, etc.)
        max_length: Maximum length of the preview string
        
    Returns:
        A truncated string representation of the data
    """
    try:
        if data is None:
            return "None"
        
        # Convert to string representation
        if isinstance(data, (dict, list)):
            data_str = str(data)
        else:
            data_str = str(data)
        
        # Truncate if too long
        if len(data_str) <= max_length:
            return data_str
        else:
            return f"{data_str[:max_length]}...[{len(data_str)-max_length} more chars]"
            
    except Exception as e:
        return f"<preview_error: {str(e)}>"

def create_tool_start_from_run_item(run_item: RunItem) -> StreamEventUnion:
    """Create a tool start event from a RunItem"""
    if not isinstance(run_item, ToolCallItem):
        logger.warning(f"Expected ToolCallItem but got {type(run_item)}")
        return create_tool_start_event(
            tool_name="unknown_tool",
            tool_type=ToolType.UNKNOWN,
            tool_id=str(id(run_item)),
            arguments={}
        )
    
    # Access the raw OpenAI tool call object
    raw_tool_call = run_item.raw_item
    
    # DEBUG: Log the actual type we're getting
    logger.info(f"[DEBUG] Raw tool call type: {type(raw_tool_call)}")
    # logger.info(f"[DEBUG] Raw tool call: {raw_tool_call}")
    
    # Use model_dump() to access Pydantic model data (this is how agents SDK does it)
    raw_data = raw_tool_call.model_dump()
    # logger.info(f"[DEBUG] Raw data after model_dump(): {raw_data}")
    
    # Extract tool information from the dumped data
    tool_id = raw_data.get('call_id', str(id(raw_tool_call)))
    
    # Determine tool type and extract relevant data
    if isinstance(raw_tool_call, ResponseFunctionToolCall):
        logger.info(f"[DEBUG] Matched ResponseFunctionToolCall")
        # Function call - data is flat, not nested under 'function'
        tool_name = raw_data.get('name', 'unknown_function')
        arguments = raw_data.get('arguments', {})
        # If arguments is a string, try to parse it as JSON
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments else {}
            except (json.JSONDecodeError, TypeError):
                arguments = {}
        tool_type = ToolType.FUNCTION_CALL
    elif isinstance(raw_tool_call, ResponseComputerToolCall):
        logger.info(f"[DEBUG] Matched ResponseComputerToolCall")
        # Computer tool
        tool_name = "computer_tool"
        computer_data = raw_data.get('computer', {})
        arguments = computer_data.get('input', {}) if computer_data else {}
        tool_type = ToolType.COMPUTER_TOOL
    elif isinstance(raw_tool_call, ResponseFileSearchToolCall):
        logger.info(f"[DEBUG] Matched ResponseFileSearchToolCall")
        # File search
        tool_name = "file_search"
        arguments = {}
        tool_type = ToolType.FILE_SEARCH  
    elif isinstance(raw_tool_call, ResponseFunctionWebSearch):
        logger.info(f"[DEBUG] Matched ResponseFunctionWebSearch")
        # Web search - extract query from action
        tool_name = "web_search"
        action_data = raw_data.get('action', {})
        query = action_data.get('query', '') if action_data else ''
        arguments = {"query": query}
        tool_type = ToolType.WEB_SEARCH
    else:
        logger.info(f"[DEBUG] No type match - falling back to raw data parsing")
        # Fallback for unknown types
        tool_name = str(type(raw_tool_call).__name__)
        arguments = {}
        tool_type = ToolType.UNKNOWN
        logger.warning(f"Unknown tool call type: {type(raw_tool_call)}")
    logger.info(f"[DEBUG] Creating tool start event: {tool_name}, {tool_type}, {tool_id}, {preview_data(arguments)}")
    return create_tool_start_event(
        tool_name=tool_name,
        tool_type=tool_type,
        tool_id=tool_id,
        arguments=arguments
    )

def create_tool_output_from_run_item(run_item: RunItem) -> StreamEventUnion:
    """Create a tool output event from a RunItem"""
    if not isinstance(run_item, ToolCallOutputItem):
        logger.warning(f"Expected ToolCallOutputItem but got {type(run_item)}")
        return create_tool_output_event(
            tool_id=str(id(run_item)),
            tool_name="unknown_tool", 
            tool_type=ToolType.UNKNOWN,
            result=None,
            status=ToolStatus.FAILED
        )
    
    # Access the raw output object and the processed output
    raw_output = run_item.raw_item
    processed_output = run_item.output
    
    # DEBUG: Log the actual raw output structure
    # logger.info(f"[DEBUG] Tool output raw_output type: {type(raw_output)}")
    # logger.info(f"[DEBUG] Tool output raw_output: {raw_output}")
    
    # Handle different types of raw_output
    if isinstance(raw_output, dict):
        # Already a dictionary (TypedDict types like FunctionCallOutput)
        raw_data = raw_output
    elif hasattr(raw_output, 'model_dump'):
        # Pydantic model
        raw_data = raw_output.model_dump()
    else:
        # Fallback - try to convert to dict or use empty dict
        raw_data = {}
        
    # logger.info(f"[DEBUG] Tool output raw_data: {raw_data}")
    
    # Extract tool information from raw output
    tool_id = raw_data.get('call_id', str(id(raw_output)))
    
    # Get the result - prefer processed output, fallback to raw
    result = processed_output if processed_output is not None else raw_data.get('output')
    
    # Determine tool name and type from the output type
    output_type = raw_data.get('type', 'unknown')
    if output_type == 'function_call_output':
        tool_name = 'function_call'
        tool_type = ToolType.FUNCTION_CALL
    elif output_type == 'computer_call_output':
        tool_name = 'computer_tool'
        tool_type = ToolType.COMPUTER_TOOL
    else:
        tool_name = output_type
        tool_type = ToolType.UNKNOWN
    
    # Status is generally completed for outputs, unless there's an error
    status = ToolStatus.COMPLETED
    if isinstance(result, str) and ('error' in result.lower() or 'failed' in result.lower()):
        status = ToolStatus.FAILED
    
    logger.info(f"[DEBUG] Creating tool output event: {tool_id}, {tool_name}, {tool_type}, {preview_data(result)}, {status}")
    return create_tool_output_event(
        tool_id=tool_id,
        tool_name=tool_name,
        tool_type=tool_type,
        result=result,
        status=status
    )

# Removed _determine_tool_type_from_run_item - tool type is now determined directly in the creation methods


