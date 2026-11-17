from sqlalchemy.orm import Session
from database.models import Lead, LeadScore, OutreachCampaign, SalesInteraction

def get_dashboard_metrics(db: Session) -> dict:
    total_leads = db.query(Lead).count()
    
    # Lead scoring breakdowns
    all_scores = db.query(LeadScore).all()
    hot_count = sum(1 for s in all_scores if s.lead_score >= 70)
    warm_count = sum(1 for s in all_scores if 50 <= s.lead_score < 70)
    cold_count = sum(1 for s in all_scores if s.lead_score < 50)
    
    avg_score = round(sum(s.lead_score for s in all_scores) / len(all_scores), 1) if all_scores else 0

    emails_generated = db.query(OutreachCampaign).count()
    emails_sent = db.query(OutreachCampaign).filter(OutreachCampaign.status == "Sent").count()
    calls_done = db.query(SalesInteraction).count()

    conversion_rate = round((hot_count / total_leads * 100), 1) if total_leads > 0 else 0.0

    # Pipeline stages count
    stage_counts = {}
    leads = db.query(Lead).all()
    for l in leads:
        stg = l.lead_status or "New"
        stage_counts[stg] = stage_counts.get(stg, 0) + 1

    # Industry distribution
    industry_counts = {}
    for l in leads:
        ind = l.industry or "Other"
        industry_counts[ind] = industry_counts.get(ind, 0) + 1

    return {
        "total_leads": total_leads,
        "hot_leads": hot_count,
        "warm_leads": warm_count,
        "cold_leads": cold_count,
        "avg_score": avg_score,
        "emails_generated": emails_generated,
        "emails_sent": emails_sent,
        "calls_done": calls_done,
        "conversion_rate": conversion_rate,
        "stage_distribution": stage_counts,
        "industry_distribution": industry_counts
    }
