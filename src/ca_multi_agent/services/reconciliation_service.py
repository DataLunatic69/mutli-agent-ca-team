from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import date, timedelta
import logging
from difflib import SequenceMatcher
import numpy as np

from ..models.reconciliation import BankStatement, BankTransaction, Reconciliation, ReconciliationMatch
from ..models.accounting import LedgerEntry

logger = logging.getLogger(__name__)

class ReconciliationService:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def match_bank_transactions(
        self,
        org_id: uuid.UUID,
        bank_statement_id: uuid.UUID,
        period_start: date,
        period_end: date,
        matching_strategy: str = "amount_date_description"
    ) -> Reconciliation:
        """
        Match bank transactions with ledger entries
        """
        try:
            # Get bank transactions
            bank_transactions = self.db.query(BankTransaction).filter(
                BankTransaction.statement_id == bank_statement_id
            ).all()
            
            # Get ledger entries for the period
            ledger_entries = self.db.query(LedgerEntry).filter(
                LedgerEntry.org_id == org_id,
                LedgerEntry.date >= period_start,
                LedgerEntry.date <= period_end
            ).all()
            
            # Create reconciliation record
            reconciliation = Reconciliation(
                org_id=org_id,
                bank_statement_id=bank_statement_id,
                period_start=period_start,
                period_end=period_end,
                status="in_progress"
            )
            self.db.add(reconciliation)
            self.db.flush()
            
            matches = []
            unmatched_bank = []
            unmatched_ledger = ledger_entries.copy()
            
            # Match transactions based on strategy
            if matching_strategy == "amount_date_description":
                matches, unmatched_bank, unmatched_ledger = await self._match_amount_date_description(
                    bank_transactions, ledger_entries
                )
            
            # Save matches to database
            for match in matches:
                reconciliation_match = ReconciliationMatch(
                    reconciliation_id=reconciliation.id,
                    bank_transaction_id=match['bank_transaction'].id,
                    ledger_entry_id=match['ledger_entry'].id,
                    match_type=match['match_type'],
                    confidence=match['confidence']
                )
                self.db.add(reconciliation_match)
            
            # Update reconciliation status
            reconciliation.status = "completed"
            reconciliation.summary = {
                "total_bank_transactions": len(bank_transactions),
                "total_ledger_entries": len(ledger_entries),
                "matched_count": len(matches),
                "unmatched_bank_count": len(unmatched_bank),
                "unmatched_ledger_count": len(unmatched_ledger),
                "match_rate": len(matches) / len(bank_transactions) if bank_transactions else 0
            }
            
            self.db.commit()
            return reconciliation
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in reconciliation: {e}")
            raise
    
    async def _match_amount_date_description(
        self,
        bank_transactions: List[BankTransaction],
        ledger_entries: List[LedgerEntry]
    ) -> Tuple[List[Dict], List[BankTransaction], List[LedgerEntry]]:
        """
        Match using amount, date, and description similarity
        """
        matches = []
        unmatched_bank = bank_transactions.copy()
        unmatched_ledger = ledger_entries.copy()
        
        for bank_txn in bank_transactions:
            best_match = None
            best_score = 0
            
            for ledger_entry in ledger_entries:
                if ledger_entry in [m['ledger_entry'] for m in matches]:
                    continue  # Already matched
                
                # Calculate match score
                amount_score = self._calculate_amount_score(bank_txn, ledger_entry)
                date_score = self._calculate_date_score(bank_txn, ledger_entry)
                desc_score = self._calculate_description_score(bank_txn, ledger_entry)
                
                total_score = amount_score * 0.5 + date_score * 0.3 + desc_score * 0.2
                
                if total_score > best_score and total_score > 0.7:  # Threshold
                    best_score = total_score
                    best_match = ledger_entry
            
            if best_match:
                matches.append({
                    'bank_transaction': bank_txn,
                    'ledger_entry': best_match,
                    'match_type': 'exact' if best_score > 0.9 else 'partial',
                    'confidence': best_score
                })
                unmatched_bank.remove(bank_txn)
                unmatched_ledger.remove(best_match)
        
        return matches, unmatched_bank, unmatched_ledger
    
    def _calculate_amount_score(self, bank_txn: BankTransaction, ledger_entry: LedgerEntry) -> float:
        """Calculate amount similarity score"""
        bank_amount = abs(bank_txn.amount)
        ledger_amount = abs(ledger_entry.debit - ledger_entry.credit)
        
        if abs(bank_amount - ledger_amount) < 0.01:  # Exact match
            return 1.0
        elif abs(bank_amount - ledger_amount) / max(bank_amount, ledger_amount) < 0.05:  # Within 5%
            return 0.8
        else:
            return 0.0
    
    def _calculate_date_score(self, bank_txn: BankTransaction, ledger_entry: LedgerEntry) -> float:
        """Calculate date proximity score"""
        date_diff = abs((bank_txn.date - ledger_entry.date).days)
        
        if date_diff == 0:
            return 1.0
        elif date_diff <= 2:
            return 0.8
        elif date_diff <= 7:
            return 0.5
        else:
            return 0.2
    
    def _calculate_description_score(self, bank_txn: BankTransaction, ledger_entry: LedgerEntry) -> float:
        """Calculate description similarity score"""
        desc1 = (bank_txn.description or "").lower()
        desc2 = (ledger_entry.description or "").lower()
        
        if not desc1 or not desc2:
            return 0.5  # Neutral score if missing descriptions
        
        # Use sequence matcher for text similarity
        similarity = SequenceMatcher(None, desc1, desc2).ratio()
        return similarity
    
    async def calculate_balances(
        self,
        org_id: uuid.UUID,
        account_code: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Calculate opening, closing, and period balances
        """
        # Opening balance (before start date)
        opening_balance = await self._get_account_balance_until(org_id, account_code, start_date - timedelta(days=1))
        
        # Period transactions
        period_entries = self.db.query(LedgerEntry).filter(
            LedgerEntry.org_id == org_id,
            LedgerEntry.account_code == account_code,
            LedgerEntry.date >= start_date,
            LedgerEntry.date <= end_date
        ).all()
        
        # Calculate period activity
        period_debit = sum(entry.debit for entry in period_entries)
        period_credit = sum(entry.credit for entry in period_entries)
        
        # Closing balance
        closing_balance = opening_balance + period_debit - period_credit
        
        return {
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "period_debit": period_debit,
            "period_credit": period_credit,
            "transaction_count": len(period_entries)
        }
    
    async def _get_account_balance_until(self, org_id: uuid.UUID, account_code: str, until_date: date) -> float:
        """Get account balance until specific date"""
        entries = self.db.query(LedgerEntry).filter(
            LedgerEntry.org_id == org_id,
            LedgerEntry.account_code == account_code,
            LedgerEntry.date <= until_date
        ).all()
        
        balance = 0.0
        for entry in entries:
            balance += entry.debit - entry.credit
        
        return balance

# Service instance
reconciliation_service = None

def get_reconciliation_service(db_session: Session) -> ReconciliationService:
    global reconciliation_service
    if reconciliation_service is None:
        reconciliation_service = ReconciliationService(db_session)
    return reconciliation_service