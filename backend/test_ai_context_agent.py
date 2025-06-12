from app.services.context.ai_context_agent import summarize_conversation
from aicore.config.model_config import get_default_model_config, get_gpt4o_mini_config

def test_model_configuration():
    """Test model configuration and capabilities."""
    
    print("=" * 80)
    print("TESTING MODEL CONFIGURATION")
    print("=" * 80)
    
    # Test default model config
    config = get_default_model_config()
    print(f"Default Model: {config.display_name}")
    print(f"Context Window: {config.capabilities.context_window:,} tokens")
    print(f"Max Output Tokens: {config.capabilities.max_output_tokens:,} tokens")
    print(f"Supports Long Context: {config.capabilities.supports_long_context}")
    print(f"Supports Vision: {config.capabilities.supports_vision}")
    print(f"Input Cost: ${config.costs.input_token_cost}/1K tokens")
    print(f"Output Cost: ${config.costs.output_token_cost}/1K tokens")
    
    # Test GPT-4o mini specific config
    gpt4o_config = get_gpt4o_mini_config()
    print(f"\nGPT-4o Mini Configuration:")
    print(f"Name: {gpt4o_config.name}")
    print(f"Display Name: {gpt4o_config.display_name}")
    print(f"Context Window: {gpt4o_config.capabilities.context_window:,} tokens")
    print(f"Max Output: {gpt4o_config.capabilities.max_output_tokens:,} tokens")
    print(f"Tags: {', '.join(gpt4o_config.tags)}")

def test_context_window_overflow():
    """Test context window overflow error handling."""
    
    print("\n" + "=" * 80)
    print("TESTING CONTEXT WINDOW OVERFLOW")
    print("=" * 80)
    
    # Create a very long conversation that should exceed context window
    # Simulate a conversation with very long messages
    long_content = "This is a very long message. " * 1000  # ~30K characters
    
    massive_conversation = []
    for i in range(20):  # 20 messages with long content each
        massive_conversation.extend([
            {"role": "user", "content": f"User message {i+1}: {long_content}"},
            {"role": "assistant", "content": f"Assistant response {i+1}: {long_content}"}
        ])
    
    print(f"Created test conversation with {len(massive_conversation)} messages")
    total_chars = sum(len(msg['content']) for msg in massive_conversation)
    estimated_tokens = total_chars // 4
    print(f"Total characters: {total_chars:,}")
    print(f"Estimated tokens: {estimated_tokens:,}")
    
    try:
        print("\nAttempting to summarize massive conversation...")
        summary = summarize_conversation(massive_conversation, summary_length="brief")
        print("❌ ERROR: Should have thrown context window error!")
        print(f"Summary: {summary[:100]}...")
        
    except ValueError as e:
        print("✅ SUCCESS: Context window overflow properly detected!")
        print(f"Error message: {str(e)}")
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")

def example_usage():
    """Example of how to use the conversation summarizer with different length options."""
    
    # Example conversation history
    sample_conversation = [
        {"role": "user", "content": "Hello, I'm working on a Python project and need help with data visualization."},
        {"role": "assistant", "content": "I'd be happy to help! What kind of data visualization are you looking to create?"},
        {"role": "user", "content": "I have sales data and want to create a bar chart showing monthly revenue."},
        {"role": "assistant", "content": "Great! You can use matplotlib or plotly for this. Here's a simple example using matplotlib to create a bar chart: import matplotlib.pyplot as plt; plt.bar(months, revenue); plt.title('Monthly Revenue'); plt.show()"},
        {"role": "user", "content": "That worked perfectly! Now I also need to add a trend line to show the growth pattern."},
        {"role": "assistant", "content": "Excellent! To add a trend line, you can use numpy's polyfit function to calculate the linear regression and then plot it: import numpy as np; z = np.polyfit(x_values, revenue, 1); p = np.poly1d(z); plt.plot(months, p(x_values), 'r--', alpha=0.8)"},
        {"role": "user", "content": "Perfect! One last question - how can I save this chart as a high-resolution image?"},
        {"role": "assistant", "content": "You can save it using plt.savefig('chart.png', dpi=300, bbox_inches='tight') before calling plt.show(). The dpi=300 ensures high resolution, and bbox_inches='tight' removes extra whitespace."}
    ]
    
    print("\n" + "=" * 80)
    print("TESTING DIFFERENT SUMMARY LENGTHS")
    print("=" * 80)
    
    # Test different summary lengths
    summary_types = [
        ("brief", "Brief Summary (100-200 words)"),
        ("medium", "Medium Summary (200-400 words)"),
        ("detailed", "Detailed Summary (400-600 words)"),
        ("comprehensive", "Comprehensive Summary (600+ words)")
    ]
    
    for summary_type, description in summary_types:
        print(f"\n{'-' * 60}")
        print(f"{description}")
        print(f"{'-' * 60}")
        
        try:
            summary = summarize_conversation(
                sample_conversation, 
                summary_length=summary_type
            )
            print(f"Length: {len(summary)} characters")
            print(f"Word count: ~{len(summary.split())} words")
            print(f"\nContent:\n{summary}")
            
        except Exception as e:
            print(f"Error generating {summary_type} summary: {e}")
    
    # Test with token limit
    print(f"\n{'-' * 60}")
    print("Token-Limited Summary (Max 100 tokens)")
    print(f"{'-' * 60}")
    
    try:
        token_limited_summary = summarize_conversation(
            sample_conversation,
            summary_length="medium",
            max_tokens=100
        )
        print(f"Length: {len(token_limited_summary)} characters")
        print(f"Word count: ~{len(token_limited_summary.split())} words")
        print(f"\nContent:\n{token_limited_summary}")
        
    except Exception as e:
        print(f"Error generating token-limited summary: {e}")
    
    print("\n" + "=" * 80)
    print("SUMMARY LENGTH COMPARISON COMPLETE")
    print("=" * 80)

def test_custom_model_config():
    """Test using custom model configuration."""
    
    print("\n" + "=" * 80)
    print("TESTING CUSTOM MODEL CONFIGURATION")
    print("=" * 80)
    
    # Create custom config with different parameters
    custom_config = get_gpt4o_mini_config()
    custom_config.parameters.temperature = 0.3  # More deterministic
    custom_config.parameters.max_tokens = 200   # Lower token limit
    
    sample_conversation = [
        {"role": "user", "content": "What are the benefits of using Python for data science?"},
        {"role": "assistant", "content": "Python offers excellent libraries like pandas, numpy, scikit-learn, and matplotlib for data analysis, machine learning, and visualization."},
        {"role": "user", "content": "How does it compare to R?"},
        {"role": "assistant", "content": "Python is more general-purpose and has better integration with web applications, while R is specialized for statistics but has a steeper learning curve."},
    ]
    
    print("Testing with custom configuration (temperature=0.3, max_tokens=200)...")
    
    try:
        summary = summarize_conversation(
            sample_conversation,
            summary_length="medium",
            model_config=custom_config
        )
        print(f"Custom config summary length: {len(summary)} characters")
        print(f"Word count: ~{len(summary.split())} words")
        print(f"\nContent:\n{summary}")
        
    except Exception as e:
        print(f"Error with custom config: {e}")

def test_specific_length():
    """Test a specific summary length quickly."""
    
    sample_conversation = [
        {"role": "user", "content": "I need help setting up a REST API with FastAPI."},
        {"role": "assistant", "content": "I'll help you set up FastAPI! First, install it with pip install fastapi uvicorn, then create a basic app.py file."},
        {"role": "user", "content": "Great! How do I add database integration?"},
        {"role": "assistant", "content": "You can use SQLAlchemy with FastAPI. Install sqlalchemy and your database driver, then set up models and database connection."},
    ]
    
    print("\n" + "=" * 80)
    print("QUICK TEST - MEDIUM LENGTH SUMMARY")
    print("=" * 80)
    
    summary = summarize_conversation(sample_conversation, summary_length="medium")
    print(f"Characters: {len(summary)} | Words: ~{len(summary.split())}")
    print(f"\n{summary}")

def run_comprehensive_tests():
    """Run all test functions."""
    
    print("🧪 STARTING COMPREHENSIVE AI CONTEXT AGENT TESTS")
    print("=" * 80)
    
    # Test 1: Model Configuration
    test_model_configuration()
    
    # Test 2: Context Window Overflow
    test_context_window_overflow()
    
    # Test 3: Custom Model Config
    test_custom_model_config()
    
    # Test 4: Summary Length Options
    example_usage()
    
    # Test 5: Quick Test
    test_specific_length()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    from aicore.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Starting comprehensive conversation summarizer testing")
    
    from aicore.ai_config import validate_api_keys
    validate_api_keys()
    
    # Run all tests
    run_comprehensive_tests()