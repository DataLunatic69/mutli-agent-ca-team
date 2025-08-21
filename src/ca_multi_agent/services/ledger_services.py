from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime, date
import logging

from ..models.accounting import ChartOfAccounts, Voucher, LedgerEntry
from ..models.document import Document

logger = logging.getLogger(__name__)

class LedgerService:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def create_voucher(
        self,
        org_id: uuid.UUID,
        voucher_date: date,
        voucher_type: str,
        entries: List[Dict[str, Any]],
        ref_no: Optional[str] = None,
        narration: Optional[str] = None,
        source: str = "agent",
        doc_id: Optional[uuid.UUID] = None
    ) -> Voucher:
        """
        Create a voucher with multiple ledger entries
        """
        try:
            # Calculate total amount for validation
            total_debit = sum(entry.get('debit', 0) for entry in entries)
            total_credit = sum(entry.get('credit', 0) for entry in entries)
            
            if abs(total_debit - total_credit) > 0.01:  # Allow for floating point precision
                raise ValueError(f"Debit ({total_debit}) and credit ({total_credit}) totals don't match")
            
            # Create voucher
            voucher = Voucher(
                org_id=org_id,
                date=voucher_date,
                type=voucher_type,
                ref_no=ref_no,
                narration=narration,
                source=source,
                amount=total_debit,  # or total_credit, they should be equal
                doc_id=doc_id
            )
            
            self.db.add(voucher)
            self.db.flush()  # Get the voucher ID
            
            # Create ledger entries
            for entry_data in entries:
                ledger_entry = LedgerEntry(
                    org_id=org_id,
                    voucher_id=voucher.id,
                    date=voucher_date,
                    account_code=entry_data['account_code'],
                    party=entry_data.get('party'),
                    description=entry_data.get('description'),
                    debit=entry_data.get('debit', 0),
                    credit=entry_data.get('credit', 0),
                    tags=entry_data.get('tags')
                )
                self.db.add(ledger_entry)
            
            self.db.commit()
            return voucher
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating voucher: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating voucher: {e}")
            raise
    
    async def map_transaction_to_coa(
        self,
        org_id: uuid.UUID,
        transaction_description: str,
        amount: float,
        transaction_type: str,  # 'debit' or 'credit'
        party: Optional[str] = None,
        hints: Optional[List[str]] = None
    ) -> Tuple[str, float, float]:
        """
        Map a transaction to Chart of Accounts using rule-based matching
        Returns: (account_code, debit_amount, credit_amount)
        """
        # Simple rule-based mapping - this should be enhanced with ML later
        description_lower = transaction_description.lower()
        
        # Default mappings based on common patterns
        mapping_rules = [
            (['salary', 'wage', 'payroll'], 'SALARIES', 'expense'),
            (['rent', 'lease'], 'RENT', 'expense'),
            (['electricity', 'power', 'utility'], 'UTILITIES', 'expense'),
            (['internet', 'broadband', 'wifi'], 'INTERNET', 'expense'),
            (['tax', 'gst', 'tds'], 'TAX_PAYABLE', 'liability'),
            (['bank', 'hdfc', 'icici', 'sbi'], 'BANK', 'asset'),
            (['cash', 'petty cash'], 'CASH', 'asset'),
            (['sale', 'revenue', 'income'], 'SALES', 'income'),
            (['purchase', 'buy', 'procure'], 'PURCHASES', 'expense'),
            (['travel', 'conveyance', 'fuel'], 'TRAVEL', 'expense'),
            (['meal', 'food', 'restaurant'], 'MEALS', 'expense'),
            (['software', 'subscription', 'saas'], 'SOFTWARE', 'expense'),
        ]
        
        # Find matching rule
        account_code = None
        for keywords, code, account_type in mapping_rules:
            if any(keyword in description_lower for keyword in keywords):
                account_code = code
                break
        
        # Default fallback
        if not account_code:
            if amount > 0:
                account_code = 'MISC_INCOME' if transaction_type == 'credit' else 'MISC_EXPENSE'
            else:
                account_code = 'MISC_EXPENSE' if transaction_type == 'debit' else 'MISC_INCOME'
        
        # Set debit/credit amounts
        if transaction_type == 'debit':
            debit_amount = abs(amount)
            credit_amount = 0
        else:  # credit
            debit_amount = 0
            credit_amount = abs(amount)
        
        return account_code, debit_amount, credit_amount
    
    async def get_ledger_entries(
        self,
        org_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_code: Optional[str] = None,
        party: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[LedgerEntry]:
        """
        Query ledger entries with filters
        """
        query = self.db.query(LedgerEntry).filter(LedgerEntry.org_id == org_id)
        
        if start_date:
            query = query.filter(LedgerEntry.date >= start_date)
        if end_date:
            query = query.filter(LedgerEntry.date <= end_date)
        if account_code:
            query = query.filter(LedgerEntry.account_code == account_code)
        if party:
            query = query.filter(LedgerEntry.party.ilike(f"%{party}%"))
        
        return query.order_by(LedgerEntry.date.desc()).offset(offset).limit(limit).all()
    
    async def get_account_balance(
        self,
        org_id: uuid.UUID,
        account_code: str,
        as_of_date: Optional[date] = None
    ) -> float:
        """
        Calculate balance for a specific account
        """
        query = self.db.query(LedgerEntry).filter(
            LedgerEntry.org_id == org_id,
            LedgerEntry.account_code == account_code
        )
        
        if as_of_date:
            query = query.filter(LedgerEntry.date <= as_of_date)
        
        entries = query.all()
        
        balance = 0.0
        for entry in entries:
            balance += entry.debit - entry.credit
        
        return balance

# Service instance (can be dependency-injected)
ledger_service = None

def get_ledger_service(db_session: Session) -> LedgerService:
    global ledger_service
    if ledger_service is None:
        ledger_service = LedgerService(db_session)
    return ledger_service