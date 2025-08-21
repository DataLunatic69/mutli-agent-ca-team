from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main functionality"""
        pass
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper method with error handling"""
        try:
            self.logger.info(f"Starting {self.agent_name} execution")
            result = await self.execute(input_data)
            self.logger.info(f"{self.agent_name} execution completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"{self.agent_name} execution failed: {e}")
            return {
                'error': str(e),
                'success': False
            }