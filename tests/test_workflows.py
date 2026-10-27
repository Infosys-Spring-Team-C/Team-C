from utils.config import Settings
from ai.providers import create_provider, ProviderError
from ai.graph import run_workflow, workflow_route

def provider(): return create_provider(Settings(demo_mode=True))

def sample_lead(): return {"id":"1","company_name":"Northstar","industry":"Logistics","company_size":"201-1000","company_description":"Growing logistics operation.","prospect_role":"Operations Director","engagement_history":"Meeting booked","explicit_needs":"Reduce manual exception handling","response_behavior":"Interested","stage":"Discovery"}

def test_router_selects_only_requested_operation():
    assert workflow_route({"operation":"outreach"})=="outreach"
    assert workflow_route({"operation":"not-real"})=="invalid"

def test_lead_intelligence_returns_validated_research_and_qualification():
    response=run_workflow("lead_intelligence",{"lead":sample_lead(),"product_service":"operations platform"},provider())
    assert response.execution.success
    assert response.research is not None and response.qualification is not None
    assert response.research.disclaimer.startswith("No website")

def test_outreach_is_draft_not_unsupported_research_claim():
    response=run_workflow("outreach",{"lead":sample_lead(),"product_service":"platform","campaign_objective":"Book a meeting","channel":"Cold email","tone":"Professional","call_to_action":"Talk?"},provider())
    assert response.result.subject_line
    assert "research" not in response.result.body.lower() or "don’t want to assume" in response.result.body.lower()

def test_conversation_extracts_only_explicit_action_date():
    text="Customer needs reporting. Maya will send the usage file by October 22, 2026. They raised a budget concern."
    response=run_workflow("conversation",{"transcript":text,"notes":""},provider())
    assert response.result.action_items
    assert response.result.action_items[0].due_date=="October 22, 2026"

def test_long_transcript_chunking_and_follow_up():
    response=run_workflow("conversation",{"transcript":("The customer needs reporting. "*1500),"notes":""},provider())
    assert "Hierarchical" in response.result.source_note
    follow=run_workflow("follow_up",{"lead":sample_lead()},provider())
    assert follow.result.priority in {"High","Medium","Low"}

def test_missing_real_provider_key_is_clear():
    try: create_provider(Settings(demo_mode=False,llm_provider="openai",openai_api_key=""))
    except ProviderError as exc: assert "OPENAI_API_KEY" in str(exc)
    else: raise AssertionError("provider should require a key")

def test_opt_in_memory_checkpointer_executes_graph():
    from langgraph.checkpoint.memory import MemorySaver
    response=run_workflow("research",{"lead":sample_lead(),"product_service":"platform"},provider(),checkpointer=MemorySaver(),thread_id="test-thread")
    assert response.execution.success
    assert response.result is not None
