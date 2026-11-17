import unittest
import json
import pandas as pd
from fastapi.testclient import TestClient

from main import app
from database.connection import get_db, Base, engine
from database.models import Lead

class TestSalesGenieBackendAndFrontendIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    def test_01_health_endpoint(self):
        """Test GET /health returns OK and app status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("app"), "SalesGenie AI")

    def test_02_lead_listing(self):
        """Test GET /leads/ returns list."""
        response = self.client.get("/leads/")
        self.assertEqual(response.status_code, 200)
        leads = response.json()
        self.assertIsInstance(leads, list)
        self.assertGreater(len(leads), 0, "Default seeded leads should exist")

    def test_03_lead_creation_and_validation(self):
        """Test POST /leads/ creates a new lead with all required fields."""
        payload = {
            "company_name": "TestCorp Enterprise",
            "industry": "Enterprise Software",
            "contact_name": "Alice Morgan",
            "email": "alice@testcorp.com",
            "phone": "+1999888777",
            "company_size": "250-500 employees",
            "funding_stage": "Series C",
            "business_need": "Automate data workflows and optimize cloud spend",
            "lead_status": "New"
        }
        response = self.client.post("/leads/", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("Lead added", data.get("message"))
        self.assertEqual(data["lead"]["company_name"], "TestCorp Enterprise")
        self.assertTrue(data["lead"]["lead_id"] > 0)

    def test_04_csv_bulk_import_validation(self):
        """Test POST /leads/bulk processes tabular rows correctly."""
        bulk_data = [
            {
                "company_name": "BulkCo A",
                "industry": "Fintech",
                "contact_name": "Bob Smith",
                "email": "bob@bulkco.com",
                "funding_stage": "Series A"
            },
            {
                "company_name": "BulkCo B",
                "industry": "Healthcare AI",
                "contact_name": "Carol Danvers",
                "email": "carol@bulkco.com",
                "funding_stage": "Series B"
            }
        ]
        response = self.client.post("/leads/bulk", json=bulk_data)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data.get("count"), 2)

    def test_05_company_analysis(self):
        """Test POST /intelligence/analyze/{id} produces business needs, opportunities, and industry insights."""
        # Get first lead
        leads = self.client.get("/leads/").json()
        lead_id = leads[0]["lead_id"]

        response = self.client.post(f"/intelligence/analyze/{lead_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["lead_id"], lead_id)
        self.assertTrue(len(data.get("business_needs", "")) > 0)
        self.assertTrue(len(data.get("opportunities", "")) > 0)
        self.assertTrue(len(data.get("industry_situation", "")) > 0)

    def test_06_lead_scoring_and_thresholds(self):
        """Test POST /intelligence/score/{id} follows exact thresholds (Very Hot, Hot, Warm, Cold)."""
        leads = self.client.get("/leads/").json()
        lead_id = leads[0]["lead_id"]

        response = self.client.post(f"/intelligence/score/{lead_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        score = data.get("lead_score")
        priority = data.get("priority_level")
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

        # Verify threshold alignment:
        if score >= 90:
            self.assertEqual(priority, "Very Hot")
        elif score >= 70:
            self.assertEqual(priority, "Hot")
        elif score >= 50:
            self.assertEqual(priority, "Warm")
        else:
            self.assertEqual(priority, "Cold")

        self.assertTrue(len(data.get("reason", "")) > 0)
        self.assertTrue(len(data.get("next_action", "")) > 0)

    def test_07_outreach_email_generation(self):
        """Test POST /intelligence/outreach generates subject, body, and strategy."""
        leads = self.client.get("/leads/").json()
        lead_id = leads[0]["lead_id"]

        for tone in ["professional", "friendly", "urgent"]:
            response = self.client.post("/intelligence/outreach", json={"lead_id": lead_id, "tone": tone})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(len(data.get("email_subject", "")) > 0)
            self.assertTrue(len(data.get("email_content", "")) > 0)
            self.assertTrue(len(data.get("follow_up_strategy", "")) > 0)

    def test_08_send_email_truthfulness_check(self):
        """Critical check: sending email without SMTP must never return false success."""
        payload = {
            "lead_id": 1,
            "recipient_email": "test@example.com",
            "subject": "Test",
            "body": "Test message"
        }
        response = self.client.post("/outreach/send-email", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Verify it reports truth: configured=False, success=False
        self.assertFalse(data.get("configured"))
        self.assertFalse(data.get("success"))
        self.assertIn("not configured", data.get("message").lower())

    def test_09_dashboard_analytics(self):
        """Test GET /analytics/dashboard returns full KPI metrics."""
        response = self.client.get("/analytics/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_leads", data)
        self.assertIn("hot_leads", data)
        self.assertIn("warm_leads", data)
        self.assertIn("cold_leads", data)
        self.assertIn("conversion_rate", data)
        self.assertIn("emails_generated", data)

    def test_10_sample_csv_validity(self):
        """Verify sample_leads.csv conforms to required schema."""
        df = pd.read_csv("sample_leads.csv")
        self.assertIn("company_name", df.columns)
        self.assertIn("contact_name", df.columns)
        self.assertIn("email", df.columns)
        self.assertGreaterEqual(len(df), 3)

    def test_11_conversation_intelligence_summarization(self):
        """Milestone 3 Test: POST /intelligence/conversation generates meeting summary, action items, and key points."""
        leads = self.client.get("/leads/").json()
        lead_id = leads[0]["lead_id"]
        payload = {
            "lead_id": lead_id,
            "notes": (
                "Sarah Johnson called today regarding data processing speed bottlenecks. "
                "Current pipelines take 6 hours daily. Budget of $50K approved for Q3. "
                "Needs architecture document by Friday and engineering demo scheduled."
            )
        }
        response = self.client.post("/intelligence/conversation", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("lead_id"), lead_id)
        self.assertTrue(len(data.get("summary", "")) > 0)
        self.assertTrue(len(data.get("action_items", "")) > 0)
        self.assertTrue(len(data.get("key_points", "")) > 0)
        self.assertTrue(len(data.get("follow_up", "")) > 0)

    def test_12_crm_sync_endpoint_truthfulness(self):
        """Milestone 3 Test: Unconfigured CRM sync endpoint returns 404, validating frontend truthful reporting."""
        payload = {"lead_id": 1, "company_name": "TechCorp"}
        response = self.client.post("/crm/sync", json=payload)
        # Verify backend does not have fake CRM route - returns 404
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
