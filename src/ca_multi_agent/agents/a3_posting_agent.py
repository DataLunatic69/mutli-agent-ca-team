from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import logging

from .base import BaseAgent
from ..services.ledger_services import get_ledger_service
from ..services.document_ingestion import document_ingestion_service

logger = logging.getLogger(__name__)

class LedgerPostingAgent(BaseAgent):
    def __init__(self, db_session):
        super().__init__("A3_Ledger_Posting")
        self.ledger_service = get_ledger_service(db_session)
        self.mapping_rules = self._load_mapping_rules()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        org_id = input_data.get('org_id')
        transactions = input_data.get('transactions', [])
        extracted_data = input_data.get('extracted_data', {})
        doc_id = input_data.get('doc_id')
        
        if not org_id:
            raise ValueError("Organization ID is required")
        
        # Process transactions
        results = await self._process_transactions(org_id, transactions, extracted_data, doc_id)
        
        return {
            'success': True,
            'org_id': org_id,
            'processed_count': len(results['posted']),
            'unmapped_count': len(results['unmapped']),
            'voucher_batch_id': results.get('voucher_batch_id'),
            'posted_entries': results['posted'],
            'unmapped_transactions': results['unmapped'],
            'rules_learned': results.get('rules_learned', []),
            'timestamp': datetime.now().isoformat()
        }

    async def _process_transactions(
        self, 
        org_id: uuid.UUID, 
        transactions: List[Dict], 
        extracted_data: Dict,
        doc_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Process a batch of transactions"""
        posted_entries = []
        unmapped_transactions = []
        learned_rules = []
        
        for transaction in transactions:
            try:
                result = await self._process_single_transaction(org_id, transaction, extracted_data, doc_id)
                if result['success']:
                    posted_entries.append(result)
                    # Learn from successful mapping
                    if result.get('learned_rule'):
                        learned_rules.append(result['learned_rule'])
                else:
                    unmapped_transactions.append({
                        'transaction': transaction,
                        'error': result.get('error'),
                        'suggestions': result.get('suggestions', [])
                    })
                    
            except Exception as e:
                logger.error(f"Error processing transaction: {e}")
                unmapped_transactions.append({
                    'transaction': transaction,
                    'error': str(e)
                })
        
        return {
            'posted': posted_entries,
            'unmapped': unmapped_transactions,
            'rules_learned': learned_rules
        }

    async def _process_single_transaction(
        self,
        org_id: uuid.UUID,
        transaction: Dict[str, Any],
        extracted_data: Dict,
        doc_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Process a single transaction"""
        description = transaction.get('description', '').lower()
        amount = transaction.get('amount', 0)
        txn_type = transaction.get('type', 'debit').lower()
        date = transaction.get('date', datetime.now().date())
        party = transaction.get('party')
        
        # Map to chart of accounts
        account_code, debit_amount, credit_amount = await self.ledger_service.map_transaction_to_coa(
            org_id, description, amount, txn_type, party
        )
        
        # Create voucher entry
        voucher_data = {
            'account_code': account_code,
            'debit': debit_amount,
            'credit': credit_amount,
            'description': description,
            'party': party,
            'tags': {
                'source': 'agent',
                'document_reference': str(doc_id) if doc_id else None,
                'auto_mapped': True
            }
        }
        
        # Create voucher (batch similar transactions)
        voucher = await self.ledger_service.create_voucher(
            org_id=org_id,
            voucher_date=date,
            voucher_type=self._determine_voucher_type(txn_type, account_code),
            entries=[voucher_data],
            narration=f"Auto-posted: {description}",
            source="A3_Agent",
            doc_id=doc_id
        )
        
        # Check if this mapping can be learned
        learned_rule = self._learn_mapping(description, account_code, amount, txn_type)
        
        return {
            'success': True,
            'voucher_id': voucher.id,
            'account_code': account_code,
            'debit': debit_amount,
            'credit': credit_amount,
            'learned_rule': learned_rule,
            'transaction_date': date.isoformat() if hasattr(date, 'isoformat') else date
        }

    def _determine_voucher_type(self, transaction_type: str, account_code: str) -> str:
        """Determine appropriate voucher type"""
        if transaction_type == 'debit':
            if account_code.startswith('BANK_') or account_code.startswith('CASH_'):
                return 'Payment'
            else:
                return 'Journal'
        else:  # credit
            if account_code.startswith('BANK_') or account_code.startswith('CASH_'):
                return 'Receipt'
            else:
                return 'Journal'

    def _learn_mapping(self, description: str, account_code: str, amount: float, txn_type: str) -> Optional[Dict]:
        """Learn from successful mappings to improve future accuracy"""
        description_keywords = description.lower().split()
        
        # Simple learning: remember this description -> account mapping
        rule = {
            'keywords': description_keywords[:3],  # First 3 keywords
            'account_code': account_code,
            'transaction_type': txn_type,
            'amount_range': (amount * 0.5, amount * 1.5),  # ±50% range
            'confidence': 0.8,
            'learned_at': datetime.now().isoformat()
        }
        
        # Store the rule (in real implementation, this would go to database)
        self.mapping_rules.append(rule)
        return rule

    def _load_mapping_rules(self) -> List[Dict]:
        """Load existing mapping rules"""
        # In production, this would load from database
        return [
            {
                'keywords': ['salary', 'payroll'],
                'account_code': 'SALARIES',
                'transaction_type': 'debit',
                'confidence': 0.9
            },
            {
                'keywords': ['rent', 'lease'],
                'account_code': 'RENT',
                'transaction_type': 'debit', 
                'confidence': 0.85
            }
        ]

    async def get_mapping_suggestions(self, description: str, amount: float, txn_type: str) -> List[Dict]:
        """Get suggestions for mapping unknown transactions"""
        suggestions = []
        
        # Check against learned rules
        for rule in self.mapping_rules:
            keyword_match = any(keyword in description.lower() for keyword in rule['keywords'])
            type_match = rule['transaction_type'] == txn_type
            
            if keyword_match and type_match:
                suggestions.append({
                    'account_code': rule['account_code'],
                    'confidence': rule['confidence'],
                    'reason': f"Matches learned pattern: {rule['keywords']}"
                })
        
        return suggestions

# Note: This agent requires database session, so we'll create it when needed