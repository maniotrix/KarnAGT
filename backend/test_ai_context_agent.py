from app.services.context.ai_context_agent import summarize_conversation

# Example usage function
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
    
    print("=" * 80)
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

def test_specific_length():
    """Test a specific summary length quickly."""
    
    sample_conversation = [
        {"role": "user", "content": "I need help setting up a REST API with FastAPI."},
        {"role": "assistant", "content": "I'll help you set up FastAPI! First, install it with pip install fastapi uvicorn, then create a basic app.py file."},
        {"role": "user", "content": "Great! How do I add database integration?"},
        {"role": "assistant", "content": "You can use SQLAlchemy with FastAPI. Install sqlalchemy and your database driver, then set up models and database connection."},
    ]
    
    print("\nQuick Test - Medium Length Summary:")
    print("-" * 40)
    
    summary = summarize_conversation(sample_conversation, summary_length="medium")
    print(f"Characters: {len(summary)} | Words: ~{len(summary.split())}")
    print(f"\n{summary}")

if __name__ == "__main__":
    from aicore.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Starting conversation summarizer length testing")
    
    from aicore.ai_config import validate_api_keys
    validate_api_keys()
    
    # Run the comprehensive test
    # example_usage()
    
    # Run a quick test
    test_specific_length()