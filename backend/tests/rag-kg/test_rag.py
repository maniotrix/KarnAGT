from agents import Agent, Runner, Tool, function_tool

from openai.types.responses import ResponseTextDeltaEvent

import asyncio
import os
from dotenv import load_dotenv
import logging
import sys

backend_dir = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, backend_dir)

from aicore.logger import get_logger, set_log_level

#logging.basicConfig(level=logging.DEBUG)
logger = get_logger(__name__, logging.DEBUG)

env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")  
load_dotenv(env_file)

# Get the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables")
else:
    logger.info("OPENAI_API_KEY is set in the environment variables")

# Create a simple agent
agent = Agent(
    name="RAG Agent",
    model="gpt-4o-mini-2024-07-18",
    instructions="You are a helpful assistant that can answer questions about the documents.",
    tools=[],
)

def stream_callback(text_chunk):
    print(text_chunk, end="", flush=True)


@function_tool(
    name_override="rag_tool",
    description_override="""
    A tool that can answer questions about the documents.
    You can use this tool to answer questions about the documents.
    """,
    strict_mode=True
)
def rag_tool(query: str) -> str:
    """
    A tool that can answer questions about the documents.
    """
    return "This is a test tool"


async def main():
    # Create a simple agent
    agent.tools.append(rag_tool)
    
    last_response_id = None
    streaming_callback = stream_callback
    
    result = Runner.run_streamed(
        agent,
        input="What is the capital of France?",
        previous_response_id=last_response_id,
    )
    
    # Collect the full response while streaming
    full_response = ""
    
    try:
        # Process streaming events with cancellation check
        async for event in result.stream_events():
                
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                # Get the text delta
                text_delta = event.data.delta
                
                # Add to the full response
                full_response += text_delta
                
                # Call the streaming callback with the delta
                if streaming_callback:
                    streaming_callback(text_delta)
                    
    except asyncio.CancelledError:
        logger.info("🛑 Stream cancelled via asyncio.CancelledError from Agents SDK")
    
    # print(full_response)

if __name__ == "__main__":
    asyncio.run(main())
