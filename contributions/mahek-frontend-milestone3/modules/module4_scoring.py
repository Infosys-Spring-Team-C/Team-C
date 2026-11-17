import json
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Lead, LeadScore

def calculate_lead_score(db: Session, lead_id: int) -> LeadScore:
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead with ID {lead_id} not found.")

    company = lead.company_name or "Company"
    industry = (lead.industry or "").lower()
    size = (lead.company_size or "").lower()
    stage = (lead.funding_stage or "").lower()
    need = (lead.business_need or "").lower()

    # Base rule-based qualification
    score = 40
    factors = []

    # 1. Funding Stage factor (+20 max)
    if any(s in stage for s in ["series c", "series d", "ipo", "growth"]):
        score += 25
        factors.append("High budget availability (+25 pts for Series C/D/Growth stage)")
    elif any(s in stage for s in ["series b", "series a"]):
        score += 18
        factors.append("Healthy growth capital (+18 pts for Series A/B stage)")
    elif "seed" in stage or "bootstrapped" in stage:
        score += 10
        factors.append("Early stage evaluation (+10 pts for Seed)")

    # 2. Company Size factor (+15 max)
    if "250" in size or "500" in size or "enterprise" in size:
        score += 15
        factors.append("Optimal team size with dedicated budget owners (+15 pts)")
    elif "100" in size or "50" in size:
        score += 12
        factors.append("Agile team structure (+12 pts)")
    else:
        score += 8
        factors.append("Emerging team (+8 pts)")

    # 3. Industry alignment factor (+12 max)
    if any(ind in industry for ind in ["software", "ai", "artificial", "cloud", "saas", "tech"]):
        score += 12
        factors.append("High product-market industry fit (+12 pts)")
    else:
        score += 6
        factors.append("Adjacent industry fit (+6 pts)")

    # 4. Explicit need urgency (+10 max)
    if any(term in need for term in ["scale", "scaling", "cost", "cloud", "faster", "pipeline", "automation"]):
        score += 10
        factors.append("Urgent strategic pain point match (+10 pts)")

    # Cap score at 98 max
    score = min(score, 95)
    score = max(score, 25)

    # Threshold classification strictly following documentation:
    # 90-100: Very Hot
    # 70-89: Hot
    # 50-69: Warm
    # 0-49: Cold
    if score >= 90:
        priority_level = "Very Hot"
        action = "Call today. Schedule technical deep-dive immediately and reference high-ROI benchmarks."
        prob = round(score / 100 * 0.95, 2)
        reason = f"{company} demonstrates top-tier qualification with {lead.funding_stage} backing, urgent {lead.business_need}, and strong enterprise readiness."
    elif score >= 70:
        priority_level = "Hot"
        action = "Call this week within 48 hours. Mention ROI metrics and reference similar success stories."
        prob = round(score / 100 * 0.90, 2)
        reason = f"{company} is in {lead.funding_stage} phase with clear budget allocation for new operational tools."
    elif score >= 50:
        priority_level = "Warm"
        action = "Follow up next week. Share product demo recording and relevant case studies."
        prob = round(score / 100 * 0.80, 2)
        reason = f"{company} shows moderate purchase intent; requires further technical nurturing and stakeholder alignment."
    else:
        priority_level = "Cold"
        action = "Low priority. Add to automated email newsletter sequence; revisit next quarter."
        prob = round(score / 100 * 0.50, 2)
        reason = f"Current profile indicates low urgency or budget constraints at this stage."

    # Persist or update
    existing = db.query(LeadScore).filter(LeadScore.lead_id == lead_id).first()
    if existing:
        existing.lead_score = score
        existing.conversion_probability = prob
        existing.priority_level = priority_level
        existing.reason = reason
        existing.next_action = action
        existing.scoring_factors = json.dumps(factors)
        existing.created_at = datetime.utcnow()
        lead_score_obj = existing
    else:
        lead_score_obj = LeadScore(
            lead_id=lead_id,
            lead_score=score,
            conversion_probability=prob,
            priority_level=priority_level,
            reason=reason,
            next_action=action,
            scoring_factors=json.dumps(factors)
        )
        db.add(lead_score_obj)

    db.commit()
    db.refresh(lead_score_obj)
    return lead_score_obj

def get_lead_score(db: Session, lead_id: int) -> LeadScore:
    return db.query(LeadScore).filter(LeadScore.lead_id == lead_id).order_by(LeadScore.score_id.desc()).first()
