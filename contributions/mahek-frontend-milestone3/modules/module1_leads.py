from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import Lead

def create_lead(db: Session, lead_data: dict) -> Lead:
    lead = Lead(
        company_name=(lead_data.get("company_name") or "").strip(),
        industry=(lead_data.get("industry") or "Technology").strip(),
        contact_name=(lead_data.get("contact_name") or "").strip(),
        email=(lead_data.get("email") or "").strip(),
        phone=(lead_data.get("phone") or "").strip(),
        company_size=(lead_data.get("company_size") or "100-250 employees").strip(),
        funding_stage=(lead_data.get("funding_stage") or "Growth").strip(),
        business_need=(lead_data.get("business_need") or "").strip(),
        lead_status=(lead_data.get("lead_status") or "New").strip()
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

def get_leads(db: Session, skip: int = 0, limit: int = 100) -> List[Lead]:
    return db.query(Lead).order_by(Lead.lead_id.desc()).offset(skip).limit(limit).all()

def get_lead_by_id(db: Session, lead_id: int) -> Optional[Lead]:
    return db.query(Lead).filter(Lead.lead_id == lead_id).first()

def update_lead(db: Session, lead_id: int, lead_data: dict) -> Optional[Lead]:
    lead = get_lead_by_id(db, lead_id)
    if not lead:
        return None
    for key, value in lead_data.items():
        if hasattr(lead, key) and value is not None:
            setattr(lead, key, value)
    db.commit()
    db.refresh(lead)
    return lead

def delete_lead(db: Session, lead_id: int) -> bool:
    lead = get_lead_by_id(db, lead_id)
    if not lead:
        return False
    db.delete(lead)
    db.commit()
    return True

def bulk_create_leads(db: Session, leads_list: List[dict]) -> List[Lead]:
    created = []
    for item in leads_list:
        lead = Lead(
            company_name=(item.get("company_name") or "").strip(),
            industry=(item.get("industry") or "Technology").strip(),
            contact_name=(item.get("contact_name") or "").strip(),
            email=(item.get("email") or "").strip(),
            phone=(item.get("phone") or "").strip(),
            company_size=(item.get("company_size") or "100-250 employees").strip(),
            funding_stage=(item.get("funding_stage") or "Growth").strip(),
            business_need=(item.get("business_need") or "").strip(),
            lead_status=(item.get("lead_status") or "New").strip()
        )
        db.add(lead)
        created.append(lead)
    db.commit()
    for lead in created:
        db.refresh(lead)
    return created

def seed_sample_leads(db: Session):
    if db.query(Lead).count() == 0:
        samples = [
            {
                "company_name": "TechCorp Solutions",
                "industry": "Enterprise Software",
                "contact_name": "Sarah Johnson",
                "email": "sarah@techcorp.com",
                "phone": "+1234567890",
                "company_size": "250-500 employees",
                "funding_stage": "Series C",
                "business_need": "Scaling data operations efficiently and reducing cloud costs",
                "lead_status": "Qualified"
            },
            {
                "company_name": "InnovateAI Labs",
                "industry": "Artificial Intelligence",
                "contact_name": "Mark Chen",
                "email": "mark@innovateai.com",
                "phone": "+9876543210",
                "company_size": "50-100 employees",
                "funding_stage": "Series A",
                "business_need": "Building AI pipelines faster with robust ML deployment",
                "lead_status": "Contacted"
            },
            {
                "company_name": "CloudScale Inc",
                "industry": "Cloud Computing",
                "contact_name": "Robert Law",
                "email": "robert@cloudscale.com",
                "phone": "+1122334455",
                "company_size": "100-250 employees",
                "funding_stage": "Series B",
                "business_need": "Reducing cloud infrastructure costs and optimizing AWS spend",
                "lead_status": "Proposal Sent"
            }
        ]
        bulk_create_leads(db, samples)
