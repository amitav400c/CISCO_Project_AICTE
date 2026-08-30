"""
NetSage AI - Main CLI Entry Point
Run batch feature extraction, rule checks, AI diagnosis, or start the dashboard.
"""

import sys
import argparse
from pathlib import Path

# Add src to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.append(str(root / "src"))

from extract_xml import extract_xml
from feature_extractor import PacketTracerFeatureExtractor
from rule_checker import DeterministicRuleChecker
from case_manager import CaseManager
from ai_diagnostician import AIDiagnostician
from human_review import HumanReviewManager

def banner():
    print("=" * 60)
    print("      NetSage AI - Cisco Network Troubleshooting Assistant")
    print("          Applied AI + Packet Tracer Lab Analysis")
    print("=" * 60)

def main():
    banner()
    parser = argparse.ArgumentParser(description="NetSage AI Network Troubleshooting Engine")
    parser.add_argument("--extract", action="store_true", help="Batch extract XML and features from .pkt files")
    parser.add_argument("--check-rules", action="store_true", help="Run deterministic rule checks across all cases")
    parser.add_argument("--diagnose", type=str, help="Diagnose a specific case ID (e.g. NETSAGE-001)")
    parser.add_argument("--list-cases", action="store_true", help="List all troubleshooting cases")
    parser.add_argument("--summary", action="store_true", help="Show system metrics and review summary")

    args = parser.parse_args()

    input_dir = root / "data" / "pkt_test_files" / "input"
    if not input_dir.exists():
        input_dir = root / "pkt_test_files" / "input"
    output_dir = root / "data" / "pkt_test_files" / "output"
    if not output_dir.exists() and (root / "pkt_test_files" / "output").exists():
        output_dir = root / "pkt_test_files" / "output"
    case_mgr = CaseManager()
    checker = DeterministicRuleChecker()
    diag = AIDiagnostician()
    review_mgr = HumanReviewManager()

    if args.extract:
        print(f"[*] Extracting PKT files from: {input_dir}")
        extract_xml(input_dir, output_dir, extract_features=True)
        print("[+] Batch extraction completed.")

    elif args.check_rules:
        cases = case_mgr.get_all_cases()
        print(f"[*] Running deterministic checks on {len(cases)} cases...")
        for c in cases:
            findings = checker.run_checks_on_case(c)
            print(f"[{c['case_id']}] {c['concept_tag']} ({c['severity']}): {len(findings)} findings")
            for f in findings:
                print(f"    - {f['title']} [{f['severity']}]")

    elif args.diagnose:
        case = case_mgr.get_case(args.diagnose)
        if not case:
            print(f"[-] Case {args.diagnose} not found.")
            sys.exit(1)
        findings = checker.run_checks_on_case(case)
        result = diag.diagnose_case(case, findings)
        print(f"\n[+] Diagnosis for {case['case_id']}:")
        print(f"  Root Cause: {result['root_cause']}")
        print(f"  Confidence: {result['confidence']*100:.1f}% ({result['confidence_level']})")
        print(f"  OSI Layer:  {result['osi_layer']}")
        print(f"  Next Cmd:   {result['next_command']}")
        print("  Fix Steps:")
        for step in result['fix_steps']:
            print(f"    {step}")

    elif args.list_cases:
        cases = case_mgr.get_all_cases()
        print(f"\nTotal Cases: {len(cases)}\n")
        print(f"{'Case ID':<14} | {'Concept':<12} | {'Layer':<20} | {'Severity':<10} | {'Symptom'}")
        print("-" * 90)
        for c in cases:
            symptom_snip = c['symptom'][:40] + "..." if len(c['symptom']) > 40 else c['symptom']
            print(f"{c['case_id']:<14} | {c['concept_tag']:<12} | {c['osi_layer'][:20]:<20} | {c['severity']:<10} | {symptom_snip}")

    elif args.summary or len(sys.argv) == 1:
        cases = case_mgr.get_all_cases()
        metrics = review_mgr.get_review_metrics()
        print(f"\nTotal Cases in Database: {len(cases)}")
        print(f"Human Review Summary: {metrics['total']} Diagnoses Logged")
        print(f"  - Accepted: {metrics['accepted']}")
        print(f"  - Edited:   {metrics['edited']}")
        print(f"  - Rejected: {metrics['rejected']}")
        print(f"  - Pending:  {metrics['pending']}")
        print(f"  - Agreement Rate: {metrics['agreement_rate']}%\n")
        print("To launch the interactive dashboard, run:")
        print("  streamlit run app.py\n")

if __name__ == "__main__":
    main()
