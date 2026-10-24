import unittest

from fastapi.testclient import TestClient

from marketplace import board_store as store
from marketplace import bills, rules
from run_board import app


def as_role(role):
    return {"X-Demo-Role": role}


class RulesTest(unittest.TestCase):
    def test_solar_matches_spec_worked_example(self):
        solar = rules.estimate_solar(23.1, baseline_monthly_kwh=3715)
        self.assertAlmostEqual(solar.capex_myr, 46_000, delta=50)
        self.assertAlmostEqual(solar.saving_myr_year, 15_450, delta=10)
        self.assertAlmostEqual(solar.payback_years, 3.0, delta=0.05)
        self.assertAlmostEqual(solar.co2e_t_year, 22.6, delta=0.05)
        self.assertEqual(rules.suggested_solar_kwp(3715), 23.1)

    def test_led_and_aircon_match_spec(self):
        led = rules.estimate_led(40)
        self.assertEqual(led.capex_myr, 1_600)
        self.assertAlmostEqual(led.saving_myr_year, 1_370, delta=5)
        self.assertAlmostEqual(led.payback_years, 1.2, delta=0.05)
        aircon = rules.estimate_aircon(3)
        self.assertEqual(aircon.capex_myr, 6_600)
        self.assertAlmostEqual(aircon.saving_myr_year, 1_600, delta=5)
        self.assertAlmostEqual(aircon.payback_years, 4.1, delta=0.05)

    def test_approximations_hide_exact_figures(self):
        self.assertEqual(rules.approx_money(15_453.4), 15_000)
        self.assertEqual(rules.approx_years(2.98), 3.0)
        self.assertEqual(rules.approx_tonnes(22.56), 22)

    def test_repayment_check(self):
        result = rules.repayment_check(15_000, 45_000, 5, 0)
        self.assertEqual(result["yearly_instalment_myr"], 9_000)
        self.assertAlmostEqual(result["coverage"], 1.67, places=2)
        with self.assertRaises(ValueError):
            rules.repayment_check(15_000, 0, 5, 5)


class BoardFlowTest(unittest.TestCase):
    def setUp(self):
        store.reset()
        self.client = TestClient(app)

    def test_investor_card_is_anonymous_and_matches_criteria(self):
        board = self.client.get("/api/greenready/board", headers=as_role("investor")).json()
        dates = [card["listed_at"] for card in board["listings"]]
        self.assertEqual(dates, sorted(dates, reverse=True))  # M03 newest first
        card = next(item for item in board["listings"] if item["id"] == "GR-L-0871")
        self.assertNotIn("identity", card)
        self.assertNotIn("company", card)
        self.assertEqual(card["usage_band"], "3,000–5,000 kWh/month")
        self.assertEqual(card["bill_band"], "RM1,500–2,500")
        self.assertEqual(card["capex_band"], "RM20k–50k")
        self.assertEqual(card["saving_approx_myr"], 15_000)
        self.assertEqual((card["criteria"]["passed"], card["criteria"]["total"]), (5, 5))
        self.assertNotIn("Kilang", str(board))
        for forbidden in ("score", "rank", "rating"):
            self.assertNotIn(forbidden, str(card).lower())

    def test_supplier_board_is_filtered_by_area_and_category(self):
        board = self.client.get("/api/greenready/board", headers=as_role("supplier")).json()
        ids = {card["id"] for card in board["listings"]}
        self.assertIn("GR-L-0871", ids)
        self.assertNotIn("GR-L-0852", ids)  # Penang, outside service area
        self.assertNotIn("GR-L-0836", ids)  # aircon only, not a supplier category
        self.assertEqual(board["requests_left"], 3)
        card = next(item for item in board["listings"] if item["id"] == "GR-L-0871")
        self.assertNotIn("bill_band", card)
        self.assertEqual(card["suggested_solar_size"], "23.1 kWp")

    def test_staff_cannot_accept(self):
        request = self.client.post(
            "/api/greenready/requests", json={"listing_id": "GR-L-0871"}, headers=as_role("investor")
        ).json()
        response = self.client.post(f"/api/greenready/requests/{request['id']}/accept", headers=as_role("sme_staff"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["rule"], "C05")

    def test_full_investor_and_supplier_flow(self):
        investor, supplier, owner = as_role("investor"), as_role("supplier"), as_role("sme_owner")

        # Supplier sends a proposal (becomes the connection request).
        draft = self.client.get(
            "/api/greenready/documents/proposal/draft", params={"listing_id": "GR-L-0871"}, headers=supplier
        ).json()
        values = {field["key"]: field["suggested"] or "Daniel" for field in draft["fields"]}
        sent = self.client.post(
            "/api/greenready/documents/proposal",
            json={"listing_id": "GR-L-0871", "values": values}, headers=supplier,
        )
        self.assertEqual(sent.status_code, 200, sent.text)
        self.assertEqual(sent.json()["document"]["paybacks"]["a"], [2.8, 3.0])
        self.assertEqual(self.client.get("/api/greenready/board", headers=supplier).json()["requests_left"], 2)

        # Investor requests to connect; EOI is blocked until acceptance.
        request = self.client.post(
            "/api/greenready/requests", json={"listing_id": "GR-L-0871", "message": "Hi"}, headers=investor
        ).json()
        blocked = self.client.get("/api/greenready/documents/eoi/draft", params={"request_id": request["id"]}, headers=investor)
        self.assertEqual(blocked.status_code, 409)

        # Owner sees both and accepts.
        inbox = self.client.get("/api/greenready/requests", headers=owner).json()["requests"]
        self.assertEqual(len(inbox), 2)
        items = self.client.get("/api/greenready/action-items", headers=owner).json()["data"]
        self.assertEqual(items["counts"]["pendingApproval"], 2)
        for item in inbox:
            self.assertEqual(
                self.client.post(f"/api/greenready/requests/{item['id']}/accept", headers=owner).status_code, 200
            )

        # Identity revealed to the accepted partners; supplier charged RM200.
        detail = self.client.get("/api/greenready/listings/GR-L-0871", headers=investor).json()
        self.assertEqual(detail["identity"]["company_name"], "Kilang Contoh Sdn Bhd")
        self.assertIn("unlocked", detail)
        billing = self.client.get("/api/greenready/billing", headers=supplier).json()
        self.assertEqual(billing["month_to_date_myr"], 200)

        # Investor sends the EOI; owner sees it and replies.
        eoi_draft = self.client.get(
            "/api/greenready/documents/eoi/draft", params={"request_id": request["id"]}, headers=investor
        ).json()
        self.assertEqual(eoi_draft["to"]["company_name"], "Kilang Contoh Sdn Bhd")
        incomplete = self.client.post(
            "/api/greenready/documents/eoi", json={"request_id": request["id"], "values": {}}, headers=investor
        )
        self.assertEqual(incomplete.status_code, 422)
        eoi_values = {field["key"]: field["suggested"] or "Nurul" for field in eoi_draft["fields"]}
        eoi = self.client.post(
            "/api/greenready/documents/eoi", json={"request_id": request["id"], "values": eoi_values}, headers=investor
        ).json()
        self.assertTrue(eoi["reference"].startswith("GR-EOI-"))
        self.assertEqual(
            self.client.post(f"/api/greenready/documents/{eoi['id']}/accept", headers=owner).json()["status"], "accepted"
        )
        actions = [event["action"] for event in self.client.get("/api/greenready/audit", headers=owner).json()["events"]]
        self.assertTrue(any(action.startswith("Sent EOI") for action in actions))

    def test_login_and_onboarding(self):
        ok = self.client.post("/api/greenready/auth/login", json={"email": "Ahmad@KilangContoh.example", "password": "demo"})
        self.assertEqual(ok.json()["role"], "sme_owner")
        bad = self.client.post("/api/greenready/auth/login", json={"email": "x@y.example", "password": "demo"})
        self.assertEqual(bad.status_code, 401)

        self.assertEqual(self.client.get("/api/greenready/onboarding/ssm/123").status_code, 422)
        duplicate = self.client.get("/api/greenready/onboarding/ssm/202301012345").json()
        self.assertIn("already has a GreenReady account", duplicate["blocked"])
        inactive = self.client.get("/api/greenready/onboarding/ssm/201801034567").json()
        self.assertFalse(inactive["checks"]["active"]["passed"])

        profile = self.client.get("/api/greenready/onboarding/ssm/201901023456").json()
        self.assertIsNone(profile["blocked"])
        self.assertEqual((profile["sector"], profile["checks"]["size"]["label"]), ("Manufacturing", "Small"))
        body = {
            "ssm_no": "201901023456", "owner_name": "Lim", "email": "lim@perabot.example", "pdpa_consent": True,
            "answers": {"lighting": "fluorescent", "aircon": "inverter", "roof_access": "yes", "daytime": "yes"},
        }
        self.assertEqual(self.client.post("/api/greenready/onboarding/register", json={**body, "pdpa_consent": False}).status_code, 422)
        created = self.client.post("/api/greenready/onboarding/register", json=body)
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["free_analyses"], 5)
        again = self.client.post("/api/greenready/onboarding/register", json=body)
        self.assertEqual((again.status_code, again.json()["rule"]), (409, "C07"))

    def test_sample_bill_matches_spec(self):
        sep = self.client.get("/api/greenready/bills/BILL-0926", headers=as_role("sme_owner")).json()
        self.assertEqual(sep["status"], "ready")
        self.assertTrue(all(check["passed"] for check in sep["checks"]))
        self.assertEqual(len(sep["checks"]), 8)
        insights = sep["insights"]
        self.assertEqual(insights["baseline_kwh"]["value"], 3715)
        self.assertEqual(insights["spike_pct"]["value"], 19)
        self.assertTrue(insights["spike_pct"]["alert"])
        self.assertEqual(insights["real_cost_per_kwh"]["value"], 0.51)
        self.assertEqual(sep["values"]["total_payable_myr"], 2140.0)

    def test_upload_review_and_recommendations(self):
        staff = as_role("sme_staff")
        bill = self.client.post(
            "/api/greenready/bills/upload", headers=staff, files={"file": ("tnb.pdf", b"%PDF-1.4", "application/pdf")}
        ).json()
        self.assertEqual(bill["status"], "needs_review")  # V12: two fields under 85%
        self.assertEqual(bill["checks"], [])
        blocked = self.client.get(f"/api/greenready/bills/{bill['id']}/recommendations", headers=staff)
        self.assertEqual(blocked.status_code, 409)

        confirmed = self.client.patch(f"/api/greenready/bills/{bill['id']}/fields", headers=staff, json={"confirm_all": True}).json()
        self.assertEqual(confirmed["status"], "check_failed")  # the misread network charge fails V04
        fixed = self.client.patch(
            f"/api/greenready/bills/{bill['id']}/fields", headers=staff, json={"values": {"network_charge_myr": 580.36}}
        ).json()
        self.assertEqual(fixed["status"], "ready")

        rec = self.client.get(f"/api/greenready/bills/{bill['id']}/recommendations", headers=staff).json()
        by_type = {option["type"]: option for option in rec["options"]}
        self.assertEqual(set(by_type), {"led", "aircon", "solar"})
        self.assertEqual(by_type["solar"]["size"], "23.1 kWp")
        self.assertAlmostEqual(by_type["aircon"]["payback_years"], 4.1, delta=0.05)
        self.assertIn(rec["explanation"]["source"], {"ai", "rules"})
        self.assertEqual(self.client.get("/api/greenready/wallet", headers=staff).json()["data"]["balance"], 4.0)

    def test_bill_upload_rules(self):
        owner = as_role("sme_owner")
        bad = self.client.post("/api/greenready/bills/upload", headers=owner, files={"file": ("bill.exe", b"MZ", "application/x-msdownload")})
        self.assertEqual(bad.status_code, 415)
        for _ in range(3):  # RM6.00 = 3 analyses
            self.client.post("/api/greenready/bills/upload", headers=owner, files={"file": ("b.png", b"\x89PNG", "image/png")})
        broke = self.client.post("/api/greenready/bills/upload", headers=owner, files={"file": ("b.png", b"\x89PNG", "image/png")})
        self.assertEqual(broke.status_code, 402)
        investor = self.client.get("/api/greenready/bills", headers=as_role("investor"))
        self.assertEqual(investor.status_code, 403)

    def test_manual_entry_runs_checks(self):
        values = {key: value for key, value in bills.SAMPLE_SEP.items() if not key.startswith("_")}
        bill = self.client.post("/api/greenready/bills/manual", headers=as_role("sme_owner"), json={**values, "month": "Sep 2026"}).json()
        self.assertEqual(bill["status"], "ready")
        missing = self.client.post("/api/greenready/bills/manual", headers=as_role("sme_owner"), json={"month": "x"})
        self.assertEqual(missing.status_code, 422)

    def test_unlisted_listing_leaves_the_board(self):
        self.client.post("/api/greenready/listings/GR-L-0871/unlist", headers=as_role("sme_owner"))
        ids = {card["id"] for card in self.client.get("/api/greenready/board", headers=as_role("investor")).json()["listings"]}
        self.assertNotIn("GR-L-0871", ids)


if __name__ == "__main__":
    unittest.main()
