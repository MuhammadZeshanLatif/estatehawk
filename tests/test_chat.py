import unittest
from unittest.mock import patch

from app import chat


class ChatTests(unittest.TestCase):
    def test_off_topic_never_calls_gemini(self):
        with patch("app.chat.ai.generate") as generate:
            reply = chat.answer("Who won the football game?")
            followup = chat.answer("What is the weather?", history=["Compare plans"])
        self.assertIn("only help with EstateHawk", reply)
        self.assertIn("only help with EstateHawk", followup)
        generate.assert_not_called()

    def test_plan_facts_use_actual_product_limits(self):
        facts = chat.plan_facts()
        self.assertIn("Pro: $99/month", facts)
        self.assertIn("3 counties", facts)
        self.assertIn("1000 leads/day", facts)

    def test_lead_question_gets_lead_explanation_without_sales(self):
        with patch("app.chat.ai.enabled", return_value=False):
            reply = chat.answer("Can you tell me more about leads?", plan="trial")
        self.assertIn("tax-delinquent property leads", reply)
        self.assertIn("Open Deals", reply)
        self.assertNotIn("Starter", reply)

    def test_gemini_receives_plan_and_curated_product_facts(self):
        with patch("app.chat.ai.enabled", return_value=True), patch("app.chat.ai.generate", return_value="Use Deals filters.") as generate:
            reply = chat.answer("How do I filter leads?", plan="starter", role="member")
        self.assertEqual(reply, "Use Deals filters.")
        prompt = generate.call_args.args[0]
        self.assertIn("plan=starter; role=member", prompt)
        self.assertNotIn("Pro: $99/month", prompt)
        self.assertIn("Deals shows leads", prompt)
        self.assertIn("Do not promote", prompt)

    def test_plan_facts_only_when_asked(self):
        with patch("app.chat.ai.enabled", return_value=True), patch("app.chat.ai.generate", return_value="Starter is $49/month.") as generate:
            chat.answer("What does Starter plan cost?", plan="trial")
        self.assertIn("Starter: $49/month", generate.call_args.args[0])

    def test_cut_off_ai_reply_uses_complete_answer(self):
        with patch("app.chat.ai.enabled", return_value=True), patch("app.chat.ai.generate", return_value="Hello! EstateHawk helps you find tax-del"):
            reply = chat.answer("Can you tell me more about leads?", plan="trial")
        self.assertIn("tax-delinquent property leads", reply)
        self.assertTrue(reply.endswith("outreach."))

    def test_private_detail_is_not_sent_to_gemini(self):
        with patch("app.chat.ai.generate") as generate:
            reply = chat.answer("Find the owner at 123 Main Street")
        self.assertIn("don't share", reply)
        generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
