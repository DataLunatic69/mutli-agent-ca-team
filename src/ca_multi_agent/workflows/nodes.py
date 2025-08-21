from typing import Dict, Any, Callable
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.graph.state import StateGraph

from .state import WorkflowState
from ..agents import get_agent
from ..utils.logging import get_agent_logger

class WorkflowNodes:
    def __init__(self, db_session):
        self.db = db_session
        self.logger = get_agent_logger("WorkflowNodes")
    
    def create_agent_node(self, agent_name: str) -> Callable:
        """Create a node for a specific agent"""
        async def agent_node(state: WorkflowState) -> WorkflowState:
            try:
                self.logger.log_execution_start({
                    'agent': agent_name,
                    'session_id': str(state.session_id)
                })
                
                agent = get_agent(agent_name, self.db)
                
                # Prepare input data for the agent
                input_data = self._prepare_agent_input(agent_name, state)
                
                # Execute the agent
                result = await agent.execute(input_data)
                
                # Update state with results
                state.add_artifact(f"{agent_name}_result", result)
                state.set_agent_status(agent_name, "completed")
                state.current_agent = agent_name
                
                self.logger.log_execution_end({
                    'agent': agent_name,
                    'result': result.get('success', False)
                })
                
                return state
                
            except Exception as e:
                self.logger.log_error(e, {
                    'agent': agent_name,
                    'session_id': str(state.session_id)
                })
                
                state.add_error(e, {'agent': agent_name})
                state.set_agent_status(agent_name, "failed")
                
                return state
        
        return agent_node
    
    def create_conditional_node(self, condition_name: str) -> Callable:
        """Create a conditional routing node"""
        async def conditional_node(state: WorkflowState) -> str:
            if condition_name == "route_intent":
                return state.intent or "advisory"
            
            elif condition_name == "route_after_ingestion":
                if state.attachments and state.intent == "upload_docs":
                    return "ledger_posting"
                return "advisory"
            
            elif condition_name == "route_after_posting":
                # Check if reconciliation is needed
                last_artifact = state.get_artifact("A3_Ledger_Posting_result")
                if last_artifact and last_artifact.get('data', {}).get('has_bank_transactions'):
                    return "reconciliation"
                return "complete"
            
            return "advisory"
        
        return conditional_node
    
    def create_tool_node(self) -> ToolNode:
        """Create a tool node for LangGraph tools"""
        # This would integrate with LangGraph's ToolNode
        # For now, return a simple implementation
        return ToolNode([])  # Empty tools for now
    
    def _prepare_agent_input(self, agent_name: str, state: WorkflowState) -> Dict[str, Any]:
        """Prepare input data for a specific agent"""
        base_input = {
            'org_id': str(state.org_id),
            'session_id': str(state.session_id)
        }
        
        if agent_name == "A1_Intent_Classification":
            base_input.update({
                'message': state.message,
                'attachments': state.attachments
            })
        
        elif agent_name == "A2_Document_Ingestion":
            base_input.update({
                'attachments': state.attachments
            })
        
        elif agent_name == "A3_Ledger_Posting":
            # Extract transactions from previous artifacts
            doc_artifact = state.get_artifact("A2_Document_Ingestion_result")
            if doc_artifact:
                base_input['transactions'] = doc_artifact.get('data', {}).get('extracted_data', [])
        
        elif agent_name in ["A6_GST_Agent", "A7_Income_Tax_Agent"]:
            # Extract period and identifiers from entities
            base_input.update({
                'period': state.entities.get('period'),
                'fy': state.entities.get('financial_year')
            })
        
        return base_input
    
    def create_error_handler_node(self) -> Callable:
        """Create a node for error handling"""
        async def error_handler_node(state: WorkflowState) -> WorkflowState:
            if state.errors:
                last_error = state.errors[-1]
                self.logger.log_error(Exception(last_error['error_message']), {
                    'session_id': str(state.session_id),
                    'agent': last_error.get('agent')
                })
            
            return state
        
        return error_handler_node