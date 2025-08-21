from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, date
import logging
import re

from .base import BaseAgent
from ..services.tax_services import get_tax_service
from ..services.ledger_services import get_ledger_service

logger = logging.getLogger(__name__)

class IncomeTaxAgent(BaseAgent):
    def __init__(self, db_session):
        super().__init__("A7_Income_Tax_Agent")
        self.tax_service = get_tax_service(db_session)
        self.ledger_service = get_ledger_service(db_session)
        
        # Tax slabs for individuals (AY 2024-25)
        self.tax_slabs = [
            (0, 300000, 0),
            (300001, 600000, 5),
            (600001, 900000, 10),
            (900001, 1200000, 15),
            (1200001, 1500000, 20),
            (1500001, float('inf'), 30)
        ]
        
        # Standard deduction
        self.standard_deduction = 50000

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        org_id = input_data.get('org_id')
        fy = input_data.get('fy')  # Financial year: 2023-24
        pan = input_data.get('pan')
        pnl_data = input_data.get('pnl', {})
        balance_data = input_data.get('balances', {})
        ledger_data = input_data.get('ledgers', [])
        
        if not all([org_id, fy, pan]):
            raise ValueError("Missing required parameters: org_id, fy, or pan")
        
        # If no financial data provided, fetch from ledger
        if not pnl_data and not balance_data and not ledger_data:
            pnl_data, balance_data = await self._fetch_financial_data(org_id, fy)
        
        # Generate ITR payload
        itr_payload = await self.tax_service.generate_itr_payload(org_id, fy, pan)
        
        # Calculate detailed tax computation
        tax_computation = await self._compute_detailed_tax(org_id, fy, pnl_data)
        
        # Generate tax payment schedule
        tax_schedule = await self._generate_tax_schedule(tax_computation)
        
        # Prepare TDS/TCS summary
        tds_summary = await self._prepare_tds_summary(org_id, fy)
        
        return {
            'success': True,
            'org_id': org_id,
            'financial_year': fy,
            'pan': pan,
            'itr_payload': itr_payload,
            'tax_computation': tax_computation,
            'tax_schedule': tax_schedule,
            'tds_tcs_summary': tds_summary,
            'compliance_notes': self._generate_compliance_notes(fy, tax_computation),
            'timestamp': datetime.now().isoformat()
        }

    async def _fetch_financial_data(self, org_id: uuid.UUID, fy: str) -> tuple:
        """Fetch financial data from ledger for the financial year"""
        # Parse financial year (e.g., "2023-24")
        start_year = int(fy.split('-')[0])
        start_date = date(start_year, 4, 1)  # April 1
        end_date = date(start_year + 1, 3, 31)  # March 31
        
        # This would involve complex financial statement generation
        # Simplified implementation for demo
        
        return {
            'revenue': 1000000,
            'expenses': 700000,
            'gross_profit': 300000,
            'net_profit': 250000
        }, {
            'assets': 500000,
            'liabilities': 200000,
            'equity': 300000
        }

    async def _compute_detailed_tax(self, org_id: uuid.UUID, fy: str, pnl_data: Dict) -> Dict:
        """Compute detailed income tax liability"""
        net_profit = pnl_data.get('net_profit', 0)
        
        # Calculate taxable income (simplified)
        taxable_income = net_profit - self.standard_deduction
        
        # Apply tax slabs
        tax_liability = 0
        remaining_income = taxable_income
        
        for lower, upper, rate in self.tax_slabs:
            if remaining_income <= 0:
                break
                
            slab_income = min(remaining_income, upper - lower)
            tax_liability += slab_income * rate / 100
            remaining_income -= slab_income
        
        # Add cess
        cess = tax_liability * 0.04  # 4% health and education cess
        total_tax = tax_liability + cess
        
        return {
            'taxable_income': taxable_income,
            'tax_liability': tax_liability,
            'cess': cess,
            'total_tax': total_tax,
            'tax_slabs_applied': self.tax_slabs,
            'standard_deduction': self.standard_deduction,
            'financial_year': fy
        }

    async def _generate_tax_schedule(self, tax_computation: Dict) -> Dict:
        """Generate tax payment schedule"""
        total_tax = tax_computation['total_tax']
        
        return {
            'advance_tax_due_dates': [
                {'installment': 1, 'due_date': '2023-06-15', 'percentage': 15},
                {'installment': 2, 'due_date': '2023-09-15', 'percentage': 45},
                {'installment': 3, 'due_date': '2023-12-15', 'percentage': 75},
                {'installment': 4, 'due_date': '2024-03-15', 'percentage': 100}
            ],
            'estimated_payments': [
                {'date': '2023-06-15', 'amount': total_tax * 0.15},
                {'date': '2023-09-15', 'amount': total_tax * 0.30},
                {'date': '2023-12-15', 'amount': total_tax * 0.30},
                {'date': '2024-03-15', 'amount': total_tax * 0.25}
            ],
            'final_payment_due': '2024-07-31',
            'total_tax_liability': total_tax
        }

    async def _prepare_tds_summary(self, org_id: uuid.UUID, fy: str) -> Dict:
        """Prepare TDS/TCS summary from ledger"""
        # This would query ledger for TDS/TCS entries
        return {
            'tds_deducted': 15000,
            'tds_deposited': 15000,
            'tds_credit_available': 15000,
            'tds_certificates': [
                {'quarter': 'Q1', 'amount': 5000, 'form': '24Q'},
                {'quarter': 'Q2', 'amount': 5000, 'form': '24Q'},
                {'quarter': 'Q3', 'amount': 5000, 'form': '24Q'}
            ],
            'tcs_collected': 0,
            'financial_year': fy
        }

    def _generate_compliance_notes(self, fy: str, tax_computation: Dict) -> List[str]:
        """Generate compliance notes and recommendations"""
        notes = []
        
        total_tax = tax_computation['total_tax']
        
        if total_tax > 10000:
            notes.append("Advance tax payments are required to avoid interest under Section 234B/C")
        
        if tax_computation['taxable_income'] > 500000:
            notes.append("Tax audit may be applicable under Section 44AB")
        
        notes.append("ITR filing due date: July 31, 2024")
        notes.append("Belated return can be filed until December 31, 2024 with penalty")
        
        return notes

    async def validate_pan(self, pan: str) -> Dict:
        """Validate PAN format and check status"""
        if not re.match(r'^[A-Z]{5}\d{4}[A-Z]{1}$', pan):
            return {"valid": False, "error": "Invalid PAN format"}
        
        return {
            "valid": True,
            "category": pan[3],  # 4th character indicates category
            "status": "active",
            "name_match": "Sample Name"  # Would come from ITD database
        }

    async def calculate_advance_tax(self, org_id: uuid.UUID, estimated_income: float) -> Dict:
        """Calculate advance tax liability"""
        taxable_income = estimated_income - self.standard_deduction
        tax_liability = 0
        remaining_income = taxable_income
        
        for lower, upper, rate in self.tax_slabs:
            if remaining_income <= 0:
                break
            slab_income = min(remaining_income, upper - lower)
            tax_liability += slab_income * rate / 100
            remaining_income -= slab_income
        
        cess = tax_liability * 0.04
        total_tax = tax_liability + cess
        
        return {
            'estimated_income': estimated_income,
            'taxable_income': taxable_income,
            'advance_tax_liability': total_tax,
            'installments': [
                {'due_date': '2023-06-15', 'amount': total_tax * 0.15},
                {'due_date': '2023-09-15', 'amount': total_tax * 0.30},
                {'due_date': '2023-12-15', 'amount': total_tax * 0.30},
                {'due_date': '2024-03-15', 'amount': total_tax * 0.25}
            ]
        }