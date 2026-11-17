from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Lead, SalesInteraction

def summarize_call_notes(db: Session, lead_id: int, notes: str) -> SalesInteraction:
    lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
    company = lead.company_name if lead else "Client"

    # Extraction logic
    lines = [line.strip() for line in notes.split("\n") if line.strip()]
    summary = f"Discussion held with {company}. Core points addressed: " + " ".join(lines[:2])
    action_items = "- Send technical architecture overview\n- Schedule demo with engineering team\n- Follow up on procurement timeline"
    follow_up = "Follow up within 5 business days with agreed documentation."

    interaction = SalesInteraction(
        lead_id=lead_id,
        summary=summary,
        action_items=action_items,
        key_points="\n".join([f"• {l}" for l in lines[:4]]),
        follow_up=follow_up
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction
