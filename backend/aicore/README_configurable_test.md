# Testing the New Configurable AI System

This guide shows how to test the new configurable AI system with just your OpenAI API key.

## Prerequisites

1. **OpenAI API Key**: Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Python Dependencies**: Make sure you have all required dependencies installed.

## Running the Test

### Basic Usage
```bash
python backend/aicore/test_configurable_agents.py
```

### With Custom Model
```bash
python backend/aicore/test_configurable_agents.py --model gpt-4o
```

### View Configuration Only
```bash
python backend/aicore/test_configurable_agents.py --config
```

### With Debug Logging
```bash
python backend/aicore/test_configurable_agents.py --log_level DEBUG
```

## Available Commands During Chat

- `quit` or `exit` - End the chat session
- `clear` - Clear conversation history and restart
- `config` - Display current configuration settings

## Features Demonstrated

✅ **Configurable Model Selection**: Change models via command line  
✅ **Streaming Responses**: Real-time text streaming  
✅ **Code Execution**: Python code execution and plot generation  
✅ **Web Search**: Search the web for current information  
✅ **Configuration Display**: View current settings  
✅ **Memory Management**: Clear conversation history  
✅ **Error Handling**: Graceful error handling and recovery  

## Example Session

```
======================================
   Configurable AI Chat - CLI Interface   
======================================

Chat powered by Configurable OpenAI Agents SDK
Type 'quit', 'exit', or press Ctrl+C to end the chat
Type 'clear' to clear the conversation history
Type 'config' to view current configuration

Current Configuration:
  Agent Name: CLI Test Assistant
  Model: gpt-4o-mini-2024-07-18
  Provider: openai
  Streaming: True
  Max Turns: 10
  Tools: execute_code, execute_system_command, web_search
  Environment: development

You: Create a simple bar chart showing sales data
Assistant: I'll create a simple bar chart with some sample sales data for you.

[Streaming response with code execution...]

Generated 1 plot(s):
  📊 /path/to/plot/abc123_plot_1234567890.png

You: config
Current Configuration:
  Agent Name: CLI Test Assistant
  Model: gpt-4o-mini-2024-07-18
  Provider: openai
  Streaming: True
  Max Turns: 10
  Tools: execute_code, execute_system_command, web_search
  Environment: development
```

## Configuration Flexibility

The test demonstrates how the new configurable system:

1. **Automatically loads sensible defaults**
2. **Allows runtime model switching**
3. **Maintains all existing functionality**
4. **Provides configuration transparency**
5. **Enables easy debugging and monitoring**

## Comparison with Legacy System

| Feature | Legacy (`test_agents.py`) | Configurable (`test_configurable_agents.py`) |
|---------|---------------------------|-----------------------------------------------|
| Model Selection | Hardcoded | Command-line configurable |
| Configuration Visibility | Hidden | Transparent with `config` command |
| Streaming | Fixed implementation | Configurable strategy |
| Tool Management | Static | Dynamic and configurable |
| Error Handling | Basic | Enhanced with configuration awareness |
| Environment Support | None | Development/production modes |

## Next Steps

Once you've verified the basic functionality works, you can:

1. **Create custom configuration files** for different environments
2. **Set up user-specific configurations** 
3. **Experiment with different model parameters**
4. **Add custom tools and behaviors**
5. **Integrate with your existing FastAPI application** 