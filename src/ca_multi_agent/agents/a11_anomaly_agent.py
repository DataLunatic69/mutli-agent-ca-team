from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, date, timedelta
import logging
import numpy as np
from scipy import stats
import pandas as pd

from .base_agent import BaseAgent
from ..services.ledger_service import get_ledger_service

logger = logging.getLogger(__name__)

class AnomalyDetectionAgent(BaseAgent):
    def __init__(self, db_session):
        super().__init__("A11_Anomaly_Detection")
        self.ledger_service = get_ledger_service(db_session)
        self.detection_rules = self._load_detection_rules()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        org_id = input_data.get('org_id')
        period = input_data.get('period', 'current_month')
        detection_types = input_data.get('detection_types', ['all'])
        
        if not org_id:
            raise ValueError("Organization ID is required")
        
        # Parse period
        start_date, end_date = self._parse_period(period)
        
        # Get ledger data for analysis
        ledger_data = await self._get_ledger_data(org_id, start_date, end_date)
        
        # Run anomaly detection
        alerts = await self._detect_anomalies(org_id, ledger_data, detection_types)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(alerts)
        
        return {
            'success': True,
            'org_id': org_id,
            'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
            'alerts': alerts,
            'risk_score': risk_score,
            'risk_level': self._get_risk_level(risk_score),
            'explanations': await self._generate_explanations(alerts),
            'recommendations': await self._generate_recommendations(alerts),
            'timestamp': datetime.now().isoformat()
        }

    async def _detect_anomalies(self, org_id: uuid.UUID, ledger_data: List, detection_types: List[str]) -> List[Dict]:
        """Detect various types of anomalies"""
        alerts = []
        
        if 'all' in detection_types or 'amount' in detection_types:
            alerts.extend(await self._detect_amount_anomalies(ledger_data))
        
        if 'all' in detection_types or 'frequency' in detection_types:
            alerts.extend(await self._detect_frequency_anomalies(ledger_data))
        
        if 'all' in detection_types or 'pattern' in detection_types:
            alerts.extend(await self._detect_pattern_anomalies(ledger_data))
        
        if 'all' in detection_types or 'duplicate' in detection_types:
            alerts.extend(await self._detect_duplicate_invoices(ledger_data))
        
        if 'all' in detection_types or 'round_trip' in detection_types:
            alerts.extend(await self._detect_round_trip_transactions(ledger_data))
        
        # Filter and prioritize alerts
        return self._prioritize_alerts(alerts)

    async def _detect_amount_anomalies(self, ledger_data: List) -> List[Dict]:
        """Detect unusual transaction amounts"""
        alerts = []
        amounts = [entry['amount'] for entry in ledger_data if entry['amount'] > 0]
        
        if len(amounts) < 10:  # Need sufficient data
            return alerts
        
        # Statistical outlier detection
        z_scores = np.abs(stats.zscore(amounts))
        outliers = np.where(z_scores > 3)[0]
        
        for idx in outliers:
            entry = ledger_data[idx]
            alerts.append({
                'type': 'amount_anomaly',
                'severity': 'high',
                'description': f'Unusually large transaction: ₹{entry["amount"]:,.2f}',
                'transaction_date': entry['date'],
                'amount': entry['amount'],
                'account': entry['account_code'],
                'z_score': float(z_scores[idx]),
                'confidence': 0.85
            })
        
        return alerts

    async def _detect_frequency_anomalies(self, ledger_data: List) -> List[Dict]:
        """Detect unusual transaction frequencies"""
        alerts = []
        
        # Group by account and date
        df = pd.DataFrame(ledger_data)
        if df.empty:
            return alerts
        
        account_freq = df.groupby(['account_code', 'date']).size()
        
        # Detect accounts with unusually high frequency
        for (account_code, transaction_date), count in account_freq.items():
            if count > 20:  # More than 20 transactions per day for an account
                alerts.append({
                    'type': 'frequency_anomaly',
                    'severity': 'medium',
                    'description': f'High transaction frequency: {count} transactions on {transaction_date}',
                    'account': account_code,
                    'date': transaction_date,
                    'count': int(count),
                    'confidence': 0.75
                })
        
        return alerts

    async def _detect_duplicate_invoices(self, ledger_data: List) -> List[Dict]:
        """Detect potential duplicate invoices"""
        alerts = []
        
        # Group by amount and party
        df = pd.DataFrame(ledger_data)
        if df.empty:
            return alerts
        
        duplicates = df[df.duplicated(subset=['amount', 'party'], keep=False)]
        
        for _, group in duplicates.groupby(['amount', 'party']):
            if len(group) > 1:
                transactions = group.to_dict('records')
                alerts.append({
                    'type': 'duplicate_invoice',
                    'severity': 'high',
                    'description': f'Possible duplicate invoices: ₹{transactions[0]["amount"]:,.2f} to {transactions[0]["party"]}',
                    'transactions': transactions,
                    'count': len(transactions),
                    'confidence': 0.9
                })
        
        return alerts

    async def _detect_round_trip_transactions(self, ledger_data: List) -> List[Dict]:
        """Detect round-trip transactions (money in and out quickly)"""
        alerts = []
        
        # This would involve complex pattern matching
        # Simplified implementation
        
        return alerts

    def _calculate_risk_score(self, alerts: List[Dict]) -> float:
        """Calculate overall risk score based on alerts"""
        if not alerts:
            return 0.0
        
        severity_weights = {
            'critical': 1.0,
            'high': 0.7,
            'medium': 0.4,
            'low': 0.1
        }
        
        total_score = 0.0
        for alert in alerts:
            weight = severity_weights.get(alert.get('severity', 'low'), 0.1)
            confidence = alert.get('confidence', 0.5)
            total_score += weight * confidence
        
        # Normalize to 0-100 scale
        return min(total_score * 20, 100.0)

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 80:
            return 'critical'
        elif risk_score >= 60:
            return 'high'
        elif risk_score >= 40:
            return 'medium'
        elif risk_score >= 20:
            return 'low'
        else:
            return 'minimal'

    async def _generate_explanations(self, alerts: List[Dict]) -> List[Dict]:
        """Generate explanations for detected anomalies"""
        explanations = []
        
        for alert in alerts:
            explanation = {
                'alert_type': alert['type'],
                'explanation': self._get_alert_explanation(alert),
                'potential_causes': self._get_potential_causes(alert),
                'investigation_suggestions': self._get_investigation_steps(alert)
            }
            explanations.append(explanation)
        
        return explanations

    def _get_alert_explanation(self, alert: Dict) -> str:
        """Get explanation for specific alert type"""
        explanations = {
            'amount_anomaly': 'Transaction amount significantly deviates from normal patterns',
            'frequency_anomaly': 'Unusually high number of transactions in a short period',
            'duplicate_invoice': 'Multiple transactions with identical amount and party',
            'pattern_anomaly': 'Unusual transaction pattern detected'
        }
        return explanations.get(alert['type'], 'Suspicious activity detected')

    async def _generate_recommendations(self, alerts: List[Dict]) -> List[Dict]:
        """Generate recommendations for addressing anomalies"""
        recommendations = []
        
        for alert in alerts:
            rec = {
                'alert_type': alert['type'],
                'immediate_actions': self._get_immediate_actions(alert),
                'preventive_measures': self._get_preventive_measures(alert),
                'monitoring_suggestions': self._get_monitoring_suggestions(alert)
            }
            recommendations.append(rec)
        
        return recommendations

    def _get_immediate_actions(self, alert: Dict) -> List[str]:
        """Get immediate actions for alert"""
        actions = {
            'amount_anomaly': [
                'Verify transaction documentation',
                'Confirm authorization for large amounts',
                'Check for proper approval signatures'
            ],
            'duplicate_invoice': [
                'Review original invoices for duplicates',
                'Contact vendor to confirm legitimacy',
                'Check payment status to avoid double payment'
            ]
        }
        return actions.get(alert['type'], ['Investigate the transaction thoroughly'])

    def _load_detection_rules(self) -> Dict:
        """Load anomaly detection rules"""
        return {
            'amount_threshold': 100000,  # ₹1 lakh
            'frequency_threshold': 20,    # transactions per day
            'z_score_threshold': 3.0,
            'date_range_days': 90         # analysis period
        }

    # Helper methods for data retrieval and processing...