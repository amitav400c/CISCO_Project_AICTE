"""
NetSage AI - Master Orchestration Pipeline
Coordinates XML extraction, topology building, rule checking,
AI diagnosis, and human review logging.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from .extract_xml import extract_xml
    from .feature_extractor import PacketTracerFeatureExtractor
    from .topology_builder import TopologyBuilder
    from .rule_checker import DeterministicRuleChecker
    from .ai_diagnostician import AIDiagnostician
    from .case_manager import CaseManager
    from .human_review import HumanReviewManager
except (ImportError, ValueError):
    from extract_xml import extract_xml
    from feature_extractor import PacketTracerFeatureExtractor
    from topology_builder import TopologyBuilder
    from rule_checker import DeterministicRuleChecker
    from ai_diagnostician import AIDiagnostician
    from case_manager import CaseManager
    from human_review import HumanReviewManager

class NetSagePipeline:
    def __init__(self):
        self.root = Path(__file__).resolve().parent.parent
        self.feature_extractor = PacketTracerFeatureExtractor()
        self.topology_builder = TopologyBuilder()
        self.rule_checker = DeterministicRuleChecker()
        self.diagnostician = AIDiagnostician()
        self.case_manager = CaseManager()
        self.review_manager = HumanReviewManager()

    def process_lab_file(self, pkt_path: Path) -> Dict[str, Any]:
        """Processes a single .pkt file end-to-end."""
        out_xml_dir = self.root / "data" / "pkt_test_files" / "output"
        if not out_xml_dir.exists():
            out_xml_dir = self.root / "pkt_test_files" / "output"
        extracted = extract_xml(pkt_path.parent, out_xml_dir, extract_features=True)
        return extracted[0] if extracted else {}

    def triage_case(self, case_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Performs end-to-end triage on a troubleshooting case."""
        case = self.case_manager.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found.")

        # 1. Deterministic Rule Checking
        rule_findings = self.rule_checker.run_checks_on_case(case)

        # 2. AI Diagnosis
        diagnosis = self.diagnostician.diagnose_case(case, rule_findings, api_key=api_key)

        # 3. Log Diagnosis
        diag_id = self.review_manager.log_diagnosis(case_id, diagnosis)

        return {
            "case": case,
            "rule_findings": rule_findings,
            "diagnosis": diagnosis,
            "diagnosis_id": diag_id
        }

if __name__ == "__main__":
    pipeline = NetSagePipeline()
    res = pipeline.triage_case("NETSAGE-001")
    print(f"[+] Triaged case: {res['case']['case_id']}")
    print(f"    Root cause: {res['diagnosis']['root_cause']}")
    print(f"    Next command: {res['diagnosis']['next_command']}")
