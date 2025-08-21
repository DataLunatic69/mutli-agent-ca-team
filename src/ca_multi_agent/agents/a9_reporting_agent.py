from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, date
import logging
import pandas as pd
import numpy as np
from sqlalchemy import func

from .base import BaseAgent
from datetime import timedelta
from ..models.accounting import LedgerEntry, ChartOfAccounts

logger = logging.getLogger(__name__)

class ReportingAgent(BaseAgent):
    def __init__(self, db_session):
        super().__init__("A9_Reporting_Analytics")
        self.db = db_session

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        org_id = input_data.get('org_id')
        period = input_data.get('period', 'current_month')
        report_types = input_data.get('report_types', ['pnl', 'bs', 'cashflow'])
        compare_with = input_data.get('compare_with', 'previous_period')
        
        if not org_id:
            raise ValueError("Organization ID is required")
        
        # Parse period
        start_date, end_date = self._parse_period(period)
        comparison_start, comparison_end = self._get_comparison_period(start_date, end_date, compare_with)
        
        reports = {}
        
        # Generate requested reports
        if 'pnl' in report_types:
            reports['profit_loss'] = await self._generate_profit_loss_report(org_id, start_date, end_date, comparison_start, comparison_end)
        
        if 'bs' in report_types:
            reports['balance_sheet'] = await self._generate_balance_sheet(org_id, end_date, comparison_end)
        
        if 'cashflow' in report_types:
            reports['cash_flow'] = await self._generate_cash_flow_statement(org_id, start_date, end_date, comparison_start, comparison_end)
        
        if 'aging' in report_types:
            reports['aging_analysis'] = await self._generate_aging_analysis(org_id, end_date)
        
        # Generate insights
        insights = await self._generate_insights(reports, org_id)
        
        return {
            'success': True,
            'org_id': org_id,
            'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
            'reports': reports,
            'insights': insights,
            'ratios': await self._calculate_financial_ratios(reports),
            'trends': await self._analyze_trends(org_id, start_date, end_date),
            'timestamp': datetime.now().isoformat()
        }

    async def _generate_profit_loss_report(self, org_id: uuid.UUID, start_date: date, end_date: date, 
                                         comp_start: date, comp_end: date) -> Dict:
        """Generate profit and loss statement"""
        # Get revenue and expense totals
        revenue = await self._get_account_type_total(org_id, 'Income', start_date, end_date)
        expenses = await self._get_account_type_total(org_id, 'Expense', start_date, end_date)
        
        # Get comparison period data
        comp_revenue = await self._get_account_type_total(org_id, 'Income', comp_start, comp_end)
        comp_expenses = await self._get_account_type_total(org_id, 'Expense', comp_start, comp_end)
        
        gross_profit = revenue - expenses
        comp_gross_profit = comp_revenue - comp_expenses
        
        return {
            'revenue': {
                'current': revenue,
                'previous': comp_revenue,
                'change': revenue - comp_revenue,
                'change_percent': ((revenue - comp_revenue) / comp_revenue * 100) if comp_revenue else 0
            },
            'expenses': {
                'current': expenses,
                'previous': comp_expenses,
                'change': expenses - comp_expenses,
                'change_percent': ((expenses - comp_expenses) / comp_expenses * 100) if comp_expenses else 0
            },
            'gross_profit': {
                'current': gross_profit,
                'previous': comp_gross_profit,
                'change': gross_profit - comp_gross_profit,
                'change_percent': ((gross_profit - comp_gross_profit) / comp_gross_profit * 100) if comp_gross_profit else 0
            },
            'breakdown': await self._get_account_breakdown(org_id, start_date, end_date)
        }

    async def _generate_balance_sheet(self, org_id: uuid.UUID, as_of_date: date, comp_date: date) -> Dict:
        """Generate balance sheet"""
        assets = await self._get_account_type_total(org_id, 'Asset', None, as_of_date)
        liabilities = await self._get_account_type_total(org_id, 'Liability', None, as_of_date)
        equity = await self._get_account_type_total(org_id, 'Equity', None, as_of_date)
        
        comp_assets = await self._get_account_type_total(org_id, 'Asset', None, comp_date)
        comp_liabilities = await self._get_account_type_total(org_id, 'Liability', None, comp_date)
        comp_equity = await self._get_account_type_total(org_id, 'Equity', None, comp_date)
        
        return {
            'assets': {
                'current': assets,
                'previous': comp_assets,
                'breakdown': await self._get_account_breakdown(org_id, None, as_of_date, 'Asset')
            },
            'liabilities': {
                'current': liabilities,
                'previous': comp_liabilities,
                'breakdown': await self._get_account_breakdown(org_id, None, as_of_date, 'Liability')
            },
            'equity': {
                'current': equity,
                'previous': comp_equity,
                'breakdown': await self._get_account_breakdown(org_id, None, as_of_date, 'Equity')
            },
            'balance_check': assets - (liabilities + equity)
        }

    async def _generate_cash_flow_statement(self, org_id: uuid.UUID, start_date: date, end_date: date,
                                          comp_start: date, comp_end: date) -> Dict:
        """Generate cash flow statement"""
        # Simplified cash flow calculation
        operating = await self._get_cash_flow_activities(org_id, 'Operating', start_date, end_date)
        investing = await self._get_cash_flow_activities(org_id, 'Investing', start_date, end_date)
        financing = await self._get_cash_flow_activities(org_id, 'Financing', start_date, end_date)
        
        net_cash_flow = operating + investing + financing
        
        return {
            'operating_activities': operating,
            'investing_activities': investing,
            'financing_activities': financing,
            'net_cash_flow': net_cash_flow,
            'opening_balance': await self._get_account_balance(org_id, 'CASH', start_date - timedelta(days=1)),
            'closing_balance': await self._get_account_balance(org_id, 'CASH', end_date)
        }

    async def _generate_aging_analysis(self, org_id: uuid.UUID, as_of_date: date) -> Dict:
        """Generate accounts receivable/payable aging analysis"""
        aging_buckets = ['0-30', '31-60', '61-90', '91+']
        
        return {
            'receivable_aging': {
                bucket: await self._get_aging_amount(org_id, 'Receivable', bucket, as_of_date)
                for bucket in aging_buckets
            },
            'payable_aging': {
                bucket: await self._get_aging_amount(org_id, 'Payable', bucket, as_of_date)
                for bucket in aging_buckets
            }
        }

    async def _generate_insights(self, reports: Dict, org_id: uuid.UUID) -> List[Dict]:
        """Generate business insights from reports"""
        insights = []
        
        pnl = reports.get('profit_loss', {})
        bs = reports.get('balance_sheet', {})
        
        # Revenue growth insight
        if pnl.get('revenue', {}).get('change_percent', 0) > 20:
            insights.append({
                'type': 'positive',
                'title': 'Strong Revenue Growth',
                'message': f"Revenue increased by {pnl['revenue']['change_percent']:.1f}% compared to previous period",
                'impact': 'high'
            })
        elif pnl.get('revenue', {}).get('change_percent', 0) < -10:
            insights.append({
                'type': 'warning',
                'title': 'Revenue Decline',
                'message': f"Revenue decreased by {abs(pnl['revenue']['change_percent']):.1f}% compared to previous period",
                'impact': 'high'
            })
        
        # Profitability insight
        if pnl.get('gross_profit', {}).get('current', 0) < 0:
            insights.append({
                'type': 'critical',
                'title': 'Negative Profitability',
                'message': 'Business is operating at a loss',
                'impact': 'very_high'
            })
        
        return insights

    async def _calculate_financial_ratios(self, reports: Dict) -> Dict:
        """Calculate key financial ratios"""
        pnl = reports.get('profit_loss', {})
        bs = reports.get('balance_sheet', {})
        
        revenue = pnl.get('revenue', {}).get('current', 1)
        profit = pnl.get('gross_profit', {}).get('current', 0)
        assets = bs.get('assets', {}).get('current', 1)
        liabilities = bs.get('liabilities', {}).get('current', 1)
        equity = bs.get('equity', {}).get('current', 1)
        
        return {
            'profitability': {
                'gross_margin': (profit / revenue * 100) if revenue else 0,
                'net_margin': (profit / revenue * 100) if revenue else 0,
            },
            'liquidity': {
                'current_ratio': (assets / liabilities) if liabilities else 0,
                'quick_ratio': ((assets) / liabilities) if liabilities else 0,
            },
            'leverage': {
                'debt_to_equity': (liabilities / equity) if equity else 0,
                'debt_ratio': (liabilities / assets) if assets else 0,
            }
        }

    # Helper methods for data retrieval would be implemented here...