import asyncio
from typing import List, Dict, Any
from agents import Agent, Runner
from app.logging.logger import get_logger
from app.aicore.config.model_config import get_default_model_config, ModelConfig
from .utils import count_tokens

logger = get_logger(__name__)

SUMMARIZATION_PROMPT = """You are a helpful AI assistant specialized in summarizing conversations.

Your task is to create accurate summaries of conversation histories. When given a conversation history, you should:

1. Identify the main topics and themes discussed
2. Highlight key points, decisions, and conclusions
3. Preserve important context and relationships between ideas
4. Create a coherent, well-structured summary
5. Follow the specified length requirements if provided

CRITICAL INSTRUCTIONS:
- AVOID REPETITION: Do not repeat the same information or phrases multiple times
- USE VARIED LANGUAGE: Express similar concepts using different wording
- PROGRESS LOGICALLY: Each sentence should add new information or perspective
- BE CONCISE AND PRECISE: Every word should serve a purpose

Focus on the most important information that would be useful for understanding the conversation's context and outcomes. Adapt your summary length and detail level based on the requirements specified in the user's request.
"""

class ConversationSummarizerAgent(Agent):
    """A specialized agent for summarizing conversation histories."""
    
    def __init__(self, model: str = "gpt-4o-mini-2024-07-18", model_config: ModelConfig = None):
        """Initialize the conversation summarizer agent."""
        self.model_config = model_config or get_default_model_config(model)
        
        super().__init__(
            name="Conversation Summarizer",
            instructions=SUMMARIZATION_PROMPT,
            model=self.model_config.name
        )
    
    def get_context_limit(self) -> int:
        """Get the context window limit for this model."""
        return self.model_config.capabilities.context_window
    
    def get_max_output_tokens(self) -> int:
        """Get the maximum output tokens for this model."""
        return self.model_config.capabilities.max_output_tokens
    
    def supports_long_context(self) -> bool:
        """Check if model supports long context conversations."""
        return self.model_config.capabilities.supports_long_context

async def summarize_conversation_async(
    conversation_history: List[Dict[str, Any]], 
    model: str = "gpt-4o-mini-2024-07-18",
    summary_length: str = "medium",
    max_tokens: int = None,
    model_config: ModelConfig = None
) -> str:
    """
    Asynchronously summarize a conversation history using an AI agent.
    
    Args:
        conversation_history: List of conversation messages, each containing 'role' and 'content'
        model: The model to use for summarization
        summary_length: Length of summary - "brief" (~100-200 words), "medium" (~200-400 words), 
                       "detailed" (~400-600 words), or "comprehensive" (~600+ words)
        max_tokens: Maximum tokens for the response (optional, overrides summary_length if specified)
        model_config: Optional model configuration to use
        
    Returns:
        str: The conversation summary
    """
    logger.info(f"Starting conversation summarization with {len(conversation_history)} messages")
    
    try:
        # Create the summarizer agent with model config
        agent = ConversationSummarizerAgent(model=model, model_config=model_config)
        
        # Log model capabilities
        logger.info(f"Using model: {agent.model_config.display_name}")
        logger.info(f"Context window: {agent.get_context_limit():,} tokens")
        logger.info(f"Max output tokens: {agent.get_max_output_tokens():,} tokens")
        logger.info(f"Supports long context: {agent.supports_long_context()}")
        
        # Format the conversation history into a readable format
        formatted_conversation = ""
        for i, message in enumerate(conversation_history, 1):
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            formatted_conversation += f"Message {i} ({role}):\n{content}\n\n"
        
        # Check if conversation fits within context window using precise token counting
        estimated_input_tokens = count_tokens(formatted_conversation, model)
        context_limit = agent.get_context_limit()
        max_output = max_tokens or agent.get_max_output_tokens()
        
        # Reserve tokens for prompt overhead (~500 tokens)
        available_context = context_limit - max_output - 500
        
        if estimated_input_tokens > available_context:
            error_msg = (
                f"Conversation exceeds model context window. "
                f"Estimated input tokens: {estimated_input_tokens:,}, "
                f"Available context: {available_context:,}, "
                f"Model context limit: {context_limit:,}, "
                f"Reserved for output: {max_output:,} tokens. "
                f"Please reduce conversation length or use a model with larger context window."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Define length specifications with structure guidelines
        length_specs = {
            "brief": "Keep the summary brief (100-200 words). Focus only on the most essential points. Use a single coherent paragraph.",
            
            "medium": "Provide a medium-length summary (200-400 words). Include main topics and key details. Organize into 2-3 clear paragraphs.",
            
            "detailed": "Create a detailed summary (400-600 words). Cover all important aspects thoroughly. Structure with clear topic transitions and 3-4 well-organized paragraphs.",
            
            "comprehensive": """Generate a comprehensive summary (600+ words) using this structure:
            
**Structure Guidelines:**
- Start with an executive overview (1-2 sentences)
- Organize into clear sections with logical flow
- Use subheadings or clear paragraph breaks for different topics
- Include context, process, and outcomes
- End with key takeaways or implications
- Ensure each paragraph adds unique value without repetition"""
        }
        
        length_instruction = length_specs.get(summary_length, length_specs["medium"])
        
        # Add token limit instruction if specified
        token_instruction = f"\n\nIMPORTANT: Limit your response to approximately {max_tokens} tokens." if max_tokens else ""
        
        # Create the summarization prompt
        summarization_request = f"""Please summarize the following conversation history:

{formatted_conversation}

{length_instruction}

Provide a well-structured summary that captures the main topics, key points, and important context from this conversation.{token_instruction}"""
        
        # Run the agent to generate the summary
        result = await Runner.run(
            agent,
            input=summarization_request
        )
        
        summary = result.final_output
        logger.info(f"Conversation summary generated successfully: {len(summary)} characters")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error during conversation summarization: {e}")
        raise

def summarize_conversation(
    conversation_history: List[Dict[str, Any]], 
    model: str = "gpt-4o-mini-2024-07-18",
    summary_length: str = "medium",
    max_tokens: int = None,
    model_config: ModelConfig = None
) -> str:
    """
    Synchronous wrapper for summarizing a conversation history.
    
    Args:
        conversation_history: List of conversation messages, each containing 'role' and 'content'
        model: The model to use for summarization
        summary_length: Length of summary - "brief", "medium", "detailed", or "comprehensive"
        max_tokens: Maximum tokens for the response (optional)
        model_config: Optional model configuration to use
        
    Returns:
        str: The conversation summary
    """
    return asyncio.run(summarize_conversation_async(conversation_history, model, summary_length, max_tokens, model_config))

# Example usage function
def example_usage():
    """Example of how to use the conversation summarizer."""
    
    # Example conversation history
    sample_conversation = [
        {"role": "user", "content": "Hello, I'm working on a Python project and need help with data visualization."},
        {"role": "assistant", "content": "I'd be happy to help! What kind of data visualization are you looking to create?"},
        {"role": "user", "content": "I have sales data and want to create a bar chart showing monthly revenue."},
        {"role": "assistant", "content": "Great! You can use matplotlib or plotly for this. Here's a simple example using matplotlib..."},
        {"role": "user", "content": "That worked perfectly! Now I also need to add a trend line."},
        {"role": "assistant", "content": "Excellent! To add a trend line, you can use numpy's polyfit function..."}
    ]
    
    # Generate summary
    summary = summarize_conversation(sample_conversation)
    print("Conversation Summary:")
    print(summary)
    
    return summary

if __name__ == "__main__":
    example_usage()
