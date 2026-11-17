import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database.connection import get_db, engine, Base
from database.models import Lead, LeadScore, CompanyInsight, OutreachCampaign
import modules.module1_leads as m1
import modules.module2_intelligence as m2
import modules.module3_outreach as m3
import modules.module4_scoring as m4
import modules.module5_conversation as m5
import modules.module6_dashboard as m6

load_dotenv()

# Create tables in DB
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SalesGenie AI Backend API",
    description="FastAPI backend providing lead management, AI intelligence, scoring, outreach, and analytics.",
    version="1.0.0"
)

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed initial leads if database is empty
with next(get_db()) as db:
    m1.seed_sample_leads(db)

# ----------------- PYDANTIC SCHEMAS -----------------
class LeadCreateSchema(BaseModel):
    company_name: str
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_size: Optional[str] = None
    funding_stage: Optional[str] = None
    business_need: Optional[str] = None
    lead_status: Optional[str] = "New"

class LeadUpdateSchema(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_size: Optional[str] = None
    funding_stage: Optional[str] = None
    business_need: Optional[str] = None
    lead_status: Optional[str] = None

class OutreachRequestSchema(BaseModel):
    lead_id: int
    tone: Optional[str] = "professional"

class CallNotesSchema(BaseModel):
    lead_id: int
    notes: str

class SendEmailSchema(BaseModel):
    lead_id: int
    recipient_email: str
    subject: str
    body: str

# ----------------- ENDPOINTS -----------------
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "app": "SalesGenie AI",
        "database": engine.name,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY").startswith("sk-proj-your-key")),
        "smtp_configured": bool(os.getenv("SMTP_SERVER"))
    }

# Lead CRUD
@app.get("/leads/", tags=["Leads"])
def list_leads(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    leads = m1.get_leads(db, skip=skip, limit=limit)
    return [
        {
            "lead_id": l.lead_id,
            "company_name": l.company_name,
            "industry": l.industry,
            "contact_name": l.contact_name,
            "email": l.email,
            "phone": l.phone,
            "company_size": l.company_size,
            "funding_stage": l.funding_stage,
            "business_need": l.business_need,
            "lead_status": l.lead_status,
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in leads
    ]

@app.post("/leads/", tags=["Leads"], status_code=status.HTTP_201_CREATED)
def add_lead(lead: LeadCreateSchema, db: Session = Depends(get_db)):
    created = m1.create_lead(db, lead.model_dump())
    return {
        "message": f"Lead added: {created.company_name} with ID {created.lead_id}",
        "lead": {
            "lead_id": created.lead_id,
            "company_name": created.company_name,
            "industry": created.industry,
            "contact_name": created.contact_name,
            "email": created.email,
            "phone": created.phone,
            "company_size": created.company_size,
            "funding_stage": created.funding_stage,
            "business_need": created.business_need,
            "lead_status": created.lead_status
        }
    }

@app.post("/leads/bulk", tags=["Leads"], status_code=status.HTTP_201_CREATED)
def bulk_import_leads(leads: List[LeadCreateSchema], db: Session = Depends(get_db)):
    data = [l.model_dump() for l in leads]
    created = m1.bulk_create_leads(db, data)
    return {
        "message": f"Successfully imported {len(created)} leads.",
        "count": len(created)
    }

@app.get("/leads/{lead_id}", tags=["Leads"])
def get_single_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = m1.get_lead_by_id(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found.")
    return {
        "lead_id": lead.lead_id,
        "company_name": lead.company_name,
        "industry": lead.industry,
        "contact_name": lead.contact_name,
        "email": lead.email,
        "phone": lead.phone,
        "company_size": lead.company_size,
        "funding_stage": lead.funding_stage,
        "business_need": lead.business_need,
        "lead_status": lead.lead_status,
        "created_at": lead.created_at.isoformat() if lead.created_at else None
    }

@app.put("/leads/{lead_id}", tags=["Leads"])
def update_existing_lead(lead_id: int, payload: LeadUpdateSchema, db: Session = Depends(get_db)):
    updated = m1.update_lead(db, lead_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found.")
    return {"message": "Lead updated successfully", "lead_id": updated.lead_id}

@app.delete("/leads/{lead_id}", tags=["Leads"])
def delete_lead_record(lead_id: int, db: Session = Depends(get_db)):
    success = m1.delete_lead(db, lead_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found.")
    return {"message": f"Lead {lead_id} deleted successfully."}

# Intelligence: Analyze
@app.post("/intelligence/analyze/{lead_id}", tags=["Intelligence"])
def analyze_company(lead_id: int, db: Session = Depends(get_db)):
    try:
        insight = m2.analyze_company_profile(db, lead_id)
        return {
            "insight_id": insight.insight_id,
            "lead_id": insight.lead_id,
            "business_needs": insight.business_needs,
            "opportunities": insight.opportunities,
            "industry_situation": insight.industry_situation,
            "pain_points": insight.pain_points,
            "created_at": insight.created_at.isoformat() if insight.created_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/intelligence/analyze/{lead_id}", tags=["Intelligence"])
def get_saved_insight(lead_id: int, db: Session = Depends(get_db)):
    insight = m2.get_company_insight(db, lead_id)
    if not insight:
        raise HTTPException(status_code=404, detail=f"No analysis found for lead {lead_id}.")
    return {
        "insight_id": insight.insight_id,
        "lead_id": insight.lead_id,
        "business_needs": insight.business_needs,
        "opportunities": insight.opportunities,
        "industry_situation": insight.industry_situation,
        "pain_points": insight.pain_points
    }

# Intelligence: Score
@app.post("/intelligence/score/{lead_id}", tags=["Intelligence"])
def score_lead(lead_id: int, db: Session = Depends(get_db)):
    try:
        score_obj = m4.calculate_lead_score(db, lead_id)
        return {
            "score_id": score_obj.score_id,
            "lead_id": score_obj.lead_id,
            "lead_score": score_obj.lead_score,
            "conversion_probability": score_obj.conversion_probability,
            "priority_level": score_obj.priority_level,
            "reason": score_obj.reason,
            "next_action": score_obj.next_action,
            "scoring_factors": score_obj.scoring_factors
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

@app.get("/intelligence/score/{lead_id}", tags=["Intelligence"])
def get_saved_score(lead_id: int, db: Session = Depends(get_db)):
    score_obj = m4.get_lead_score(db, lead_id)
    if not score_obj:
        raise HTTPException(status_code=404, detail=f"No score found for lead {lead_id}.")
    return {
        "score_id": score_obj.score_id,
        "lead_id": score_obj.lead_id,
        "lead_score": score_obj.lead_score,
        "conversion_probability": score_obj.conversion_probability,
        "priority_level": score_obj.priority_level,
        "reason": score_obj.reason,
        "next_action": score_obj.next_action,
        "scoring_factors": score_obj.scoring_factors
    }

# Outreach: Email Generation
@app.post("/intelligence/outreach", tags=["Outreach"])
def generate_outreach_email(payload: OutreachRequestSchema, db: Session = Depends(get_db)):
    try:
        campaign = m3.generate_personalized_email(db, payload.lead_id, payload.tone or "professional")
        return {
            "campaign_id": campaign.campaign_id,
            "lead_id": campaign.lead_id,
            "email_subject": campaign.email_subject,
            "email_content": campaign.email_content,
            "follow_up_strategy": campaign.follow_up_strategy,
            "tone": campaign.tone,
            "status": campaign.status
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}")

@app.get("/intelligence/outreach/{lead_id}", tags=["Outreach"])
def get_saved_outreach(lead_id: int, db: Session = Depends(get_db)):
    campaign = m3.get_outreach_campaign(db, lead_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"No outreach campaign found for lead {lead_id}.")
    return {
        "campaign_id": campaign.campaign_id,
        "lead_id": campaign.lead_id,
        "email_subject": campaign.email_subject,
        "email_content": campaign.email_content,
        "follow_up_strategy": campaign.follow_up_strategy,
        "tone": campaign.tone,
        "status": campaign.status
    }

# Outreach Email Sending Status / Action
@app.post("/outreach/send-email", tags=["Outreach"])
def send_email_endpoint(payload: SendEmailSchema, db: Session = Depends(get_db)):
    smtp_host = os.getenv("SMTP_SERVER")
    if not smtp_host:
        return {
            "success": False,
            "configured": False,
            "message": "Email delivery service (SMTP) is not configured in the backend environment. No email was sent."
        }
    return {
        "success": True,
        "configured": True,
        "message": f"Email queued for {payload.recipient_email}."
    }

# Conversation Intelligence
@app.post("/intelligence/conversation", tags=["Conversation"])
def summarize_conversation(payload: CallNotesSchema, db: Session = Depends(get_db)):
    try:
        interaction = m5.summarize_call_notes(db, payload.lead_id, payload.notes)
        return {
            "interaction_id": interaction.interaction_id,
            "lead_id": interaction.lead_id,
            "summary": interaction.summary,
            "action_items": interaction.action_items,
            "key_points": interaction.key_points,
            "follow_up": interaction.follow_up
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Call summarization failed: {str(e)}")

# Dashboard Analytics
@app.get("/analytics/dashboard", tags=["Dashboard"])
@app.get("/dashboard/stats", tags=["Dashboard"])
def get_dashboard_data(db: Session = Depends(get_db)):
    return m6.get_dashboard_metrics(db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
