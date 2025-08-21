from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
from sqlalchemy.orm import Session

from ....agents import get_supervisor
from ....api.dependencies import get_db
from ....workflows.state import WorkflowState

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    org_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    session_id: Optional[uuid.UUID] = None
    attachments: List[uuid.UUID] = []
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    success: bool
    reply: str
    session_id: uuid.UUID
    actions: List[dict] = []
    artifacts: List[dict] = []
    download_url: Optional[str] = None
    agent_route: List[str] = []
    processing_time: str

@router.post("")
async def chat_endpoint(
    request: ChatRequest, 
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint that routes to appropriate agents via supervisor
    """
    try:
        # Get supervisor agent
        supervisor = get_supervisor(db)
        
        # Execute the workflow
        result = await supervisor.execute({
            'message': request.message,
            'org_id': request.org_id,
            'user_id': request.user_id,
            'session_id': request.session_id,
            'attachments': request.attachments,
            'context': request.context or {}
        })
        
        # Format the response
        response = await _format_chat_response(result, request.message)
        
        return ChatResponse(**response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

async def _format_chat_response(supervisor_result: Dict, original_message: str) -> Dict:
    """Format the supervisor result into a chat response"""
    result_data = supervisor_result.get('result', {})
    
    # Generate appropriate reply based on the result
    reply = _generate_reply(original_message, result_data)
    
    return {
        'success': supervisor_result.get('success', False),
        'reply': reply,
        'session_id': uuid.UUID(supervisor_result.get('session_id', uuid.uuid4())),
        'actions': result_data.get('next_actions', []),
        'artifacts': supervisor_result.get('artifacts', []),
        'download_url': supervisor_result.get('download_url'),
        'agent_route': supervisor_result.get('agent_route', []),
        'processing_time': supervisor_result.get('processing_time', '')
    }

def _generate_reply(original_message: str, result_data: Dict) -> str:
    """Generate a natural language reply based on the processing result"""
    message_lower = original_message.lower()
    
    if 'gst' in message_lower:
        return _format_gst_reply(result_data)
    elif 'tax' in message_lower or 'itr' in message_lower:
        return _format_tax_reply(result_data)
    elif 'report' in message_lower:
        return _format_report_reply(result_data)
    elif 'reconcile' in message_lower:
        return _format_reconciliation_reply(result_data)
    elif 'upload' in message_lower or 'document' in message_lower:
        return _format_upload_reply(result_data)
    else:
        return _format_general_reply(result_data)

def _format_gst_reply(result_data: Dict) -> str:
    """Format reply for GST-related queries"""
    liability = result_data.get('liability_summary', {})
    return f"""✅ GST processing completed.

Period: {liability.get('period', 'N/A')}
Output Tax Liability: ₹{liability.get('output_tax_liability', 0):,.2f}
Input Tax Credit: ₹{liability.get('input_tax_credit', 0):,.2f}
Net GST Payable: ₹{liability.get('net_gst_payable', 0):,.2f}

GSTR-1 and GSTR-3B returns have been prepared. You can download the reports."""

def _format_tax_reply(result_data: Dict) -> str:
    """Format reply for tax-related queries"""
    computation = result_data.get('tax_computation', {})
    return f"""✅ Income tax computation completed.

Taxable Income: ₹{computation.get('taxable_income', 0):,.2f}
Total Tax Liability: ₹{computation.get('total_tax', 0):,.2f}

ITR has been prepared. Please review the advance tax payment schedule."""

def _format_upload_reply(result_data: Dict) -> str:
    """Format reply for document uploads"""
    processed = result_data.get('processed_count', 0)
    return f"""✅ Document processing completed.

Successfully processed {processed} transactions. The entries have been posted to the ledger. 

Would you like to reconcile these transactions or generate a report?"""

def _format_reconciliation_reply(result_data: Dict) -> str:
    """Format reply for reconciliation"""
    summary = result_data.get('summary', {})
    return f"""✅ Bank reconciliation completed.

Matched: {summary.get('matched_count', 0)} transactions
Unmatched: {summary.get('unmatched_bank_count', 0)} bank transactions

Review the adjustments suggested for unmatched transactions."""

def _format_report_reply(result_data: Dict) -> str:
    """Format reply for reporting"""
    return """✅ Financial reports generated.

The reports include Profit & Loss statement, Balance Sheet, and Cash Flow statement. 
You can download the reports in PDF or Excel format."""

def _format_general_reply(result_data: Dict) -> str:
    """Format general reply"""
    return """✅ Request processed successfully.

I've completed the requested operation. You can review the results and download any generated reports."""