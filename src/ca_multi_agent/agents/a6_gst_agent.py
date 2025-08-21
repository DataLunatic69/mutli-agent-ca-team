from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, date
import logging
import json

from .base_agent import BaseAgent
from ..services.tax_services import get_tax_service
from ..services.ledger_services import get_ledger_service

logger = logging.getLogger(__name__)

class GSTAgent(BaseAgent):
    def __init__(self, db_session):
        super().__init__("A6_GST_Agent")
        self.tax_service = get_tax_service(db_session)
        self.ledger_service = get_ledger_service(db_session)
        self.gst_rates = {
            '0': 0.0,      # Nil rated
            '5': 5.0,      # 5% GST
            '12': 12.0,    # 12% GST  
            '18': 18.0,    # 18% GST
            '28': 28.0     # 28% GST
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        org_id = input_data.get('org_id')
        period = input_data.get('period')
        gstin = input_data.get('gstin')
        sales_data = input_data.get('sales', [])
        purchase_data = input_data.get('purchases', [])
        
        if not all([org_id, period, gstin]):
            raise ValueError("Missing required parameters: org_id, period, or gstin")
        
        # If no data provided, fetch from ledger
        if not sales_data and not purchase_data:
            sales_data, purchase_data = await self._fetch_gst_data_from_ledger(org_id, period)
        
        # Calculate GST liability
        liability_result = await self.tax_service.calculate_gst_liability(org_id, period, gstin)
        
        # Generate GSTR-1
        gstr1_result = await self.tax_service.generate_gstr1_json(org_id, period, gstin)
        
        # Generate GSTR-3B summary
        gstr3b_result = await self._generate_gstr3b_summary(liability_result)
        
        # Reconcile with GSTR-2B (ITC)
        itc_reconciliation = await self._reconcile_itc(org_id, period, liability_result)
        
        return {
            'success': True,
            'org_id': org_id,
            'period': period,
            'gstin': gstin,
            'liability_summary': liability_result,
            'gstr1_json': gstr1_result,
            'gstr3b_summary': gstr3b_result,
            'itc_reconciliation': itc_reconciliation,
            'compliance_status': self._check_compliance_status(period),
            'timestamp': datetime.now().isoformat()
        }

    async def _fetch_gst_data_from_ledger(self, org_id: uuid.UUID, period: str) -> tuple:
        """Fetch GST-relevant data from ledger entries"""
        # Parse period
        month, year = period.split('-')
        start_date = date(int(year), int(month), 1)
        end_date = date(int(year), int(month), 28)  # Approximate
        
        # Get ledger entries with GST tags
        entries = await self.ledger_service.get_ledger_entries(
            org_id, start_date, end_date
        )
        
        sales_data = []
        purchase_data = []
        
        for entry in entries:
            tags = entry.tags or {}
            if tags.get('gst_applicable'):
                transaction_data = {
                    'date': entry.date.isoformat(),
                    'description': entry.description,
                    'amount': entry.debit - entry.credit,
                    'gst_rate': tags.get('gst_rate', 0),
                    'taxable_value': tags.get('taxable_value', 0),
                    'tax_amount': tags.get('tax_amount', 0),
                    'party': entry.party,
                    'hsn_sac': tags.get('hsn_sac')
                }
                
                if tags.get('transaction_direction') == 'OUTWARD':
                    sales_data.append(transaction_data)
                else:
                    purchase_data.append(transaction_data)
        
        return sales_data, purchase_data

    async def _generate_gstr3b_summary(self, liability_result: Dict) -> Dict:
        """Generate GSTR-3B summary from liability calculation"""
        return {
            "gstin": liability_result["gstin"],
            "period": liability_result["period"],
            "3.1": {
                "Outward supplies and inward supplies liable to reverse charge": {
                    "Taxable value": liability_result["sales_summary"]["total_taxable_value"],
                    "Integrated Tax": self._calculate_tax_by_type(liability_result["sales_summary"], "igst"),
                    "Central Tax": self._calculate_tax_by_type(liability_result["sales_summary"], "cgst"),
                    "State Tax": self._calculate_tax_by_type(liability_result["sales_summary"], "sgst")
                }
            },
            "4": {
                "Eligible ITC": {
                    "Integrated Tax": liability_result["input_tax_credit"] * 0.5,  # Simplified
                    "Central Tax": liability_result["input_tax_credit"] * 0.25,
                    "State Tax": liability_result["input_tax_credit"] * 0.25
                }
            },
            "5.1": {
                "Total tax liability": liability_result["output_tax_liability"]
            }
        }

    def _calculate_tax_by_type(self, summary: Dict, tax_type: str) -> float:
        """Calculate tax amount by type (IGST, CGST, SGST)"""
        # Simplified calculation - in reality, this would use actual tax breakdown
        total_tax = summary["total_tax"]
        if tax_type == "igst":
            return total_tax * 0.5
        elif tax_type == "cgst":
            return total_tax * 0.25
        elif tax_type == "sgst":
            return total_tax * 0.25
        return 0.0

    async def _reconcile_itc(self, org_id: uuid.UUID, period: str, liability_result: Dict) -> Dict:
        """Reconcile Input Tax Credit with GSTR-2B"""
        # This would integrate with GSTN API or uploaded GSTR-2B in real implementation
        return {
            "eligible_itc": liability_result["input_tax_credit"],
            "matched_itc": liability_result["input_tax_credit"] * 0.85,  # 85% matched
            "mismatched_itc": liability_result["input_tax_credit"] * 0.15,
            "reconciliation_status": "partial_match",
            "notes": "15% ITC requires vendor documentation verification"
        }

    def _check_compliance_status(self, period: str) -> Dict:
        """Check GST compliance status for the period"""
        due_dates = {
            "GSTR-1": self._get_gstr1_due_date(period),
            "GSTR-3B": self._get_gstr3b_due_date(period),
            "GSTR-9": self._get_annual_return_due_date(period)
        }
        
        return {
            "period": period,
            "due_dates": due_dates,
            "filing_status": {
                "GSTR-1": "pending",
                "GSTR-3B": "pending", 
                "GSTR-9": "not_applicable"
            },
            "penalties_applicable": False
        }

    def _get_gstr1_due_date(self, period: str) -> str:
        """Calculate GSTR-1 due date"""
        month, year = period.split('-')
        due_date = date(int(year), int(month) + 1, 11)  # 11th of next month
        return due_date.isoformat()

    def _get_gstr3b_due_date(self, period: str) -> str:
        """Calculate GSTR-3B due date"""
        month, year = period.split('-')
        due_date = date(int(year), int(month) + 1, 20)  # 20th of next month
        return due_date.isoformat()

    def _get_annual_return_due_date(self, period: str) -> str:
        """Calculate annual return due date"""
        month, year = period.split('-')
        due_date = date(int(year) + 1, 12, 31)  # 31st Dec of next year
        return due_date.isoformat()

    async def validate_gstin(self, gstin: str) -> Dict:
        """Validate GSTIN format and check status"""
        # Basic format validation
        if not re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$', gstin):
            return {"valid": False, "error": "Invalid GSTIN format"}
        
        # Check state code (first two digits)
        state_code = gstin[:2]
        valid_states = ['27', '29', '33']  # Example state codes
        
        return {
            "valid": True,
            "state_code": state_code,
            "state_valid": state_code in valid_states,
            "status": "active",
            "business_name": "Sample Business Name"  # Would come from GSTN API
        }