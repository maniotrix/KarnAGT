#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command line interface for the chat system powered by OpenAI Agents SDK
"""

import os
import sys
import logging
import argparse
from typing import List, Dict
from pathlib import Path

# Add the project root to Python path to ensure imports work
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from aicore.openai_assistant import OpenAIAssistant 
from aicore.config import validate_api_keys
from aicore.logger import get_logger, set_log_level

# Set up logger with INFO level as default
logger = get_logger(__name__, logging.INFO)

# ANSI color codes for terminal output
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_welcome_message():
    """Display a welcome message for the CLI chat application"""
    clear_screen()
    print(f"{COLORS['bold']}{COLORS['cyan']}======================================{COLORS['reset']}")
    print(f"{COLORS['bold']}{COLORS['blue']}   OpenAI Chat - Command Line Interface   {COLORS['reset']}")
    print(f"{COLORS['bold']}{COLORS['cyan']}======================================{COLORS['reset']}")
    print()
    print(f"{COLORS['yellow']}Chat powered by OpenAI Agents SDK{COLORS['reset']}")
    print(f"{COLORS['yellow']}Type 'quit', 'exit', or press Ctrl+C to end the chat{COLORS['reset']}")
    print(f"{COLORS['yellow']}Type 'clear' to clear the conversation history{COLORS['reset']}")
    print()


def stream_callback(text_chunk):
    """Callback function for streaming text chunks to the terminal"""
    # Print the text chunk without a newline to create a streaming effect
    print(text_chunk, end="", flush=True)


def create_agent() -> OpenAIAssistant:
    """Create and return a new OpenAI assistant agent"""
    logger.info("Creating new OpenAI agent with Agents SDK")
    
    # Create the agent with streaming callback
    agent: OpenAIAssistant = OpenAIAssistant(streaming_callback=stream_callback)
    
    return agent


def chat_loop(assistant: OpenAIAssistant):
    """Main chat loop for the CLI application"""
    try:
        while True:
            # Get user input
            print(f"{COLORS['bold']}{COLORS['green']}You:{COLORS['reset']} ", end="")
            user_input = input().strip()
            
            # Handle special commands
            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{COLORS['yellow']}Goodbye!{COLORS['reset']}")
                break
            elif user_input.lower() == "clear":
                assistant.clear_memory()
                clear_screen()
                display_welcome_message()
                continue
            elif not user_input:
                continue
            
            # Display assistant prompt
            print(f"{COLORS['bold']}{COLORS['blue']}Assistant:{COLORS['reset']} ", end="")
            
            try:
                # Process message and stream the response
                # The streaming callback will handle printing the response in real-time
                import matplotlib
                matplotlib.use('Agg')
                response = assistant.process_message(user_input)
                matplotlib.use('TkAgg')
                # Add a newline after the streaming response completes
                print("\n")
            except Exception as e:
                print(f"{COLORS['red']}Error: {str(e)}{COLORS['reset']}\n")
                logger.error(f"Error processing message: {e}", exc_info=True)
    
    except KeyboardInterrupt:
        print(f"\n\n{COLORS['yellow']}Chat session ended by user.{COLORS['reset']}")
        return


def main():
    """Main function for the CLI chat application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="OpenAI Chat Command Line Interface")
    parser.add_argument(
        "--log_level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
        default="CRITICAL",
        help="Set the logging level"
    )
    args = parser.parse_args()
    
    # Set log level
    set_log_level(args.log_level)
    
    try:
        # Validate API keys
        logger.info("Validating API keys")
        validate_api_keys()
        logger.info("API keys validated successfully")
        
        # Display welcome message
        display_welcome_message()
        
        # Create OpenAI agent
        assistant: OpenAIAssistant = create_agent()
        
        
        # Start chat loop
        chat_loop(assistant)
        
    except Exception as e:
        print(f"{COLORS['red']}Fatal error: {str(e)}{COLORS['reset']}")
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 