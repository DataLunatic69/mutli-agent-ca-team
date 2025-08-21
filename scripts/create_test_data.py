

from src.ca_multi_agent.db.session import SyncSessionLocal
from src.ca_multi_agent.models.user_org import Organization, User
from src.ca_multi_agent.models.accounting import ChartOfAccounts

def create_test_data():
    """Create test data for development"""
    db = SyncSessionLocal()
    
    try:
        # Create test organization
        org = Organization(
            name="Test Company Pvt Ltd",
            legal_name="Test Company Private Limited",
            tax_id="ABCDE1234F",
            gstin="27ABCDE1234F1Z5",
            industry_code="IT_SERVICES",
            address={
                "street": "123 Business Street",
                "city": "Mumbai",
                "state": "MH",
                "pincode": "400001"
            }
        )
        db.add(org)
        db.flush()
        
        # Create test user
        user = User(
            email="admin@testcompany.com",
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
            full_name="Admin User",
            is_superuser=True,
            organization_id=org.id
        )
        db.add(user)
        
        # Create chart of accounts
        accounts = [
            {"code": "SALES", "name": "Sales Revenue", "type": "Income"},
            {"code": "BANK", "name": "Bank Account", "type": "Asset"},
            {"code": "CASH", "name": "Cash in Hand", "type": "Asset"},
            {"code": "SALARIES", "name": "Salaries Expense", "type": "Expense"},
            {"code": "RENT", "name": "Rent Expense", "type": "Expense"},
            {"code": "GST_PAYABLE", "name": "GST Payable", "type": "Liability"},
            {"code": "GST_RECEIVABLE", "name": "GST Receivable", "type": "Asset"}
        ]
        
        for acc in accounts:
            coa = ChartOfAccounts(
                org_id=org.id,
                code=acc["code"],
                name=acc["name"],
                type=acc["type"],
                is_active=True
            )
            db.add(coa)
        
        db.commit()
        print("✅ Test data created successfully!")
        print(f"Organization ID: {org.id}")
        print(f"User email: admin@testcompany.com")
        print(f"Password: secret")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating test data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()