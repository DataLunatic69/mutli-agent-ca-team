from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional, Union
import uuid
from datetime import datetime
from enum import Enum

class AgentStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class WorkflowState(BaseModel):
    # Core identifiers
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: Optional[uuid.UUID] = None
    org_id: uuid.UUID
    conversation_id: Optional[uuid.UUID] = None
    
    # Input data
    message: str = ""
    attachments: List[uuid.UUID] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Agent processing
    intent: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    current_agent: Optional[str] = None
    agent_status: Dict[str, AgentStatus] = Field(default_factory=dict)
    
    # Results and artifacts
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    next_actions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    timeout_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
        use_enum_values = True
    
    @validator('updated_at', pre=True, always=True)
    def update_timestamp(cls, v):
        return datetime.now()
    
    def update(self, **kwargs):
        """Update state with new values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def add_artifact(self, artifact_type: str, data: Any, metadata: Optional[Dict] = None):
        """Add an artifact to the state"""
        self.artifacts.append({
            'type': artifact_type,
            'data': data,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'agent': self.current_agent
        })
    
    def add_error(self, error: Exception, context: Optional[Dict] = None):
        """Add an error to the state"""
        self.errors.append({
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'timestamp': datetime.now().isoformat(),
            'agent': self.current_agent
        })
    
    def set_agent_status(self, agent_name: str, status: AgentStatus):
        """Set status for a specific agent"""
        self.agent_status[agent_name] = status
    
    def get_artifact(self, artifact_type: str) -> Optional[Dict]:
        """Get the most recent artifact of a specific type"""
        for artifact in reversed(self.artifacts):
            if artifact['type'] == artifact_type:
                return artifact
        return None
    
    def get_artifacts_by_type(self, artifact_type: str) -> List[Dict]:
        """Get all artifacts of a specific type"""
        return [art for art in self.artifacts if art['type'] == artifact_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            'session_id': str(self.session_id),
            'org_id': str(self.org_id),
            'intent': self.intent,
            'current_agent': self.current_agent,
            'artifact_count': len(self.artifacts),
            'error_count': len(self.errors),
            'status': 'completed' if not self.errors else 'failed'
        }