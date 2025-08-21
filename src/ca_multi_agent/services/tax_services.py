from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import date
import logging
import json

from ..models.tax import GSTReturn, ITReturn, TaxComputation
from ..models.accounting import LedgerEntry

logger = logging.getLogger(__name__)

class TaxService:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def calculate_gst_liability(
        self,
        org_id: uuid.UUID,
        period: str,  # Format: "MM-YYYY"
        gstin: str
    ) -> Dict[str, Any]:
        """
        Calculate GST liability for a period
        """
        try:
            month, year = period.split('-')
            start_date = date(int(year), int(month), 1)
            end_date = date(int(year), int(month), 28)  # Approximate end
            
            # Get sales and purchase entries
            sales_entries = self._get_tax_entries(org_id, start_date, end_date, 'OUTWARD')
            purchase_entries = self._get_tax_entries(org_id, start_date, end_date, 'INWARD')
            
            # Calculate totals
            sales_summary = self._summarize_gst_entries(sales_entries)
            purchase_summary = self._summarize_gst_entries(purchase_entries)
            
            # Calculate liability
            output_tax = sales_summary['total_tax']
            input_tax_credit = purchase_summary['total_tax']
            net_liability = output_tax - input_tax_credit
            
            result = {
                "gstin": gstin,
                "period": period,
                "sales_summary": sales_summary,
                "purchase_summary": purchase_summary,
                "output_tax_liability": output_tax,
                "input_tax_credit": input_tax_credit,
                "net_gst_payable": max(0, net_liability),
                "refund_eligible": max(0, -net_liability),
                "calculation_date": date.today().isoformat()
            }
            
            # Save computation
            computation = TaxComputation(
                org_id=org_id,
                financial_year=f"{year}-{int(year)+1}",
                tax_type="gst",
                computation_data=result,
                result=result
            )
            self.db.add(computation)
            self.db.commit()
            
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error calculating GST liability: {e}")
            raise
    
    def _get_tax_entries(self, org_id: uuid.UUID, start_date: date, end_date: date, direction: str) -> List[LedgerEntry]:
        """Get ledger entries with GST tags"""
        query = self.db.query(LedgerEntry).filter(
            LedgerEntry.org_id == org_id,
            LedgerEntry.date >= start_date,
            LedgerEntry.date <= end_date,
            LedgerEntry.tags != None
        )
        
        entries = query.all()
        
        # Filter entries with GST tags and matching direction
        gst_entries = []
        for entry in entries:
            tags = entry.tags or {}
            if tags.get('gst_applicable') and tags.get('transaction_direction') == direction:
                gst_entries.append(entry)
        
        return gst_entries
    
    def _summarize_gst_entries(self, entries: List[LedgerEntry]) -> Dict[str, Any]:
        """Summarize GST entries by tax rate"""
        summary = {
            "total_taxable_value": 0.0,
            "total_tax": 0.0,
            "by_tax_rate": {},
            "entry_count": len(entries)
        }
        
        for entry in entries:
            tags = entry.tags or {}
            tax_rate = tags.get('gst_rate', 0)
            taxable_value = tags.get('taxable_value', 0)
            tax_amount = tags.get('tax_amount', 0)
            
            summary["total_taxable_value"] += taxable_value
            summary["total_tax"] += tax_amount
            
            if tax_rate not in summary["by_tax_rate"]:
                summary["by_tax_rate"][tax_rate] = {
                    "taxable_value": 0.0,
                    "tax_amount": 0.0,
                    "entry_count": 0
                }
            
            summary["by_tax_rate"][tax_rate]["taxable_value"] += taxable_value
            summary["by_tax_rate"][tax_rate]["tax_amount"] += tax_amount
            summary["by_tax_rate"][tax_rate]["entry_count"] += 1
        
        return summary
    
    async def generate_gstr1_json(
        self,
        org_id: uuid.UUID,
        period: str,
        gstin: str
    ) -> Dict[str, Any]:
        """
        Generate GSTR-1 JSON payload
        """
        # Calculate liability first to get data
        liability = await self.calculate_gst_liability(org_id, period, gstin)
        
        # Format as GSTR-1 JSON
        gstr1_payload = {
            "gstin": gstin,
            "fp": period,
            "b2b": self._format_b2b_section(liability),
            "b2cs": self._format_b2cs_section(liability),
            "cdnr": self._format_credit_debit_notes(liability),
            "summary": self._format_gstr1_summary(liability)
        }
        
        # Save to database
        gst_return = GSTReturn(
            org_id=org_id,
            return_period=period,
            return_type="GSTR1",
            gstin=gstin,
            payload=gstr1_payload,
            summary=liability,
            status="draft"
        )
        self.db.add(gst_return)
        self.db.commit()
        
        return gstr1_payload
    
    def _format_b2b_section(self, liability: Dict) -> List[Dict]:
        """Format B2B section of GSTR-1"""
        # This would be populated with actual invoice data
        return []
    
    def _format_b2cs_section(self, liability: Dict) -> List[Dict]:
        """Format B2CS section of GSTR-1"""
        return []
    
    def _format_credit_debit_notes(self, liability: Dict) -> List[Dict]:
        """Format credit/debit notes section"""
        return []
    
    def _format_gstr1_summary(self, liability: Dict) -> Dict:
        """Format GSTR-1 summary section"""
        return {
            "tt_tax": liability["output_tax_liability"],
            "tt_rec": liability["total_taxable_value"],
            "tt_itc": liability["input_tax_credit"]
        }
    
    async def generate_itr_payload(
        self,
        org_id: uuid.UUID,
        assessment_year: str,  # Format: "2024-25"
        pan: str
    ) -> Dict[str, Any]:
        """
        Generate Income Tax Return JSON payload
        """
        # This would calculate income, deductions, tax liability, etc.
        # Simplified implementation
        
        itr_payload = {
            "pan": pan,
            "ay": assessment_year,
            "personal_info": self._get_personal_info(org_id),
            "income_details": await self._calculate_income_details(org_id, assessment_year),
            "deductions": await self._calculate_deductions(org_id, assessment_year),
            "tax_computation": await self._compute_tax_liability(org_id, assessment_year),
            "taxes_paid": await self._get_taxes_paid(org_id, assessment_year)
        }
        
        # Save to database
        it_return = ITReturn(
            org_id=org_id,
            assessment_year=assessment_year,
            return_type="ITR3",  # Assuming business
            pan=pan,
            payload=itr_payload,
            status="draft"
        )
        self.db.add(it_return)
        self.db.commit()
        
        return itr_payload
    
    def _get_personal_info(self, org_id: uuid.UUID) -> Dict:
        """Get personal/business information"""
        return {}  # Would fetch from organization profile
    
    async def _calculate_income_details(self, org_id: uuid.UUID, assessment_year: str) -> Dict:
        """Calculate income from various sources"""
        return {
            "business_income": 0.0,
            "capital_gains": 0.0,
            "other_sources": 0.0,
            "total_income": 0.0
        }
    
    async def _calculate_deductions(self, org_id: uuid.UUID, assessment_year: str) -> Dict:
        """Calculate allowable deductions"""
        return {
            "section_80C": 0.0,
            "section_80D": 0.0,
            "other_deductions": 0.0,
            "total_deductions": 0.0
        }
    
    async def _compute_tax_liability(self, org_id: uuid.UUID, assessment_year: str) -> Dict:
        """Compute total tax liability"""
        return {
            "gross_tax_liability": 0.0,
            "rebates": 0.0,
            "net_tax_liability": 0.0
        }
    
    async def _get_taxes_paid(self, org_id: uuid.UUID, assessment_year: str) -> Dict:
        """Get taxes already paid (advance tax, TDS, etc.)"""
        return {
            "advance_tax": 0.0,
            "tds": 0.0,
            "self_assessment_tax": 0.0,
            "total_taxes_paid": 0.0
        }

# Service instance
tax_service = None

def get_tax_service(db_session: Session) -> TaxService:
    global tax_service
    if tax_service is None:
        tax_service = TaxService(db_session)
    return tax_service