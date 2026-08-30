"""
NetSage AI - Automated Test Suite
Unit and integration tests covering:
- XML Feature Extractor & save-ref-id resolution
- Case Manager & 32-case dataset consistency
- Deterministic Rule Checker accuracy
- AI Diagnostician JSON output schema
- Human Review logging & metrics calculation
"""

import os
import sys
import unittest
from pathlib import Path

# Add root and src to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "src"))

try:
    from src.feature_extractor import PacketTracerFeatureExtractor
    from src.case_manager import CaseManager
    from src.rule_checker import DeterministicRuleChecker
    from src.ai_diagnostician import AIDiagnostician
    from src.human_review import HumanReviewManager
except ImportError:
    from feature_extractor import PacketTracerFeatureExtractor
    from case_manager import CaseManager
    from rule_checker import DeterministicRuleChecker
    from ai_diagnostician import AIDiagnostician
    from human_review import HumanReviewManager

class TestNetSageAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = root
        cls.extractor = PacketTracerFeatureExtractor()
        cls.case_mgr = CaseManager()
        cls.checker = DeterministicRuleChecker()
        cls.diag = AIDiagnostician()
        cls.review_mgr = HumanReviewManager()

    def test_01_feature_extractor_save_ref_id(self):
        """Verify XML extraction correctly extracts save-ref-id for every device."""
        xml_dir = self.root / "data" / "pkt_test_files" / "output"
        if not xml_dir.exists():
            xml_dir = self.root / "pkt_test_files" / "output"
        xml_files = list(xml_dir.glob("*.xml"))
        self.assertGreaterEqual(len(xml_files), 1, "At least 1 XML file should exist.")

        for xml_file in xml_files:
            features = self.extractor.extract_from_xml(xml_file)
            self.assertIn("devices", features)
            self.assertIn("topology_links", features)
            self.assertGreater(len(features["devices"]), 0)

            # Check that every device has a non-empty save_ref_id
            for dev in features["devices"]:
                self.assertTrue(
                    dev["save_ref_id"].startswith("save-ref-id:"),
                    f"Device {dev['name']} in {xml_file.name} is missing valid save-ref-id format: {dev['save_ref_id']}"
                )

    def test_02_case_manager_dataset(self):
        """Verify at least 30 cases exist with all mandatory fields."""
        cases = self.case_mgr.get_all_cases()
        self.assertGreaterEqual(len(cases), 30, "Must have at least 30 troubleshooting cases.")

        mandatory_keys = [
            "case_id", "lab_source", "symptom", "topology_note", "show_outputs",
            "expected_fault", "osi_layer", "concept_tag", "severity",
            "deterministic_findings", "expected_next_command", "expected_fix"
        ]
        for c in cases:
            for k in mandatory_keys:
                self.assertIn(k, c, f"Case {c.get('case_id')} is missing field {k}")
                self.assertTrue(len(str(c[k]).strip()) > 0, f"Case {c.get('case_id')} field {k} is empty")

    def test_03_deterministic_rule_checker(self):
        """Verify deterministic rules trigger on known fault signatures."""
        # 1. Duplicate IP
        dup_case = self.case_mgr.get_case("NETSAGE-004")
        findings = self.checker.run_checks_on_case(dup_case)
        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("RULE-DUP-IP", rule_ids)

        # 2. Administratively Down
        down_case = self.case_mgr.get_case("NETSAGE-015")
        findings = self.checker.run_checks_on_case(down_case)
        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("RULE-ADMIN-DOWN", rule_ids)

        # 3. Subnet Mask / MTU Mismatch
        mtu_case = self.case_mgr.get_case("NETSAGE-006")
        findings = self.checker.run_checks_on_case(mtu_case)
        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("RULE-MTU-MISMATCH", rule_ids)

        # 4. Inverted Wildcard Mask
        acl_case = self.case_mgr.get_case("NETSAGE-030")
        findings = self.checker.run_checks_on_case(acl_case)
        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("RULE-ACL-WILDCARD", rule_ids)

    def test_04_ai_diagnostician_schema(self):
        """Verify AI diagnostician returns valid schema conforming to prompt specifications."""
        sample_case = self.case_mgr.get_case("NETSAGE-001")
        findings = self.checker.run_checks_on_case(sample_case)
        res = self.diag.diagnose_case(sample_case, findings)

        self.assertEqual(res["case_id"], "NETSAGE-001")
        self.assertIn("root_cause", res)
        self.assertIn("confidence", res)
        self.assertIn("evidence", res)
        self.assertIn("next_command", res)
        self.assertIn("fix_steps", res)
        self.assertIsInstance(res["evidence"], list)
        self.assertIsInstance(res["fix_steps"], list)
        self.assertGreater(len(res["fix_steps"]), 0)

    def test_05_human_review_metrics(self):
        """Verify human review logging and agreement rate calculation."""
        metrics = self.review_mgr.get_review_metrics()
        self.assertIn("total", metrics)
        self.assertIn("accepted", metrics)
        self.assertIn("edited", metrics)
        self.assertIn("rejected", metrics)
        self.assertIn("agreement_rate", metrics)
        self.assertGreaterEqual(metrics["total"], 30)

if __name__ == "__main__":
    unittest.main()
