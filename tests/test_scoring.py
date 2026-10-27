from ai.scoring import calculate_lead_score

def test_score_is_bounded_explainable_and_not_probability():
    outcome=calculate_lead_score({"company_description":"A detailed company description with scale context.","industry":"Technology","company_size":"51-200","prospect_role":"VP Sales","engagement_history":"Meeting booked","explicit_needs":"Needs better reporting quickly","stage":"Discovery","response_behavior":"Interested"})
    assert 0<=outcome.score<=100
    assert outcome.qualification_category in {"Qualified","Nurture","Low priority"}
    assert len(outcome.factors)==8
    assert "not a predicted conversion probability" in outcome.methodology_note

def test_missing_information_reduces_score():
    empty=calculate_lead_score({})
    rich=calculate_lead_score({"company_description":"x"*100,"industry":"SaaS","company_size":"51-200","prospect_role":"Director","engagement_history":"Meeting","explicit_needs":"Need a system now","stage":"Proposal","response_behavior":"Interested"})
    assert empty.score < rich.score
