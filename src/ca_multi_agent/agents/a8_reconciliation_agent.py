from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, date, timedelta
import logging
from dateutil import rrule
import holidays

from .base import BaseAgent
from ..models.compliance import ComplianceTask, ComplianceRule

logger = logging.getLogger(__name__)

class ComplianceAgent(BaseAgent):
    def __init__(self, db_session):
        super().__init__("A8_Compliance_Calendar")
        self.db = db_session
        self.india_holidays = holidays.India()
        
        # Predefined compliance rules for Indian regulations
        self.default_rules = [
            {
                'name': 'GSTR-1 Monthly Filing',
                'description': 'Monthly return for outward supplies',
                'rule_type': 'tax',
                'frequency': 'monthly',
                'due_date_rule': {'day_of_month': 11, 'adjust_weekend': True},
                'jurisdiction': 'india'
            },
            {
                'name': 'GSTR-3B Monthly Filing',
                'description': 'Monthly summary return with tax payment',
                'rule_type': 'tax', 
                'frequency': 'monthly',
                'due_date_rule': {'day_of_month': 20, 'adjust_weekend': True},
                'jurisdiction': 'india'
            },
            {
                'name': 'TDS Quarterly Return',
                'description': 'Quarterly TDS return filing',
                'rule_type': 'tax',
                'frequency': 'quarterly', 
                'due_date_rule': {'month': [1,4,7,10], 'day_of_month': 31, 'adjust_weekend': True},
                'jurisdiction': 'india'
            },
            {
                'name': 'Income Tax Advance Payment',
                'description': 'Advance tax installment payments',
                'rule_type': 'tax',
                'frequency': 'quarterly',
                'due_date_rule': {'month': [6,9,12,3], 'day_of_month': 15, 'adjust_weekend': True},
                'jurisdiction': 'india'
            }
        ]

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        org_id = input_data.get('org_id')
        entity_type = input_data.get('entity_type', 'company')
        state = input_data.get('state', 'MH')
        fy = input_data.get('fy', '2024-25')
        
        if not org_id:
            raise ValueError("Organization ID is required")
        
        # Ensure compliance rules exist
        await self._ensure_compliance_rules(org_id, entity_type, state)
        
        # Generate compliance tasks for the period
        tasks = await self._generate_compliance_tasks(org_id, fy, entity_type, state)
        
        # Get upcoming tasks
        upcoming_tasks = await self._get_upcoming_tasks(org_id, days_ahead=30)
        
        # Generate calendar file
        calendar_url = await self._generate_calendar_file(org_id, fy)
        
        return {
            'success': True,
            'org_id': org_id,
            'financial_year': fy,
            'tasks_generated': len(tasks),
            'upcoming_tasks': len(upcoming_tasks),
            'tasks': tasks,
            'next_actions': self._get_next_actions(upcoming_tasks),
            'calendar_ics_url': calendar_url,
            'compliance_score': await self._calculate_compliance_score(org_id),
            'timestamp': datetime.now().isoformat()
        }

    async def _ensure_compliance_rules(self, org_id: uuid.UUID, entity_type: str, state: str):
        """Ensure compliance rules exist for the organization"""
        existing_rules = self.db.query(ComplianceRule).filter(
            ComplianceRule.org_id == org_id
        ).count()
        
        if existing_rules == 0:
            # Create default rules
            for rule_data in self.default_rules:
                rule = ComplianceRule(
                    org_id=org_id,
                    **rule_data
                )
                self.db.add(rule)
            self.db.commit()

    async def _generate_compliance_tasks(self, org_id: uuid.UUID, fy: str, entity_type: str, state: str) -> List[Dict]:
        """Generate compliance tasks for the financial year"""
        tasks = []
        rules = self.db.query(ComplianceRule).filter(
            ComplianceRule.org_id == org_id,
            ComplianceRule.is_active == True
        ).all()
        
        # Parse financial year
        start_year = int(fy.split('-')[0])
        start_date = date(start_year, 4, 1)
        end_date = date(start_year + 1, 3, 31)
        
        for rule in rules:
            due_dates = self._calculate_due_dates(rule, start_date, end_date, state)
            
            for due_date in due_dates:
                task = ComplianceTask(
                    org_id=org_id,
                    title=f"{rule.name} - {due_date.strftime('%b %Y')}",
                    description=rule.description,
                    due_date=due_date,
                    task_type=rule.rule_type,
                    priority=self._determine_priority(rule, due_date),
                    metadata={
                        'rule_id': str(rule.id),
                        'frequency': rule.frequency,
                        'jurisdiction': rule.jurisdiction
                    }
                )
                self.db.add(task)
                tasks.append({
                    'title': task.title,
                    'due_date': task.due_date.isoformat(),
                    'priority': task.priority,
                    'type': task.task_type
                })
        
        self.db.commit()
        return tasks

    def _calculate_due_dates(self, rule: ComplianceRule, start_date: date, end_date: date, state: str) -> List[date]:
        """Calculate due dates based on rule frequency"""
        due_dates = []
        
        if rule.frequency == 'monthly':
            for dt in rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date):
                due_date = self._apply_due_date_rule(rule.due_date_rule, dt, state)
                due_dates.append(due_date)
                
        elif rule.frequency == 'quarterly':
            for dt in rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date):
                if dt.month in rule.due_date_rule.get('month', [3,6,9,12]):
                    due_date = self._apply_due_date_rule(rule.due_date_rule, dt, state)
                    due_dates.append(due_date)
        
        return due_dates

    def _apply_due_date_rule(self, due_date_rule: Dict, base_date: date, state: str) -> date:
        """Apply due date rules considering weekends and holidays"""
        day_of_month = due_date_rule.get('day_of_month', 1)
        adjust_weekend = due_date_rule.get('adjust_weekend', False)
        
        # Create due date
        due_date = base_date.replace(day=day_of_month)
        
        # Adjust for weekends if needed
        if adjust_weekend:
            due_date = self._adjust_for_weekend(due_date)
        
        # Adjust for holidays
        due_date = self._adjust_for_holidays(due_date, state)
        
        return due_date

    def _adjust_for_weekend(self, due_date: date) -> date:
        """Adjust due date to avoid weekends"""
        if due_date.weekday() == 5:  # Saturday
            return due_date - timedelta(days=1)
        elif due_date.weekday() == 6:  # Sunday
            return due_date + timedelta(days=1)
        return due_date

    def _adjust_for_holidays(self, due_date: date, state: str) -> date:
        """Adjust due date for state-specific holidays"""
        state_holidays = getattr(self.india_holidays, f'{state}_holidays', {})
        
        while due_date in state_holidays:
            due_date += timedelta(days=1)
        
        return due_date

    async def _get_upcoming_tasks(self, org_id: uuid.UUID, days_ahead: int = 30) -> List[Dict]:
        """Get tasks due in the next specified days"""
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        tasks = self.db.query(ComplianceTask).filter(
            ComplianceTask.org_id == org_id,
            ComplianceTask.due_date >= today,
            ComplianceTask.due_date <= end_date,
            ComplianceTask.status.in_(['pending', 'in_progress'])
        ).order_by(ComplianceTask.due_date).all()
        
        return [{
            'id': str(task.id),
            'title': task.title,
            'due_date': task.due_date.isoformat(),
            'priority': task.priority,
            'status': task.status
        } for task in tasks]

    def _get_next_actions(self, upcoming_tasks: List[Dict]) -> List[Dict]:
        """Get recommended next actions based on upcoming tasks"""
        actions = []
        
        for task in upcoming_tasks:
            days_until_due = (date.fromisoformat(task['due_date']) - date.today()).days
            
            if days_until_due <= 7:
                actions.append({
                    'task_id': task['id'],
                    'action': 'URGENT: Complete filing',
                    'due_in_days': days_until_due,
                    'priority': 'critical'
                })
            elif days_until_due <= 14:
                actions.append({
                    'task_id': task['id'],
                    'action': 'Prepare documents for filing',
                    'due_in_days': days_until_due,
                    'priority': 'high'
                })
            else:
                actions.append({
                    'task_id': task['id'],
                    'action': 'Schedule preparation',
                    'due_in_days': days_until_due,
                    'priority': 'medium'
                })
        
        return actions

    async def _generate_calendar_file(self, org_id: uuid.UUID, fy: str) -> str:
        """Generate ICS calendar file for compliance dates"""
        # This would generate actual ICS file in production
        return f"/api/v1/calendar/{org_id}/{fy}.ics"

    async def _calculate_compliance_score(self, org_id: uuid.UUID) -> float:
        """Calculate organization's compliance score"""
        total_tasks = self.db.query(ComplianceTask).filter(
            ComplianceTask.org_id == org_id
        ).count()
        
        completed_tasks = self.db.query(ComplianceTask).filter(
            ComplianceTask.org_id == org_id,
            ComplianceTask.status == 'completed'
        ).count()
        
        if total_tasks == 0:
            return 100.0
        
        return (completed_tasks / total_tasks) * 100

    async def add_custom_deadline(self, org_id: uuid.UUID, deadline_data: Dict) -> Dict:
        """Add custom compliance deadline"""
        task = ComplianceTask(
            org_id=org_id,
            title=deadline_data['title'],
            description=deadline_data.get('description', ''),
            due_date=date.fromisoformat(deadline_data['due_date']),
            task_type=deadline_data.get('type', 'custom'),
            priority=deadline_data.get('priority', 'medium'),
            metadata=deadline_data.get('metadata', {})
        )
        
        self.db.add(task)
        self.db.commit()
        
        return {
            'task_id': str(task.id),
            'title': task.title,
            'due_date': task.due_date.isoformat(),
            'status': task.status
        }