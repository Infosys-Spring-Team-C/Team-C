from __future__ import annotations
import csv, io, os
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.db import Base, SessionLocal, engine, Lead, LeadScore, CompanyInsight, OutreachCampaign, SalesInteraction, CRMSyncLog
from ai.providers import create_provider
from ai.graph import run_workflow
from utils.config import get_settings

app = FastAPI(title="SalesGenie AI API", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

class LeadWrite(BaseModel):
    company_name: str = Field(min_length=1, max_length=240)
    industry: str = ""; contact_name: str = ""; email: str = ""; phone: str = ""; website: str = ""
    company_size: str = ""; company_description: str = ""; prospect_role: str = ""; status: str = "New"
    stage: str = "Prospecting"; engagement_history: str = ""; explicit_needs: str = ""; response_behavior: str = ""; user_research: str = ""
    funding_stage: str = ""; tech_stack: str = ""; pain_points: str = ""; lead_source: str = ""

class LeadPatch(BaseModel):
    company_name: str | None = None; industry: str | None = None; contact_name: str | None = None; email: str | None = None
    phone: str | None = None; website: str | None = None; company_size: str | None = None; company_description: str | None = None
    prospect_role: str | None = None; status: str | None = None; stage: str | None = None; engagement_history: str | None = None
    explicit_needs: str | None = None; response_behavior: str | None = None; user_research: str | None = None

def lead_dict(row: Lead):
    return {"id":str(row.id),"company_name":row.company_name,"industry":row.industry,"contact_name":row.contact_name,"email":row.email,
      "phone":row.phone,"website":row.company_website,"company_size":row.company_size,"company_description":row.business_need,
      "prospect_role":row.decision_maker_status,"status":row.lead_status.title(),"stage":row.lead_status.title(),"engagement_history":row.engagement_level,
      "explicit_needs":row.business_need,"response_behavior":"","user_research":row.pain_points,"funding_stage":row.funding_stage,
      "tech_stack":row.tech_stack,"pain_points":row.pain_points,"lead_source":row.lead_source,"created_at":row.created_at.isoformat() if row.created_at else None}

def validate_state(s):
    allowed={"new","contacted","qualified","proposal","negotiation","converted","unqualified","lost"}
    aliases={"active":"contacted","prospecting":"new","discovery":"contacted","closed won":"converted","closed lost":"lost"}
    s=(s or "new").strip().lower(); s=aliases.get(s,s)
    if s not in allowed: raise HTTPException(422, "Invalid lead lifecycle status")
    return s

def validate_transition(current, target):
    transitions={"new":{"new","contacted","qualified","unqualified","lost"},
      "contacted":{"contacted","qualified","unqualified","lost"},
      "qualified":{"qualified","proposal","negotiation","converted","lost"},
      "proposal":{"proposal","negotiation","converted","lost"},
      "negotiation":{"negotiation","converted","lost"},
      "converted":{"converted"},"unqualified":{"unqualified"},"lost":{"lost"}}
    if target not in transitions.get(current,set()): raise HTTPException(422,f"Invalid lead lifecycle transition: {current} to {target}")
    return target

@app.get("/api/v1/health")
def health(): return {"status":"ok","mode":"local","database":"configured"}

@app.post("/api/v1/leads", status_code=201)
@app.post("/api/v1/leads/", status_code=201)
def create_lead(body: LeadWrite, db: Session=Depends(get_db)):
    data=body.model_dump(); email=data["email"].strip().lower()
    if email and db.scalar(select(Lead).where(func.lower(Lead.email)==email)):
        raise HTTPException(409,"A lead with this email already exists")
    company=data["company_name"].strip()
    status=validate_state(data["stage"] or data["status"])
    row=Lead(company_name=company, industry=data["industry"], contact_name=data["contact_name"], email=email,
      phone=data["phone"], company_website=data["website"], company_size=data["company_size"], funding_stage=data["funding_stage"],
      tech_stack=data["tech_stack"], business_need=data["explicit_needs"] or data["company_description"], pain_points=data["pain_points"] or data["user_research"],
      lead_source=data["lead_source"], lead_status=status, decision_maker_status=data["prospect_role"], engagement_level=data["engagement_history"] or "unknown")
    db.add(row)
    try: db.commit(); db.refresh(row)
    except Exception: db.rollback(); raise HTTPException(500,"Could not save lead")
    return lead_dict(row)

@app.get("/api/v1/leads")
@app.get("/api/v1/leads/")
def list_leads(query: str="", status: str="", stage: str="", industry: str="", page: int=Query(1,ge=1), page_size: int=Query(100,ge=1,le=500), db: Session=Depends(get_db)):
    stmt=select(Lead)
    if query.strip():
        q=f"%{query.strip().lower()}%"; stmt=stmt.where(func.lower(Lead.company_name).like(q)|func.lower(Lead.contact_name).like(q)|func.lower(Lead.email).like(q)|func.lower(Lead.industry).like(q))
    if industry: stmt=stmt.where(func.lower(Lead.industry)==industry.lower())
    if status or stage: stmt=stmt.where(Lead.lead_status==validate_state(stage or status))
    return [lead_dict(x) for x in db.scalars(stmt.order_by(Lead.id).offset((page-1)*page_size).limit(page_size)).all()]

@app.get("/api/v1/leads/{lead_id}")
def get_lead(lead_id: int, db: Session=Depends(get_db)):
    row=db.get(Lead,lead_id)
    if not row: raise HTTPException(404,"Lead not found")
    return lead_dict(row)

@app.patch("/api/v1/leads/{lead_id}")
@app.put("/api/v1/leads/{lead_id}")
def update_lead(lead_id: int, body: LeadPatch, db: Session=Depends(get_db)):
    row=db.get(Lead,lead_id)
    if not row: raise HTTPException(404,"Lead not found")
    values=body.model_dump(exclude_unset=True)
    mapping={"website":"company_website","company_description":"business_need","explicit_needs":"business_need","prospect_role":"decision_maker_status","engagement_history":"engagement_level","user_research":"pain_points"}
    if "stage" in values or "status" in values: row.lead_status=validate_transition(row.lead_status,validate_state(values.get("stage") or values.get("status")))
    for k,v in values.items():
        if k not in {"stage","status"} and v is not None: setattr(row,mapping.get(k,k),v)
    if row.email: row.email=row.email.strip().lower()
    try: db.commit(); db.refresh(row)
    except Exception: db.rollback(); raise HTTPException(409,"Update conflicts with existing data")
    return lead_dict(row)

@app.delete("/api/v1/leads/{lead_id}",status_code=204)
def delete_lead(lead_id:int,db:Session=Depends(get_db)):
    row=db.get(Lead,lead_id)
    if not row: raise HTTPException(404,"Lead not found")
    db.delete(row); db.commit()

@app.post("/api/v1/leads/import")
def import_csv(file: UploadFile=File(...),db:Session=Depends(get_db)):
    try: text=file.file.read(5_000_001).decode("utf-8-sig")
    except Exception as exc: raise HTTPException(400,"CSV must be valid UTF-8") from exc
    if len(text)>5_000_000: raise HTTPException(413,"CSV exceeds 5 MB limit")
    reader=csv.DictReader(io.StringIO(text))
    headers={str(x or "").strip().lower() for x in (reader.fieldnames or [])}
    if not headers.intersection({"company_name","company","company name","account name"}): raise HTTPException(422,"CSV needs a company_name, company, or account name column")
    imported=0; duplicate=0; invalid=[]; seen=set()
    for n,r in enumerate(reader,start=2):
        r={str(k or "").strip().lower():str(v or "").strip() for k,v in r.items()}
        company=r.get("company_name") or r.get("company") or r.get("company name") or r.get("account name")
        email=r.get("email","").lower(); key=email or company.casefold()
        if not company: invalid.append({"row":n,"error":"Company name is required"}); continue
        if key in seen or (email and db.scalar(select(Lead.id).where(func.lower(Lead.email)==email))): duplicate+=1; continue
        seen.add(key)
        try:
            lead=Lead(company_name=company,contact_name=r.get("contact_name") or r.get("contact name") or r.get("contact", ""),email=email,
              industry=r.get("industry",""),company_website=r.get("website", ""),company_size=r.get("company_size", ""),
              business_need=r.get("explicit_needs") or r.get("business_need", ""),pain_points=r.get("pain_points", ""),lead_status="new")
            db.add(lead); db.flush(); imported+=1
        except Exception as exc: db.rollback(); raise HTTPException(400,f"Import failed at row {n}: {exc}")
    db.commit(); return {"imported":imported,"duplicate":duplicate,"skipped":duplicate,"invalid":len(invalid),"errors":invalid,"filename":file.filename}

def ai_work(op,request):
    response=run_workflow(op,request,create_provider(get_settings()))
    if response.errors: raise HTTPException(502,"AI workflow failed: "+"; ".join(response.errors))
    return response

@app.post("/api/v1/intelligence/analyze/{lead_id}")
@app.post("/api/v1/leads/{lead_id}/insights")
def analyze(lead_id:int,body:dict[str,Any]|None=None,db:Session=Depends(get_db)):
    row=db.get(Lead,lead_id)
    if not row: raise HTTPException(404,"Lead not found")
    if body and body.get("research"):
        model=body["research"]
        provider=(body.get("execution") or {}).get("provider","local-ui")
        model_name=(body.get("execution") or {}).get("model","")
    else:
        result=ai_work("lead_intelligence",{"lead":lead_dict(row)}); model=result.research.model_dump() if result.research else {}
        provider=result.execution.provider; model_name=result.execution.model
    obj=CompanyInsight(lead_id=lead_id,business_needs=model.get("possible_needs",[]),opportunities=model.get("opportunities",[]),pain_points=model.get("potential_challenges",[]),
      industry_context=model.get("company_overview",""),recommended_value_proposition=model.get("product_industry_fit",""),supporting_evidence=[x.model_dump() if hasattr(x,"model_dump") else x for x in model.get("supported_facts",[])],provider=provider,model=model_name)
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id":obj.id,"lead_id":lead_id,**model}

@app.get("/api/v1/intelligence/{lead_id}")
def get_intelligence(lead_id:int,db:Session=Depends(get_db)):
    return db.scalars(select(CompanyInsight).where(CompanyInsight.lead_id==lead_id).order_by(CompanyInsight.id.desc())).all()

@app.post("/api/v1/scoring/{lead_id}")
@app.post("/api/v1/leads/{lead_id}/scores")
def score_lead(lead_id:int,body:dict[str,Any]|None=None,db:Session=Depends(get_db)):
    row=db.get(Lead,lead_id)
    if not row: raise HTTPException(404,"Lead not found")
    if body and body.get("score"):
        data=body["score"]
    else:
        from ai.scoring.rule_based import calculate_lead_score
        data=calculate_lead_score(lead_dict(row)).model_dump()
    obj=LeadScore(lead_id=lead_id,lead_score=data["score"],priority_level="hot" if data["score"]>=70 else "warm" if data["score"]>=45 else "cold", scoring_factors=data, explanation=data.get("methodology_note",""))
    db.add(obj); db.commit(); db.refresh(obj); return {"id":obj.id,**data,"created_at":obj.created_at.isoformat()}

@app.get("/api/v1/scoring/{lead_id}")
def get_scores(lead_id:int,db:Session=Depends(get_db)):
    return db.scalars(select(LeadScore).where(LeadScore.lead_id==lead_id).order_by(LeadScore.id.desc())).all()

@app.post("/api/v1/outreach/generate")
def generate_outreach(body:dict[str,Any],db:Session=Depends(get_db)):
    lead_id=int(body.get("lead_id",0)); lead=db.get(Lead,lead_id)
    if not lead: raise HTTPException(404,"Lead not found")
    if body.get("body"):
        draft=body; provider="local-ui"
    else:
        result=ai_work("outreach",{"lead":lead_dict(lead),**body}); draft=result.result.model_dump(); provider=result.execution.provider
    obj=OutreachCampaign(lead_id=lead_id,email_subject=draft.get("subject_line") or "",email_content=draft["body"],tone=body.get("tone","professional"),email_type=draft.get("channel","Email"),campaign_goal=body.get("campaign_objective",""),provider=provider)
    db.add(obj); db.commit(); db.refresh(obj); return {"id":obj.id,"lead_id":lead_id,**draft,"status":"draft"}

@app.get("/api/v1/outreach/{lead_id}")
@app.get("/api/v1/leads/{lead_id}/outreach-drafts")
def list_outreach(lead_id:int,db:Session=Depends(get_db)):
    return [{"id":x.id,"lead_id":x.lead_id,"subject_line":x.email_subject,"body":x.email_content,"status":x.status} for x in db.scalars(select(OutreachCampaign).where(OutreachCampaign.lead_id==lead_id).order_by(OutreachCampaign.id.desc())).all()]

@app.get("/api/v1/outreach/campaigns/{campaign_id}")
def get_campaign(campaign_id:int,db:Session=Depends(get_db)):
    x=db.get(OutreachCampaign,campaign_id)
    if not x: raise HTTPException(404,"Outreach draft not found")
    return {"id":x.id,"lead_id":x.lead_id,"subject_line":x.email_subject,"body":x.email_content,"tone":x.tone,"status":x.status,"created_at":x.created_at.isoformat()}

@app.patch("/api/v1/outreach/campaigns/{campaign_id}")
def patch_campaign(campaign_id:int,body:dict[str,Any],db:Session=Depends(get_db)):
    x=db.get(OutreachCampaign,campaign_id)
    if not x: raise HTTPException(404,"Outreach draft not found")
    if "subject_line" in body: x.email_subject=str(body["subject_line"])[:500]
    if "email_subject" in body: x.email_subject=str(body["email_subject"])[:500]
    if "body" in body: x.email_content=str(body["body"])
    if "email_content" in body: x.email_content=str(body["email_content"])
    if "tone" in body: x.tone=str(body["tone"])[:60]
    db.commit(); db.refresh(x)
    return {"id":x.id,"lead_id":x.lead_id,"subject_line":x.email_subject,"body":x.email_content,"status":x.status}

@app.post("/api/v1/leads/{lead_id}/outreach-drafts")
def save_outreach(lead_id:int,body:dict[str,Any],db:Session=Depends(get_db)):
    if not db.get(Lead,lead_id): raise HTTPException(404,"Lead not found")
    draft=body.get("draft",body); obj=OutreachCampaign(lead_id=lead_id,email_subject=draft.get("subject_line", ""),email_content=draft.get("body", ""),provider=draft.get("provider","mock"))
    db.add(obj); db.commit(); db.refresh(obj); return {"id":obj.id,"lead_id":lead_id,"status":"draft"}

@app.post("/api/v1/conversations/summarize")
def summarize(body:dict[str,Any],db:Session=Depends(get_db)):
    lead_id=int(body.get("lead_id",0)); row=db.get(Lead,lead_id)
    if not row: raise HTTPException(404,"Lead not found")
    if len(str(body.get("transcript","")))>42000: raise HTTPException(413,"Transcript exceeds 42,000 characters")
    result=ai_work("conversation",body); summary=result.result.model_dump()
    obj=SalesInteraction(lead_id=lead_id,interaction_type=body.get("interaction_type","call"),transcript=body.get("transcript",""),summary=summary.get("executive_summary",""),key_points=summary.get("key_discussion_points",[]),action_items=[x.model_dump() if hasattr(x,"model_dump") else x for x in summary.get("action_items",[])])
    db.add(obj); db.commit(); db.refresh(obj); return {"id":obj.id,"lead_id":lead_id,**summary}

@app.get("/api/v1/conversations/{lead_id}")
@app.get("/api/v1/leads/{lead_id}/conversations")
def conversations(lead_id:int,db:Session=Depends(get_db)):
    return [{"id":x.id,"lead_id":x.lead_id,"summary":x.summary,"key_points":x.key_points,"action_items":x.action_items,"transcript":x.transcript} for x in db.scalars(select(SalesInteraction).where(SalesInteraction.lead_id==lead_id).order_by(SalesInteraction.id.desc())).all()]

@app.get("/api/v1/analytics")
@app.get("/api/v1/dashboard/summary")
def analytics(db:Session=Depends(get_db)):
    leads=db.scalars(select(Lead)).all(); stages={}
    for x in leads: stages[x.lead_status]=stages.get(x.lead_status,0)+1
    latest_ids=select(func.max(LeadScore.id).label("latest_id")).group_by(LeadScore.lead_id).subquery()
    scores=db.scalars(select(LeadScore.lead_score).where(LeadScore.id.in_(select(latest_ids.c.latest_id)))).all(); qualified=sum(x.lead_status in {"qualified","proposal","negotiation"} for x in leads)
    return {"source":"local database","is_demo":False,"total_leads":len(leads),"qualified_leads":qualified,"average_lead_score":round(sum(scores)/len(scores),1) if scores else None,
      "conversion_rate":(sum(x.lead_status=="converted" for x in leads)/len(leads)) if leads else None,"outreach_activity":db.scalar(select(func.count()).select_from(OutreachCampaign)) or 0,
      "follow_up_tasks":0,"pipeline_distribution":[{"stage":k,"count":v} for k,v in sorted(stages.items())],"lead_score_distribution":[],"activity_trend":[]}

@app.get("/api/v1/follow-ups")
def follow_ups(): return []

@app.get("/api/v1/recommendations/{lead_id}")
def recommendations(lead_id:int,db:Session=Depends(get_db)):
    lead=db.get(Lead,lead_id)
    if not lead: raise HTTPException(404,"Lead not found")
    response=ai_work("follow_up",{"lead":lead_dict(lead)})
    result=response.result
    return result.model_dump() if hasattr(result,"model_dump") else result

@app.get("/api/v1/crm/providers")
def crm_providers():
    return [{"provider":"salesforce","configured":bool(os.getenv("SALESFORCE_ACCESS_TOKEN")),"live_sync_available":False},
            {"provider":"hubspot","configured":bool(os.getenv("HUBSPOT_ACCESS_TOKEN")),"live_sync_available":False}]

@app.post("/api/v1/crm/mappings/validate")
def validate_crm_mapping(body:dict[str,Any]):
    mapping=body.get("mapping",body)
    if not isinstance(mapping,dict): raise HTTPException(422,"mapping must be an object")
    allowed={"company_name","contact_name","email","phone","industry","website","company_size","stage"}
    invalid=[k for k,v in mapping.items() if k not in allowed or not isinstance(v,str) or not v.strip()]
    return {"valid":not invalid,"errors":[f"Invalid source field or target for: {x}" for x in invalid],"mapping":mapping}

@app.post("/api/v1/crm/sync/preview")
def crm_preview(body:dict[str,Any],db:Session=Depends(get_db)):
    ids=body.get("lead_ids",[])
    if not isinstance(ids,list) or len(ids)>500: raise HTTPException(422,"lead_ids must be a list of at most 500 IDs")
    records=[]
    for item in ids:
        try: lead=db.get(Lead,int(item))
        except (ValueError,TypeError): lead=None
        if not lead: records.append({"lead_id":item,"valid":False,"error":"Lead not found"})
        else: records.append({"lead_id":lead.id,"valid":True,"fields":lead_dict(lead)})
    return {"provider":body.get("provider"),"operation":body.get("operation","upsert"),"dry_run":True,"records":records}

@app.post("/api/v1/crm/sync")
def crm_sync(body:dict[str,Any],db:Session=Depends(get_db)):
    provider=str(body.get("provider","" )).lower()
    if provider not in {"salesforce","hubspot"}: raise HTTPException(422,"provider must be salesforce or hubspot")
    token=os.getenv("SALESFORCE_ACCESS_TOKEN" if provider=="salesforce" else "HUBSPOT_ACCESS_TOKEN")
    log=CRMSyncLog(provider=provider,operation=str(body.get("operation","upsert")),status="failed",
       request_metadata={"mode":"not_configured"},error_message="Live CRM transport is not configured in this local build.")
    db.add(log); db.commit(); db.refresh(log)
    raise HTTPException(501,"CRM adapter transport is not configured; a failed synchronization attempt was recorded.")

@app.get("/api/v1/crm/sync-logs")
def sync_logs(db:Session=Depends(get_db)):
    rows=db.scalars(select(CRMSyncLog).order_by(CRMSyncLog.id.desc()).limit(250)).all()
    return [{"id":x.id,"provider":x.provider,"operation":x.operation,"status":x.status,"error_message":x.error_message,"attempt_count":x.attempt_count,"created_at":x.created_at.isoformat()} for x in rows]

@app.post("/api/v1/crm/sync-logs/{log_id}/retry")
def retry_sync(log_id:int,db:Session=Depends(get_db)):
    log=db.get(CRMSyncLog,log_id)
    if not log: raise HTTPException(404,"Sync log not found")
    if log.status=="success": raise HTTPException(409,"Successful CRM operations cannot be retried")
    log.attempt_count+=1; log.status="failed"; log.error_message="Retry unavailable: CRM adapter transport is not configured."
    db.commit(); return {"id":log.id,"status":log.status,"attempt_count":log.attempt_count,"error_message":log.error_message}

@app.post("/api/v1/leads/{lead_id}/conversations")
def save_conversation(lead_id:int,body:dict[str,Any],db:Session=Depends(get_db)):
    if not db.get(Lead,lead_id): raise HTTPException(404,"Lead not found")
    summary=body.get("summary",{}); summary=summary if isinstance(summary,dict) else {}
    obj=SalesInteraction(lead_id=lead_id,interaction_type="call",summary=summary.get("executive_summary",str(summary)),key_points=summary.get("key_discussion_points",[]),action_items=summary.get("action_items",[]))
    db.add(obj); db.commit(); db.refresh(obj); return {"id":obj.id,"lead_id":lead_id}
