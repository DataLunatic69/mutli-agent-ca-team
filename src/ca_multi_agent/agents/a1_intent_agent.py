import re
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import logging

from .base_agent import BaseAgent
from ..services.document_ingestion import document_ingestion_service

logger = logging.getLogger(__name__)

class IntentAgent(BaseAgent):
    def __init__(self):
        super().__init__("A1_Intent_Classification")
        self.intent_patterns = {
            'upload_docs': [
                r'upload', r'scan', r'process.*document', r'ingest', 
                r'attach.*file', r'send.*document'
            ],
            'post_entries': [
                r'post.*entry', r'create.*voucher', r'journal.*entry',
                r'book.*transaction', r'ledger.*entry', r'accounting.*entry'
            ],
            'reconcile': [
                r'reconcile', r'bank.*statement', r'match.*transaction',
                r'bank.*reco', r'statement.*matching', r'compare.*bank'
            ],
            'tax_gst': [
                r'gst', r'goods.*service.*tax', r'gstr', r'gstr1', r'gstr3b',
                r'gst.*return', r'gst.*filing', r'gst.*calculation'
            ],
            'tax_it': [
                r'income.*tax', r'itr', r'tds', r'tax.*return', r'income.*tax.*return',
                r'advance.*tax', r'self.*assessment', r'tax.*calculation'
            ],
            'compliance': [
                r'compliance', r'deadline', r'due.*date', r'filing.*date',
                r'roc', r'mca', r'compliance.*calendar', r'reminder'
            ],
            'report': [
                r'report', r'financial.*statement', r'profit.*loss', 
                r'balance.*sheet', r'cash.*flow', r'financial.*report',
                r'statement', r'mis', r'dashboard'
            ],
            'advisory': [
                r'advice', r'advisory', r'consult', r'question', r'help',
                r'guidance', r'suggest', r'recommend', r'what.*should', 
                r'how.*to', r'can.*i'
            ]
        }
        
        self.entity_patterns = {
            'period': r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4}|\d{1,2}[-/]\d{4}',
            'financial_year': r'fy\s*\d{2}-\d{2}|financial year\s*\d{4}-\d{2}',
            'amount': r'₹\s*\d+|\d+\s*(rs|rupees|inr)',
            'gstin': r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}',
            'pan': r'[A-Z]{5}\d{4}[A-Z]{1}',
            'account_number': r'account\s*no\.?\s*[\dX-]+',
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data.get('message', '').lower()
        attachments = input_data.get('attachments', [])
        context = input_data.get('context', {})
        
        # Classify intent
        intent, confidence = self._classify_intent(message, attachments)
        
        # Extract entities
        entities = self._extract_entities(message)
        
        # Determine next steps
        next_agent = self._determine_next_agent(intent, entities, attachments)
        
        return {
            'intent': intent,
            'confidence': confidence,
            'entities': entities,
            'next_agent': next_agent,
            'suggested_actions': self._get_suggested_actions(intent, entities),
            'timestamp': datetime.now().isoformat()
        }

    def _classify_intent(self, message: str, attachments: List) -> tuple:
        """Classify user intent based on message and attachments"""
        if attachments:
            return 'upload_docs', 0.95
        
        if not message.strip():
            return 'advisory', 0.5
        
        best_intent = 'advisory'
        best_score = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            score = self._calculate_intent_score(message, patterns)
            if score > best_score:
                best_score = score
                best_intent = intent
        
        return best_intent, best_score

    def _calculate_intent_score(self, message: str, patterns: List[str]) -> float:
        """Calculate intent matching score"""
        score = 0.0
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                score += 0.2  # Each matching pattern adds to score
        return min(score, 1.0)  # Cap at 1.0

    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract entities from message"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches[0] if len(matches) == 1 else matches
        
        # Extract date references
        date_entities = self._extract_date_entities(message)
        if date_entities:
            entities['dates'] = date_entities
        
        return entities

    def _extract_date_entities(self, message: str) -> List[str]:
        """Extract date-related entities"""
        date_patterns = [
            r'today|now|current',
            r'yesterday',
            r'tomorrow',
            r'this\s*month',
            r'last\s*month',
            r'next\s*month',
            r'this\s*quarter',
            r'last\s*quarter',
            r'this\s*year',
            r'last\s*year',
        ]
        
        dates = []
        for pattern in date_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                dates.append(pattern.replace('\\s*', ' '))
        
        return dates

    def _determine_next_agent(self, intent: str, entities: Dict, attachments: List) -> str:
        """Determine which agent should handle this request next"""
        agent_mapping = {
            'upload_docs': 'A2_Document_Ingestion',
            'post_entries': 'A3_Ledger_Posting',
            'reconcile': 'A5_Reconciliation',
            'tax_gst': 'A6_GST_Agent',
            'tax_it': 'A7_Income_Tax_Agent',
            'compliance': 'A8_Compliance_Calendar',
            'report': 'A9_Reporting_Analytics',
            'advisory': 'A10_Advisory_Q&A'
        }
        
        return agent_mapping.get(intent, 'A10_Advisory_Q&A')

    def _get_suggested_actions(self, intent: str, entities: Dict) -> List[str]:
        """Get suggested actions based on intent"""
        actions = {
            'upload_docs': ['Process documents', 'Extract transactions'],
            'post_entries': ['Create vouchers', 'Map to chart of accounts'],
            'reconcile': ['Match bank transactions', 'Identify exceptions'],
            'tax_gst': ['Calculate GST liability', 'Prepare GSTR-1'],
            'tax_it': ['Compute income tax', 'Generate ITR'],
            'compliance': ['Check deadlines', 'Create reminders'],
            'report': ['Generate financial statements', 'Create dashboards'],
            'advisory': ['Provide guidance', 'Answer questions']
        }
        
        return actions.get(intent, ['Provide assistance'])

# Agent instance
intent_agent = IntentAgent()