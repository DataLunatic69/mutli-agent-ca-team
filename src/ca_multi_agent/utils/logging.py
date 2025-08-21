import logging
import logging.config
import json
from datetime import datetime
from typing import Dict, Any
import uuid

def setup_logging():
    """Setup structured logging configuration"""
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'fmt': '%(asctime)s %(name)s %(levelname)s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'standard'
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': 'logs/ca_multi_agent.log',
                'formatter': 'standard'
            },
            'json_file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': 'logs/structured.log',
                'formatter': 'json'
            }
        },
        'loggers': {
            '': {
                'handlers': ['console', 'file', 'json_file'],
                'level': 'INFO',
                'propagate': True
            },
            'agent': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False
            },
            'sqlalchemy': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False
            }
        }
    }
    
    # Create logs directory
    import os
    os.makedirs('logs', exist_ok=True)
    
    logging.config.dictConfig(logging_config)

class AgentLogger:
    """Custom logger for agent operations with structured logging"""
    
    def __init__(self, agent_name: str):
        self.logger = logging.getLogger(f'agent.{agent_name}')
        self.agent_name = agent_name
        self.session_id = str(uuid.uuid4())
    
    def log_execution_start(self, input_data: Dict):
        """Log agent execution start"""
        self.logger.info(
            "Agent execution started",
            extra={
                'agent': self.agent_name,
                'session_id': self.session_id,
                'input': input_data,
                'timestamp': datetime.now().isoformat(),
                'event': 'execution_start'
            }
        )
    
    def log_execution_end(self, result: Dict, execution_time: float):
        """Log agent execution completion"""
        self.logger.info(
            "Agent execution completed",
            extra={
                'agent': self.agent_name,
                'session_id': self.session_id,
                'result': result,
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat(),
                'event': 'execution_end'
            }
        )
    
    def log_error(self, error: Exception, context: Dict = None):
        """Log agent error"""
        self.logger.error(
            "Agent execution failed",
            extra={
                'agent': self.agent_name,
                'session_id': self.session_id,
                'error': str(error),
                'error_type': type(error).__name__,
                'context': context or {},
                'timestamp': datetime.now().isoformat(),
                'event': 'execution_error'
            }
        )
    
    def log_metric(self, metric_name: str, value: float, tags: Dict = None):
        """Log performance metric"""
        self.logger.info(
            "Agent metric",
            extra={
                'agent': self.agent_name,
                'session_id': self.session_id,
                'metric_name': metric_name,
                'metric_value': value,
                'tags': tags or {},
                'timestamp': datetime.now().isoformat(),
                'event': 'metric'
            }
        )

def get_agent_logger(agent_name: str) -> AgentLogger:
    """Get a configured agent logger"""
    return AgentLogger(agent_name)