from typing import Dict, Any, List, Optional, Callable
import uuid
from datetime import datetime
import logging
import asyncio
from langgraph.graph import StateGraph, END
from langgraph.graph.state import StateGraph

from .base_agent import BaseAgent
from ..workflows.state import WorkflowState
from ..utils.logging import get_agent_logger

logger = logging.getLogger(__name__)

class SupervisorAgent(BaseAgent):
    def __init__(self, db_session):
        super().__init__("Supervisor")
        self.db = db_session
        self.agent_logger = get_agent_logger("Supervisor")
        self.workflow_graph = self._build_workflow_graph()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the supervisor workflow"""
        try:
            # Initialize workflow state
            initial_state = WorkflowState(
                org_id=input_data.get('org_id'),
                message=input_data.get('message', ''),
                attachments=input_data.get('attachments', []),
                user_id=input_data.get('user_id')
            )
            
            self.agent_logger.log_execution_start(input_data)
            start_time = datetime.now()
            
            # Execute the workflow graph
            final_state = await self.workflow_graph.arun(initial_state)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.agent_logger.log_execution_end(final_state.dict(), execution_time)
            
            return self._format_final_response(final_state)
            
        except Exception as e:
            self.agent_logger.log_error(e, input_data)
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _build_workflow_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(state_schema=WorkflowState)
        
        # Define nodes (each agent as a node)
        workflow.add_node("intent_classification", self._run_intent_agent)
        workflow.add_node("document_ingestion", self._run_document_agent)
        workflow.add_node("ledger_posting", self._run_ledger_agent)
        workflow.add_node("reconciliation", self._run_reconciliation_agent)
        workflow.add_node("gst_processing", self._run_gst_agent)
        workflow.add_node("tax_processing", self._run_tax_agent)
        workflow.add_node("compliance_check", self._run_compliance_agent)
        workflow.add_node("report_generation", self._run_reporting_agent)
        workflow.add_node("advisory", self._run_advisory_agent)
        workflow.add_node("anomaly_detection", self._run_anomaly_agent)
        workflow.add_node("report_formatting", self._run_formatter_agent)
        
        # Set entry point
        workflow.set_entry_point("intent_classification")
        
        # Define conditional edges based on intent
        workflow.add_conditional_edges(
            "intent_classification",
            self._route_based_on_intent,
            {
                "upload_docs": "document_ingestion",
                "post_entries": "ledger_posting", 
                "reconcile": "reconciliation",
                "tax_gst": "gst_processing",
                "tax_it": "tax_processing",
                "compliance": "compliance_check",
                "report": "report_generation",
                "advisory": "advisory",
                "anomaly": "anomaly_detection",
                "format": "report_formatting"
            }
        )
        
        # Define edges for document processing flow
        workflow.add_edge("document_ingestion", "ledger_posting")
        workflow.add_conditional_edges(
            "ledger_posting",
            self._route_after_posting,
            {
                "reconcile": "reconciliation",
                "tax": "gst_processing",
                "report": "report_generation",
                "complete": END
            }
        )
        
        # Define edges for reconciliation flow
        workflow.add_conditional_edges(
            "reconciliation",
            self._route_after_reconciliation,
            {
                "adjust": "ledger_posting",
                "complete": END
            }
        )
        
        # Define edges for tax processing flow
        workflow.add_edge("gst_processing", "report_formatting")
        workflow.add_edge("tax_processing", "report_formatting")
        workflow.add_edge("report_formatting", END)
        
        # Define edges for reporting flow
        workflow.add_edge("report_generation", "report_formatting")
        
        return workflow.compile()

    async def _run_intent_agent(self, state: WorkflowState) -> WorkflowState:
        """Run intent classification agent"""
        from . import get_agent
        agent = get_agent("A1_Intent_Classification")
        
        result = await agent.execute({
            'message': state.message,
            'attachments': state.attachments,
            'org_id': str(state.org_id)
        })
        
        state.update(
            intent=result['intent'],
            entities=result.get('entities', {}),
            current_agent="A1_Intent_Classification"
        )
        
        state.artifacts.append({
            'type': 'intent_result',
            'data': result,
            'timestamp': datetime.now().isoformat()
        })
        
        return state

    async def _run_document_agent(self, state: WorkflowState) -> WorkflowState:
        """Run document ingestion agent"""
        from . import get_agent
        agent = get_agent("A2_Document_Ingestion")
        
        result = await agent.execute({
            'attachments': state.attachments,
            'org_id': str(state.org_id)
        })
        
        state.update(
            current_agent="A2_Document_Ingestion",
            artifacts=state.artifacts + [{
                'type': 'document_ingestion_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_ledger_agent(self, state: WorkflowState) -> WorkflowState:
        """Run ledger posting agent"""
        from . import get_agent
        agent = get_agent("A3_Ledger_Posting", self.db)
        
        # Get transactions from previous artifacts
        transactions = self._extract_transactions(state.artifacts)
        
        result = await agent.execute({
            'org_id': str(state.org_id),
            'transactions': transactions,
            'doc_id': state.attachments[0] if state.attachments else None
        })
        
        state.update(
            current_agent="A3_Ledger_Posting",
            artifacts=state.artifacts + [{
                'type': 'ledger_posting_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_reconciliation_agent(self, state: WorkflowState) -> WorkflowState:
        """Run reconciliation agent"""
        from . import get_agent
        agent = get_agent("A5_Reconciliation", self.db)
        
        # Extract period from entities or use default
        period = state.entities.get('period', self._get_default_period())
        
        result = await agent.execute({
            'org_id': str(state.org_id),
            'period': period,
            'bank_statement_id': state.attachments[0] if state.attachments else None
        })
        
        state.update(
            current_agent="A5_Reconciliation",
            artifacts=state.artifacts + [{
                'type': 'reconciliation_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_gst_agent(self, state: WorkflowState) -> WorkflowState:
        """Run GST agent"""
        from . import get_agent
        agent = get_agent("A6_GST_Agent", self.db)
        
        period = state.entities.get('period', self._get_default_period())
        gstin = state.entities.get('gstin') or self._get_org_gstin(state.org_id)
        
        result = await agent.execute({
            'org_id': str(state.org_id),
            'period': period,
            'gstin': gstin
        })
        
        state.update(
            current_agent="A6_GST_Agent",
            artifacts=state.artifacts + [{
                'type': 'gst_processing_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_tax_agent(self, state: WorkflowState) -> WorkflowState:
        """Run income tax agent"""
        from . import get_agent
        agent = get_agent("A7_Income_Tax_Agent", self.db)
        
        fy = state.entities.get('financial_year', '2024-25')
        pan = state.entities.get('pan') or self._get_org_pan(state.org_id)
        
        result = await agent.execute({
            'org_id': str(state.org_id),
            'fy': fy,
            'pan': pan
        })
        
        state.update(
            current_agent="A7_Income_Tax_Agent",
            artifacts=state.artifacts + [{
                'type': 'tax_processing_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_compliance_agent(self, state: WorkflowState) -> WorkflowState:
        """Run compliance agent"""
        from . import get_agent
        agent = get_agent("A8_Compliance_Calendar", self.db)
        
        result = await agent.execute({
            'org_id': str(state.org_id),
            'entity_type': state.entities.get('entity_type', 'company'),
            'state': state.entities.get('state', 'MH'),
            'fy': state.entities.get('financial_year', '2024-25')
        })
        
        state.update(
            current_agent="A8_Compliance_Calendar",
            artifacts=state.artifacts + [{
                'type': 'compliance_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_reporting_agent(self, state: WorkflowState) -> WorkflowState:
        """Run reporting agent"""
        from . import get_agent
        agent = get_agent("A9_Reporting_Analytics", self.db)
        
        result = await agent.execute({
            'org_id': str(state.org_id),
            'period': state.entities.get('period', self._get_default_period()),
            'report_types': state.entities.get('report_types', ['pnl', 'bs'])
        })
        
        state.update(
            current_agent="A9_Reporting_Analytics",
            artifacts=state.artifacts + [{
                'type': 'reporting_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_advisory_agent(self, state: WorkflowState) -> WorkflowState:
        """Run advisory agent"""
        from . import get_agent
        agent = get_agent("A10_Advisory_Q&A", self.db)
        
        result = await agent.execute({
            'org_id': str(state.org_id),
            'question': state.message,
            'context_refs': self._extract_context_references(state.artifacts)
        })
        
        state.update(
            current_agent="A10_Advisory_Q&A",
            artifacts=state.artifacts + [{
                'type': 'advisory_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_anomaly_agent(self, state: WorkflowState) -> WorkflowState:
        """Run anomaly detection agent"""
        from . import get_agent
        agent = get_agent("A11_Anomaly_Detection", self.db)
        
        result = await agent.execute({
            'org_id': str(state.org_id),
            'period': state.entities.get('period', self._get_default_period())
        })
        
        state.update(
            current_agent="A11_Anomaly_Detection",
            artifacts=state.artifacts + [{
                'type': 'anomaly_detection_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    async def _run_formatter_agent(self, state: WorkflowState) -> WorkflowState:
        """Run report formatter agent"""
        from . import get_agent
        agent = get_agent("A12_Report_Formatter")
        
        # Extract report components from artifacts
        components = self._extract_report_components(state.artifacts)
        
        result = await agent.execute({
            'components': components,
            'format': state.entities.get('format', 'pdf'),
            'title': state.entities.get('title', 'Financial Report')
        })
        
        state.update(
            current_agent="A12_Report_Formatter",
            artifacts=state.artifacts + [{
                'type': 'formatting_result',
                'data': result,
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        return state

    def _route_based_on_intent(self, state: WorkflowState) -> str:
        """Route to next node based on intent"""
        return state.intent or "advisory"

    def _route_after_posting(self, state: WorkflowState) -> str:
        """Route after ledger posting"""
        # Check if there are bank statements to reconcile
        if any('bank' in artifact.get('type', '') for artifact in state.artifacts):
            return "reconcile"
        return "complete"

    def _route_after_reconciliation(self, state: WorkflowState) -> str:
        """Route after reconciliation"""
        # Check if adjustments are needed
        last_artifact = state.artifacts[-1] if state.artifacts else {}
        if last_artifact.get('type') == 'reconciliation_result':
            if last_artifact.get('data', {}).get('adjustments'):
                return "adjust"
        return "complete"

    def _extract_transactions(self, artifacts: List[Dict]) -> List[Dict]:
        """Extract transactions from document ingestion artifacts"""
        for artifact in artifacts:
            if artifact.get('type') == 'document_ingestion_result':
                return artifact.get('data', {}).get('extracted_data', {}).get('transactions', [])
        return []

    def _extract_context_references(self, artifacts: List[Dict]) -> List[Dict]:
        """Extract context references from artifacts"""
        references = []
        for artifact in artifacts:
            if artifact.get('type') in ['ledger_posting_result', 'reconciliation_result']:
                references.append({
                    'type': artifact['type'],
                    'timestamp': artifact['timestamp'],
                    'summary': f"Processed {len(artifact.get('data', {}).get('processed_entries', []))} entries"
                })
        return references

    def _extract_report_components(self, artifacts: List[Dict]) -> List[Dict]:
        """Extract report components from various agent results"""
        components = []
        
        for artifact in artifacts:
            if artifact['type'] == 'reporting_result':
                components.extend(artifact['data'].get('reports', {}).values())
            elif artifact['type'] in ['gst_processing_result', 'tax_processing_result']:
                components.append({
                    'type': 'summary',
                    'title': f"{artifact['type'].replace('_result', '').title()} Summary",
                    'data': artifact['data']
                })
        
        return components

    def _get_default_period(self) -> str:
        """Get default period (current month)"""
        today = datetime.now()
        return today.strftime("%m-%Y")

    def _get_org_gstin(self, org_id: uuid.UUID) -> str:
        """Get organization's GSTIN from database"""
        # This would query the database
        return "27ABCDE1234F1Z5"  # Example

    def _get_org_pan(self, org_id: uuid.UUID) -> str:
        """Get organization's PAN from database"""
        # This would query the database
        return "ABCDE1234F"  # Example

    def _format_final_response(self, state: WorkflowState) -> Dict[str, Any]:
        """Format the final response from workflow state"""
        # Extract the main result from the last artifact
        last_artifact = state.artifacts[-1] if state.artifacts else {}
        
        response = {
            'success': True,
            'session_id': str(state.session_id),
            'org_id': str(state.org_id),
            'result': last_artifact.get('data', {}),
            'artifacts': [{
                'type': art['type'],
                'timestamp': art['timestamp']
            } for art in state.artifacts],
            'agent_route': self._get_agent_route(state.artifacts),
            'processing_time': datetime.now().isoformat()
        }
        
        # Add download URL if report was generated
        if last_artifact.get('type') == 'formatting_result':
            response['download_url'] = last_artifact['data'].get('download_url')
        
        return response

    def _get_agent_route(self, artifacts: List[Dict]) -> List[str]:
        """Get the route of agents that were executed"""
        return [art['type'].replace('_result', '') for art in artifacts if 'result' in art['type']]

# Supervisor instance
supervisor_agent = None

def get_supervisor(db_session) -> SupervisorAgent:
    """Get supervisor agent instance"""
    global supervisor_agent
    if supervisor_agent is None:
        supervisor_agent = SupervisorAgent(db_session)
    return supervisor_agent