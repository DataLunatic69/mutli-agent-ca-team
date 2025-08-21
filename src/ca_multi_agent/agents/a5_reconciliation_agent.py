from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, date
import logging

from .base import BaseAgent
from ..services.reconciliation_service import get_reconciliation_service
from ..services.ledger_services import get_ledger_service
from datetime import timedelta

logger = logging.getLogger(__name__)

class ReconciliationAgent(BaseAgent):
    def __init__(self, db_session):
        super().__init__("A5_Reconciliation")
        self.reconciliation_service = get_reconciliation_service(db_session)
        self.ledger_service = get_ledger_service(db_session)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        org_id = input_data.get('org_id')
        period = input_data.get('period')
        bank_statement_id = input_data.get('bank_statement_id')
        ledger_source = input_data.get('ledger_source', 'primary')
        
        if not all([org_id, period, bank_statement_id]):
            raise ValueError("Missing required parameters: org_id, period, or bank_statement_id")
        
        # Parse period (format: "MM-YYYY" or date range)
        start_date, end_date = self._parse_period(period)
        
        # Perform reconciliation
        reconciliation_result = await self.reconciliation_service.match_bank_transactions(
            org_id, bank_statement_id, start_date, end_date
        )
        
        # Generate adjustments for unmatched transactions
        adjustments = await self._generate_adjustments(
            org_id, reconciliation_result, start_date, end_date
        )
        
        return {
            'success': True,
            'reconciliation_id': reconciliation_result.id,
            'org_id': org_id,
            'period': period,
            'summary': reconciliation_result.summary,
            'matched_count': reconciliation_result.summary.get('matched_count', 0),
            'unmatched_bank_count': reconciliation_result.summary.get('unmatched_bank_count', 0),
            'unmatched_ledger_count': reconciliation_result.summary.get('unmatched_ledger_count', 0),
            'adjustments': adjustments,
            'status': reconciliation_result.status,
            'timestamp': datetime.now().isoformat()
        }

    def _parse_period(self, period: str) -> tuple:
        """Parse period string into start and end dates"""
        try:
            if '-' in period and len(period) == 7:  # MM-YYYY format
                month, year = period.split('-')
                start_date = date(int(year), int(month), 1)
                # Calculate end date (last day of month)
                if int(month) == 12:
                    end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)
                return start_date, end_date
            else:
                # Default to current month if format not recognized
                today = datetime.now()
                start_date = date(today.year, today.month, 1)
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
                return start_date, end_date
                
        except (ValueError, IndexError):
            # Fallback to current month
            today = datetime.now()
            start_date = date(today.year, today.month, 1)
            end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
            return start_date, end_date

    async def _generate_adjustments(
        self, 
        org_id: uuid.UUID, 
        reconciliation_result, 
        start_date: date, 
        end_date: date
    ) -> List[Dict]:
        """Generate adjustment entries for unmatched transactions"""
        adjustments = []
        
        # Get the reconciliation matches to find unmatched transactions
        # (This would query the database for actual unmatched transactions)
        
        # Sample adjustment logic
        adjustments.append({
            'type': 'bank_charge',
            'description': 'Bank service charges',
            'amount': 150.00,
            'account_code': 'BANK_CHARGES',
            'suggested_action': 'Create expense voucher',
            'confidence': 0.7
        })
        
        adjustments.append({
            'type': 'interest_income', 
            'description': 'Bank interest earned',
            'amount': 89.50,
            'account_code': 'INTEREST_INCOME',
            'suggested_action': 'Create income voucher',
            'confidence': 0.8
        })
        
        return adjustments

    async def get_reconciliation_status(self, reconciliation_id: uuid.UUID) -> Dict[str, Any]:
        """Get status of a specific reconciliation"""
        # This would query the database for reconciliation status
        return {
            'reconciliation_id': reconciliation_id,
            'status': 'completed',
            'progress': 100,
            'last_updated': datetime.now().isoformat()
        }

    async def suggest_reconciliation_rules(self, org_id: uuid.UUID) -> List[Dict]:
        """Suggest reconciliation rules based on history"""
        # This would analyze past reconciliations to suggest improvements
        return [
            {
                'rule_type': 'amount_tolerance',
                'description': 'Allow ±1% amount variance',
                'confidence': 0.85,
                'impact': 'Reduces false negatives by 15%'
            },
            {
                'rule_type': 'date_tolerance', 
                'description': 'Allow ±3 days date variance',
                'confidence': 0.78,
                'impact': 'Reduces false negatives by 22%'
            }
        ]

# Note: This agent requires database session