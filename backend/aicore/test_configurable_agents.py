#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command line interface for testing the new configurable AI system
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

# Use the new configurable system
from aicore import ConfigurableAssistantClient, ConfigManager, AIConfig, config_manager
from aicore.ai_config import validate_api_keys
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
    print(f"{COLORS['bold']}{COLORS['blue']}   Configurable AI Chat - CLI Interface   {COLORS['reset']}")
    print(f"{COLORS['bold']}{COLORS['cyan']}======================================{COLORS['reset']}")
    print()
    print(f"{COLORS['yellow']}Chat powered by Configurable OpenAI Agents SDK{COLORS['reset']}")
    print(f"{COLORS['yellow']}Type 'quit', 'exit', or press Ctrl+C to end the chat{COLORS['reset']}")
    print(f"{COLORS['yellow']}Type 'clear' to clear the conversation history{COLORS['reset']}")
    print(f"{COLORS['yellow']}Type 'config' to view current configuration{COLORS['reset']}")
    print()


def stream_callback(text_chunk):
    """Callback function for streaming text chunks to the terminal"""
    # Print the text chunk without a newline to create a streaming effect
    print(text_chunk, end="", flush=True)


def create_simple_config(model_name: str = None) -> AIConfig:
    """
    Create a simple configuration with just OpenAI settings
    
    Args:
        model_name: Optional model name override
        
    Returns:
        AIConfig: Simple configuration for testing
    """
    # Start with default configuration
    config = config_manager.load_config()
    
    # Override model name if provided
    if model_name:
        config.model.name = model_name
        logger.info(f"Using model: {model_name}")
    
    # Ensure OpenAI provider is set (should be default)
    from aicore.config.model_config import ModelProvider
    from aicore.config.runner_config import StreamingMode
    
    config.model.provider.provider = ModelProvider.OPENAI
    config.model.provider.api_key_env_var = "OPENAI_API_KEY"
    
    # Enable streaming for better CLI experience
    config.runner.streaming.mode = StreamingMode.TEXT_ONLY
    
    # Set reasonable defaults for CLI usage
    config.agent.name = "CLI Test Assistant"
    config.runner.execution.max_turns = 10
    
    logger.info("Simple configuration created successfully")
    return config


def create_configurable_client(model_name: str = None) -> ConfigurableAssistantClient:
    """Create and return a new configurable assistant client"""
    logger.info("Creating new configurable assistant client")
    
    try:
        # Create simple configuration
        config = create_simple_config(model_name)
        
        # Create the configurable client
        client = ConfigurableAssistantClient(
            user_id="cli_test_user",
            conversation_id="cli_session",
            environment="development"
        )
        
        # Update with our simple config
        client.update_configuration(config=config)
        
        # Set streaming callback
        client.set_streaming_callback(stream_callback)
        
        logger.info("Configurable assistant client created successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create configurable client: {e}")
        raise


def display_configuration(client: ConfigurableAssistantClient, conversation_history=None):
    """Display current configuration"""
    print(f"\n{COLORS['cyan']}Current Configuration:{COLORS['reset']}")
    summary = client.get_configuration_summary()
    
    print(f"  Agent Name: {COLORS['green']}{summary.get('agent_name', 'Unknown')}{COLORS['reset']}")
    print(f"  Model: {COLORS['green']}{summary.get('model_name', 'Unknown')}{COLORS['reset']}")
    print(f"  Provider: {COLORS['green']}{summary.get('provider', 'Unknown')}{COLORS['reset']}")
    print(f"  Streaming: {COLORS['green']}{summary.get('streaming_enabled', False)}{COLORS['reset']}")
    print(f"  Max Turns: {COLORS['green']}{summary.get('max_turns', 0)}{COLORS['reset']}")
    print(f"  Tools: {COLORS['green']}{', '.join(summary.get('tools_enabled', []))}{COLORS['reset']}")
    print(f"  Environment: {COLORS['green']}{summary.get('environment', 'Unknown')}{COLORS['reset']}")
    
    # Show conversation context info
    if conversation_history is not None:
        print(f"  Conversation Messages: {COLORS['green']}{len(conversation_history)}{COLORS['reset']}")
        if conversation_history:
            last_role = conversation_history[-1].get("role", "unknown")
            print(f"  Last Message From: {COLORS['green']}{last_role}{COLORS['reset']}")
    
    print()


async def chat_loop(client: ConfigurableAssistantClient):
    """
    Main chat loop for the CLI application.
    
    Maintains conversation history locally and passes full context to each API call,
    ensuring the LLM has access to previous exchanges for proper conversational flow.
    """
    try:
        # Initialize conversation history - maintains full conversation context
        # including both user messages and assistant responses
        conversation_history = []
        
        while True:
            # Get user input
            print(f"{COLORS['bold']}{COLORS['green']}You:{COLORS['reset']} ", end="")
            user_input = input().strip()
            
            # Handle special commands
            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{COLORS['yellow']}Goodbye!{COLORS['reset']}")
                break
            elif user_input.lower() == "clear":
                client.clear_conversation_memory()
                conversation_history.clear()  # Clear local history too
                clear_screen()
                display_welcome_message()
                continue
            elif user_input.lower() == "config":
                display_configuration(client, conversation_history)
                continue
            elif not user_input:
                continue
            
            # Add user message to conversation history
            conversation_history.append({
                "role": "user", 
                "content": user_input
            })
            
            # Display assistant prompt
            print(f"{COLORS['bold']}{COLORS['blue']}Assistant:{COLORS['reset']} ", end="")
            
            try:
                # Process message with streaming - pass full conversation context
                logger.debug(f"Sending conversation context with {len(conversation_history)} messages")
                import matplotlib
                matplotlib.use('Agg')  # Set non-interactive backend
                
                response = await client.send_message_streaming(
                    message=conversation_history,  # ✅ Pass full conversation context
                    callback=stream_callback
                )
                
                matplotlib.use('TkAgg')  # Restore interactive backend
                
                # Add a newline after the streaming response completes
                print("\n")
                
                # Add assistant response to conversation history
                assistant_response = response.get("content", "")
                if assistant_response:
                    conversation_history.append({
                        "role": "assistant",
                        "content": assistant_response
                    })
                
                # Display any plots that were generated
                plots = response.get("plots", [])
                if plots:
                    print(f"{COLORS['cyan']}Generated {len(plots)} plot(s):{COLORS['reset']}")
                    for plot in plots:
                        print(f"  📊 {plot}")
                    print()
                
                # Show if response was cancelled
                if response.get("was_cancelled", False):
                    print(f"{COLORS['yellow']}⚠️  Response was cancelled{COLORS['reset']}")
                
            except Exception as e:
                print(f"{COLORS['red']}Error: {str(e)}{COLORS['reset']}\n")
                logger.error(f"Error processing message: {e}", exc_info=True)
    
    except KeyboardInterrupt:
        print(f"\n\n{COLORS['yellow']}Chat session ended by user.{COLORS['reset']}")
        return


def main():
    """Main function for the configurable CLI chat application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Configurable OpenAI Chat CLI")
    parser.add_argument(
        "--log_level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
        default="CRITICAL",
        help="Set the logging level"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="OpenAI model name to use (e.g., gpt-4o-mini-2024-07-18, gpt-4o)"
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Show configuration and exit"
    )
    args = parser.parse_args()
    
    # Set log level
    set_log_level(args.log_level)
    
    try:
        # Validate API keys
        logger.info("Validating API keys")
        if not validate_api_keys():
            print(f"{COLORS['red']}API key validation failed. Please set OPENAI_API_KEY environment variable.{COLORS['reset']}")
            return 1
        logger.info("API keys validated successfully")
        
        # Create configurable client
        client = create_configurable_client(model_name=args.model)
        
        # If --config flag is set, just show config and exit
        if args.config:
            display_configuration(client)
            return 0
        
        # Display welcome message
        display_welcome_message()
        
        # Show current configuration
        display_configuration(client, [])
        
        # Start async chat loop
        import asyncio
        asyncio.run(chat_loop(client))
        
    except Exception as e:
        print(f"{COLORS['red']}Fatal error: {str(e)}{COLORS['reset']}")
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 