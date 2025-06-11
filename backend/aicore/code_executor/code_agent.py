import os
import glob
import uuid
from typing import Dict, List
from agents import Agent, RunContextWrapper, WebSearchTool
from aicore.code_executor.code_tool import execute_code, execute_system_command
from aicore.code_executor.logger import get_logger
# Get logger
logger = get_logger()

from aicore.prompt_utils import get_instructions_template, INITIAL_CORE_PROMPT
class CodeExecutorAgent(Agent):
    """
    A specialized Agent subclass for executing code with managed message IDs.
    
    This agent automatically handles message ID generation and injection into instructions,
    making it ideal for code execution where unique identifiers are needed for plots and files.
    """
    
    def __init__(self, name: str, root_plots_dir: str, core_prompt: str = INITIAL_CORE_PROMPT, model: str = "gpt-4o-mini-2024-07-18"):
        """
        Initialize the CodeExecutorAgent.
        
        Args:
            name: The name of the agent
            plots_dir: Directory where plots will be saved
        """
        self.core_prompt = core_prompt
        unique_id = str(uuid.uuid4())[:8]
        self.unique_plots_dir = os.path.join(root_plots_dir, unique_id)
        os.makedirs(self.unique_plots_dir, exist_ok=True)
        # check if directory is exists
        if not os.path.exists(self.unique_plots_dir):
            raise ValueError(f"Plots directory {self.unique_plots_dir} does not exist")
        else:
            logger.info(f"Plots directory {self.unique_plots_dir} exists")
            self.instructions_template = get_instructions_template(self.unique_plots_dir, core_prompt=self.core_prompt)
        
        # Current message ID for the agent
        self.current_message_id = str(uuid.uuid4())[:8]
        
        websearch_tool = WebSearchTool(user_location={"type": "approximate", "city": "New Delhi"})
        
        # Initialize the parent Agent class
        super().__init__(
            name=name,
            instructions=self._get_dynamic_instructions,
            tools=[execute_code, execute_system_command, websearch_tool],
            model=model
        )
    
    def _get_dynamic_instructions(self, run_context: RunContextWrapper, agent: Agent) -> str:
        """
        Dynamically generate instructions with the current message ID.
        
        Args:
            run_context: The current run context
            agent: The agent instance
            
        Returns:
            str: Instructions with the message ID injected
        """
        # Return instructions with the current message ID injected
        return self.instructions_template.replace("{message_id}", self.current_message_id)
    
    def set_message_id(self, message_id=None):
        """
        Set the message ID for the next execution.
        
        Args:
            message_id: Custom message ID to use, or None to generate a new one
            
        Returns:
            str: The message ID that was set
        """
        if message_id is None:
            # Generate a new message ID if none provided
            message_id = str(uuid.uuid4())[:8]
        
        self.current_message_id = message_id
        return message_id
        
    def get_all_plots_with_message_id(self) -> Dict[str, List[str]]:
        """
        Extract all message IDs from generated plot filenames along with the plots.
        Returns a dictionary mapping each message ID to a list of its associated plot file paths.
        """
        data: Dict[str, List[str]] = {}
        plots = glob.glob(f"{self.unique_plots_dir}/*_*.png")
        if not plots:
            return {}
            
        # Sort plots by creation time (newest first)
        plots.sort(key=lambda x: os.path.getctime(x), reverse=True)
        
        for plot in plots:
            msg_id = os.path.basename(plot).split('_')[0]
            if msg_id not in data:
                data[msg_id] = []
            data[msg_id].append(plot)
        return data
        
    def get_current_message_id(self) -> str:
        """
        Get the current message ID.
        
        Returns:
            str: The current message ID
        """
        return self.current_message_id
