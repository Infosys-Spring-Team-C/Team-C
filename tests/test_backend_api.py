from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.db import Base
from backend.api import app, get_db

engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
TestingSession=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
Base.metadata.create_all(engine)
def test_local_api_crud_duplicate_scoring_and_insights():
    def override_db():
        db=TestingSession()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db]=override_db
    try:
        with TestClient(app) as client:
            created=client.post("/api/v1/leads",json={"company_name":"Acme Systems","industry":"Software","email":"hello@acme.test","explicit_needs":"Reduce manual reporting"})
            assert created.status_code==201, created.text
            lead=created.json(); lead_id=lead["id"]
            assert client.get(f"/api/v1/leads/{lead_id}").json()["company_name"]=="Acme Systems"
            assert client.post("/api/v1/leads",json={"company_name":"Duplicate","email":"HELLO@ACME.TEST"}).status_code==409
            assert client.patch(f"/api/v1/leads/{lead_id}",json={"stage":"qualified"}).json()["stage"]=="Qualified"
            assert client.patch(f"/api/v1/leads/{lead_id}",json={"stage":"made-up"}).status_code==422
            assert client.patch(f"/api/v1/leads/{lead_id}",json={"stage":"new"}).status_code==422
            scored=client.post(f"/api/v1/leads/{lead_id}/scores",json={"score":{"score":64,"qualification_category":"Nurture","factors":[]}})
            assert scored.status_code==200,scored.text
            insight=client.post(f"/api/v1/leads/{lead_id}/insights",json={"research":{"company_overview":"Supplied context only.","possible_needs":[],"potential_challenges":[],"opportunities":[],"supported_facts":[]}})
            assert insight.status_code==200,insight.text
            assert len(client.get(f"/api/v1/intelligence/{lead_id}").json())==1
            outreach=client.post("/api/v1/outreach/generate",json={"lead_id":lead_id,"product_service":"reporting tools","campaign_objective":"compare workflows"})
            assert outreach.status_code==200,outreach.text
            assert outreach.json()["status"]=="draft"
            campaign_id=outreach.json()["id"]
            assert client.patch(f"/api/v1/outreach/campaigns/{campaign_id}",json={"subject_line":"Edited subject"}).json()["subject_line"]=="Edited subject"
            conversation=client.post("/api/v1/conversations/summarize",json={"lead_id":lead_id,"transcript":"The customer needs a cost report. The buyer will share the report by November 4, 2026."})
            assert conversation.status_code==200,conversation.text
            assert len(client.get(f"/api/v1/conversations/{lead_id}").json())==1
            recommendation=client.get(f"/api/v1/recommendations/{lead_id}")
            assert recommendation.status_code==200,recommendation.text
            csv_data=b"""company_name,email
Beta Labs,beta@example.test
Beta Duplicate,beta@example.test
,missing@example.test
"""
            imported=client.post("/api/v1/leads/import",files={"file":("leads.csv",csv_data,"text/csv")})
            assert imported.status_code==200,imported.text
            assert (imported.json()["imported"],imported.json()["duplicate"],imported.json()["invalid"])==(1,1,1)
            assert client.get("/api/v1/analytics").json()["total_leads"]==2
            assert client.delete(f"/api/v1/leads/{lead_id}").status_code==204
            assert client.get(f"/api/v1/leads/{lead_id}").status_code==404
    finally:
        app.dependency_overrides.clear()
