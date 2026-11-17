import os
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Lead, CompanyInsight, OutreachCampaign

def generate_personalized_email(db: Session, lead_id: int, tone: str = "professional") -> OutreachCampaign:
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead with ID {lead_id} not found.")

    company = lead.company_name or "Your Company"
    contact = lead.contact_name or "Sales Leader"
    first_name = contact.split()[0] if contact else "Partner"
    stage = lead.funding_stage or "growth"
    need = lead.business_need or "efficient scaling"
    industry = lead.industry or "Software"

    insight = db.query(CompanyInsight).filter(CompanyInsight.lead_id == lead_id).first()

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if openai_key and not openai_key.startswith("sk-proj-your-key"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            prompt = (
                f"Write a high-converting cold outreach sales email.\n"
                f"Recipient: {contact} at {company}\n"
                f"Industry: {industry}, Funding Stage: {stage}\n"
                f"Business Need: {need}\n"
                f"Tone: {tone}\n\n"
                f"Output format:\n"
                f"Subject: <subject>\n"
                f"Body: <body text>"
            )
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=450,
                temperature=0.7
            )
            text = response.choices[0].message.content or ""
            subject = f"Quick question for {company}"
            body = text
            if "Subject:" in text:
                parts = text.split("Subject:", 1)[1].split("\n", 1)
                subject = parts[0].strip()
                body = parts[1].strip() if len(parts) > 1 else text
        except Exception as e:
            print(f"[AI Service] OpenAI outreach generation error ({e}). Using template.")
            subject = f"Transforming data operations at {company}"
            body = (
                f"Hi {first_name},\n\n"
                f"I noticed {company} recently reached the {stage} milestone — congratulations! "
                f"As you scale {industry} operations, addressing {need} becomes pivotal.\n\n"
                f"Our AI sales & intelligence platform has helped peers cut processing cycles by 65% "
                f"while reducing infrastructure overhead by 40%.\n\n"
                f"Would you be open to a 15-minute introductory call this Thursday to explore synergies?\n\n"
                f"Best regards,\nSalesGenie Team"
            )
    else:
        # High quality personalization per tone based on training guide demo
        if tone.lower() == "friendly":
            subject = f"Excited about {company}'s recent growth!"
            body = (
                f"Hi {first_name},\n\n"
                f"Huge congratulations on {company}'s {stage} milestone! Loving what your team is building in {industry}.\n\n"
                f"Teams at your stage often hit bandwidth limits when {need}. We built SalesGenie AI to handle "
                f"the heavy lifting, driving a 65% reduction in manual turnaround.\n\n"
                f"Would love to share a quick 10-minute coffee chat or demo if you're open to it this week?\n\n"
                f"Cheers,\nSalesGenie Team"
            )
        elif tone.lower() == "urgent":
            subject = f"Urgent efficiency gains for {company}"
            body = (
                f"Hi {first_name},\n\n"
                f"Companies in {industry} experiencing {stage} velocity are facing immediate bottlenecks around {need}.\n\n"
                f"SalesGenie AI delivers immediate cost reduction within 14 days, already trusted by high-growth leaders.\n\n"
                f"Can we reserve 15 minutes tomorrow afternoon to review key benchmarks for {company}?\n\n"
                f"Regards,\nSalesGenie Team"
            )
        else:  # professional default
            subject = f"Quick question regarding {company}'s {stage} growth"
            body = (
                f"Hi {first_name},\n\n"
                f"I noticed {company} recently secured {stage} positioning — congratulations on the momentum! "
                f"As you scale operations, {need} becomes a critical priority.\n\n"
                f"Our platform has helped similar {stage} companies reduce pipeline processing time by 65% "
                f"while cutting overhead costs by 40%.\n\n"
                f"Would you be open to a brief 15-minute conversation this week to explore how we can support {company}'s objectives?\n\n"
                f"Best regards,\nSalesGenie Enterprise Team"
            )

    follow_up_strategy = (
        f"If no reply within 48 hours, send follow-up highlighting technical case study "
        f"and benchmark metrics relevant to {stage} {industry} companies."
    )

    campaign = OutreachCampaign(
        lead_id=lead_id,
        email_subject=subject,
        email_content=body,
        follow_up_strategy=follow_up_strategy,
        tone=tone,
        status="Draft"
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign

def get_outreach_campaign(db: Session, lead_id: int) -> OutreachCampaign:
    return db.query(OutreachCampaign).filter(OutreachCampaign.lead_id == lead_id).order_by(OutreachCampaign.campaign_id.desc()).first()
