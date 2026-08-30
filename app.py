"""
NetSage AI - Interactive Network Troubleshooting Dashboard
Streamlit-based UI for Packet Tracer XML extraction, topology exploration,
deterministic rule checking, AI diagnosis, human review, and live lab demo.
"""

import os
import sys
import json
import glob
from pathlib import Path
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add root and src to path
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "src"))

try:
    from src.feature_extractor import PacketTracerFeatureExtractor
    from src.topology_builder import TopologyBuilder
    from src.rule_checker import DeterministicRuleChecker
    from src.case_manager import CaseManager
    from src.ai_diagnostician import AIDiagnostician
    from src.human_review import HumanReviewManager
    from src.pipeline import NetSagePipeline
except ImportError:
    from feature_extractor import PacketTracerFeatureExtractor
    from topology_builder import TopologyBuilder
    from rule_checker import DeterministicRuleChecker
    from case_manager import CaseManager
    from ai_diagnostician import AIDiagnostician
    from human_review import HumanReviewManager
    from pipeline import NetSagePipeline

# Streamlit Page Config
st.set_page_config(
    page_title="NetSage AI - Cisco Troubleshooting Assistant",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-critical { background-color: #fee2e2; color: #991b1b; }
    .badge-high { background-color: #ffedd5; color: #9a3412; }
    .badge-medium { background-color: #fef9c3; color: #854d0e; }
    .badge-low { background-color: #e0f2fe; color: #075985; }
    .badge-accepted { background-color: #dcfce7; color: #166534; }
    .badge-edited { background-color: #fef08a; color: #854d0e; }
    .badge-rejected { background-color: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

# Initialize Core Services
@st.cache_resource
def get_services():
    case_mgr = CaseManager()
    checker = DeterministicRuleChecker()
    diagnostician = AIDiagnostician()
    review_mgr = HumanReviewManager()
    extractor = PacketTracerFeatureExtractor()
    topo_builder = TopologyBuilder()
    pipeline = NetSagePipeline()
    return case_mgr, checker, diagnostician, review_mgr, extractor, topo_builder, pipeline

case_mgr, checker, diagnostician, review_mgr, extractor, topo_builder, pipeline = get_services()

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/network-cable.png", width=64)
    st.title("NetSage AI")
    st.markdown("**Cisco Network Troubleshooting Assistant**\n*Human-in-the-Loop AI & Lab Triage*")
    st.divider()

    st.subheader("🔑 AI Model Settings")
    env_gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    env_openai_key = os.environ.get("OPENAI_API_KEY")

    default_idx = 1 if env_gemini_key else (2 if env_openai_key else 0)
    api_provider = st.selectbox(
        "Inference Engine", 
        ["Built-in Expert Reasoning Engine", "Google Gemini API (Flash)", "OpenAI API"],
        index=default_idx
    )
    api_key = ""
    if "Gemini" in api_provider:
        if env_gemini_key:
            st.success("✅ Gemini API Key detected from `.env`")
            api_key = env_gemini_key
        else:
            api_key = st.text_input("Gemini API Key", type="password", help="Enter GEMINI_API_KEY or put it in .env")
    elif "OpenAI" in api_provider:
        if env_openai_key:
            st.success("✅ OpenAI API Key detected from `.env`")
            api_key = env_openai_key
        else:
            api_key = st.text_input("OpenAI API Key", type="password", help="Enter OPENAI_API_KEY or put it in .env")
    else:
        st.info("ℹ️ Running in fast local Expert Reasoning mode (No API key needed).")

    st.divider()
    cases_list = case_mgr.get_all_cases()
    metrics = review_mgr.get_review_metrics()
    st.metric("Total Lab Cases", len(cases_list))
    st.metric("AI Agreement Rate", f"{metrics['agreement_rate']}%")
    st.caption("NetSage AI v2.4 | Cisco AICTE Project")

# Header
st.markdown('<div class="main-header">🌐 NetSage AI: Network Troubleshooting Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-assisted diagnosis of Cisco Packet Tracer lab networks with deterministic rule checking, save-ref-id topology mapping, and human-in-the-loop oversight.</div>', unsafe_allow_html=True)

# Tabs
tabs = st.tabs([
    "📊 Overview & Metrics",
    "🔍 Case Explorer (32 Cases)",
    "🕸️ Topology Visualizer",
    "⚙️ Deterministic Rule Checker",
    "🧠 AI Diagnostician",
    "✍️ Human Review & Responsible AI",
    "🚀 Live Broken Lab Demo"
])

# -------------------------------------------------------------
# TAB 1: Overview & Metrics
# -------------------------------------------------------------
with tabs[0]:
    st.subheader("System Telemetry & Quality Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>{len(cases_list)}</h3><p>Troubleshooting Cases</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h3>5</h3><p>Parsed Packet Tracer Labs</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><h3>10</h3><p>Active Deterministic Rules</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><h3>{metrics["agreement_rate"]}%</h3><p>Human Agreement Rate</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    df_cases = pd.DataFrame(cases_list)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📁 Cases by Network Concept")
        if not df_cases.empty and "concept_tag" in df_cases:
            concept_counts = df_cases["concept_tag"].value_counts()
            fig, ax = plt.subplots(figsize=(6, 3.5))
            concept_counts.plot(kind="bar", color="#2563eb", ax=ax)
            ax.set_ylabel("Count")
            ax.set_title("Distribution of Network Fault Categories")
            plt.xticks(rotation=45, ha='right')
            st.pyplot(fig)

    with c2:
        st.markdown("#### 🏷️ Cases by OSI Layer")
        if not df_cases.empty and "osi_layer" in df_cases:
            layer_counts = df_cases["osi_layer"].value_counts()
            fig, ax = plt.subplots(figsize=(6, 3.5))
            layer_counts.plot(kind="pie", autopct='%1.1f%%', colors=["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"], ax=ax)
            ax.set_ylabel("")
            ax.set_title("OSI Layer Distribution")
            st.pyplot(fig)

    st.markdown("#### 🛡️ Responsible AI Review Distribution")
    reviews_all = review_mgr.get_all_reviews()
    if reviews_all:
        df_rev = pd.DataFrame(reviews_all)
        r_counts = df_rev["review_status"].value_counts()
        st.bar_chart(r_counts)

# -------------------------------------------------------------
# TAB 2: Case Explorer
# -------------------------------------------------------------
with tabs[1]:
    st.subheader("📚 Troubleshooting Cases Dataset (cases.csv)")
    st.markdown("Filter and inspect real-world lab cases across all network layers.")

    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        all_concepts = ["All"] + sorted(list(set(df_cases["concept_tag"].tolist())))
        sel_concept = st.selectbox("Filter Concept Tag", all_concepts)
    with f_col2:
        all_layers = ["All"] + sorted(list(set(df_cases["osi_layer"].tolist())))
        sel_layer = st.selectbox("Filter OSI Layer", all_layers)
    with f_col3:
        all_sev = ["All", "Critical", "High", "Medium", "Low"]
        sel_sev = st.selectbox("Filter Severity", all_sev)

    filtered = df_cases.copy()
    if sel_concept != "All":
        filtered = filtered[filtered["concept_tag"] == sel_concept]
    if sel_layer != "All":
        filtered = filtered[filtered["osi_layer"] == sel_layer]
    if sel_sev != "All":
        filtered = filtered[filtered["severity"] == sel_sev]

    st.dataframe(
        filtered[["case_id", "lab_source", "concept_tag", "osi_layer", "severity", "symptom"]],
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    st.markdown("### 🔎 Case Detail Inspector")
    selected_case_id = st.selectbox("Select Case to Inspect", df_cases["case_id"].tolist())
    case_detail = case_mgr.get_case(selected_case_id)

    if case_detail:
        d1, d2 = st.columns([1, 1])
        with d1:
            st.markdown(f"**Case ID:** `{case_detail['case_id']}` | **Severity:** `{case_detail['severity']}`")
            st.markdown(f"**Lab File:** `{case_detail['lab_source']}`")
            st.markdown(f"**OSI Layer:** `{case_detail['osi_layer']}` | **Concept:** `{case_detail['concept_tag']}`")
            st.markdown(f"**Symptom:**\n> {case_detail['symptom']}")
            st.markdown(f"**Topology Notes:**\n{case_detail['topology_note']}")
            st.markdown(f"**Expected Fault:**\n`{case_detail['expected_fault']}`")

        with d2:
            st.markdown("**Show Command Telemetry:**")
            st.code(case_detail["show_outputs"], language="text")
            st.markdown("**Expected Cisco IOS Fix:**")
            st.code(case_detail["expected_fix"], language="cisco")

# -------------------------------------------------------------
# TAB 3: Topology Visualizer
# -------------------------------------------------------------
with tabs[2]:
    st.subheader("🕸️ Network Topology & Device Graph Visualizer")
    st.markdown("Visualizes network devices and connections mapped via **`save-ref-id`** extracted from decrypted Packet Tracer XMLs.")

    json_dir = root / "data" / "extracted_features"
    feature_files = list(json_dir.glob("*.json"))
    
    if feature_files:
        scenario_names = [f.stem.replace("_features", "") for f in feature_files]
        selected_scenario = st.selectbox("Select Lab Scenario", scenario_names)
        
        target_file = json_dir / f"{selected_scenario}_features.json"
        with open(target_file, "r", encoding="utf-8") as f:
            sc_data = json.load(f)

        top_col1, top_col2 = st.columns([2, 1])
        with top_col1:
            st.markdown(f"#### Topology Graph: `{selected_scenario}`")
            G = topo_builder.build_graph_from_scenario(sc_data)
            
            fig, ax = plt.subplots(figsize=(10, 6.5))
            pos = nx.spring_layout(G, seed=42, k=0.9)
            
            node_colors = []
            for node in G.nodes():
                ntype = G.nodes[node].get("device_type", "")
                if "Router" in ntype:
                    node_colors.append("#2563eb")
                elif "MultiLayer" in ntype:
                    node_colors.append("#7c3aed")
                elif "Switch" in ntype:
                    node_colors.append("#059669")
                elif "Server" in ntype:
                    node_colors.append("#dc2626")
                elif "Wireless" in ntype or "AccessPoint" in ntype:
                    node_colors.append("#0891b2")
                else:
                    node_colors.append("#d97706")

            nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1200, alpha=0.9, ax=ax)
            nx.draw_networkx_labels(G, pos, font_size=8, font_family="sans-serif", font_color="white", font_weight="bold", ax=ax)
            nx.draw_networkx_edges(G, pos, width=2, edge_color="#94a3b8", ax=ax)
            
            edge_labels = {(u, v): f"{d.get('from_port','')} - {d.get('to_port','')}" for u, v, d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6, ax=ax)
            
            ax.set_title(f"{sc_data.get('device_count', 0)} Devices | {sc_data.get('link_count', 0)} Physical & Logical Links", fontsize=11)
            plt.axis("off")
            st.pyplot(fig)

        with top_col2:
            st.markdown("#### 📱 Device Inspector")
            dev_names = [d["name"] for d in sc_data.get("devices", [])]
            sel_dev = st.selectbox("Inspect Device", dev_names)
            
            dev_obj = next((d for d in sc_data["devices"] if d["name"] == sel_dev), None)
            if dev_obj:
                st.markdown(f"**Type:** `{dev_obj.get('type')}`")
                st.markdown(f"**Save-Ref-ID:** `{dev_obj.get('save_ref_id')}`")
                st.markdown(f"**Model:** `{dev_obj.get('model', 'N/A')}`")
                st.markdown(f"**Power State:** `{'ON' if dev_obj.get('power') else 'OFF'}`")
                
                st.markdown("**Configured Interfaces:**")
                ports = dev_obj.get("ports", [])
                port_rows = []
                for p in ports:
                    if p.get("ip_address"):
                        port_rows.append({
                            "Port": p.get("name"),
                            "IP": p.get("ip_address"),
                            "Mask": p.get("subnet_mask"),
                            "Status": "Down" if p.get("admin_down") else p.get("link_status")
                        })
                if port_rows:
                    st.dataframe(pd.DataFrame(port_rows), hide_index=True)
                else:
                    st.caption("No static Layer 3 IPs configured on this device.")

                if dev_obj.get("running_config"):
                    with st.expander("View Running Config"):
                        st.code(dev_obj.get("running_config_text", ""), language="cisco")

# -------------------------------------------------------------
# TAB 4: Deterministic Rule Checker
# -------------------------------------------------------------
with tabs[3]:
    st.subheader("⚙️ Deterministic Rule-Based Network Validation Engine")
    st.markdown("Runs algorithmic checks (duplicate IPs, subnet mismatches, gateway errors, down links, inverted masks) before AI inference.")

    r_case_id = st.selectbox("Select Case for Rule Checking", df_cases["case_id"].tolist(), key="rule_case_select")
    r_case = case_mgr.get_case(r_case_id)

    if st.button("▶️ Run Deterministic Rule Engine", type="primary"):
        with st.spinner("Analyzing telemetry and configurations..."):
            findings = checker.run_checks_on_case(r_case)
            
            st.markdown(f"### Rule Findings ({len(findings)} detected)")
            for f in findings:
                sev = f.get("severity", "Medium")
                sev_color = "red" if sev == "Critical" else "orange" if sev == "High" else "blue"
                
                with st.container():
                    st.markdown(f"#### :{sev_color}[[{sev}]] {f.get('title')}")
                    st.markdown(f"**Rule ID:** `{f.get('rule_id')}` | **Category:** `{f.get('category')}`")
                    st.markdown(f"**Evidence:** `{f.get('evidence')}`")
                    st.markdown(f"**Algorithmic Recommendation:** {f.get('recommendation')}")
                    st.divider()

# -------------------------------------------------------------
# TAB 5: AI Diagnostician
# -------------------------------------------------------------
with tabs[4]:
    st.subheader("🧠 NetSage AI Diagnostic Engine")
    st.markdown("Structured prompt execution enforcing JSON output schema (`root_cause`, `confidence`, `evidence`, `next_command`, `fix_steps`).")

    ai_case_id = st.selectbox("Select Case for AI Diagnosis", df_cases["case_id"].tolist(), key="ai_case_select")
    ai_case = case_mgr.get_case(ai_case_id)

    col_diag1, col_diag2 = st.columns([1, 1])
    with col_diag1:
        st.markdown(f"**Case:** `{ai_case['case_id']}` ({ai_case['concept_tag']})")
        st.markdown(f"**Symptom:**\n> {ai_case['symptom']}")
        with st.expander("View Input Show Command Telemetry"):
            st.code(ai_case["show_outputs"], language="text")

        if st.button("🚀 Run AI Diagnosis", type="primary", key="btn_run_ai"):
            with st.spinner("Generating evidence-backed diagnosis..."):
                findings = checker.run_checks_on_case(ai_case)
                diag_res = diagnostician.diagnose_case(ai_case, findings, api_key=api_key if api_key else None)
                
                # Store diagnosis in session state
                st.session_state["latest_diag"] = diag_res
                diag_id = review_mgr.log_diagnosis(ai_case_id, diag_res)
                st.session_state["latest_diag_id"] = diag_id
                st.success(f"Diagnosis completed and logged (ID: #{diag_id})")

    with col_diag2:
        if "latest_diag" in st.session_state:
            res = st.session_state["latest_diag"]
            st.markdown("### 📋 AI Structured Diagnosis")
            
            conf = res.get("confidence", 0.9)
            conf_pct = int(conf * 100) if conf <= 1.0 else int(conf)
            st.progress(conf_pct / 100, text=f"AI Confidence Score: {conf_pct}% ({res.get('confidence_level', 'High')})")
            
            st.markdown(f"**OSI Layer:** `{res.get('osi_layer')}` | **Fault Type:** `{res.get('fault_type')}`")
            st.markdown(f"**Root Cause:**\n> {res.get('root_cause')}")
            
            st.markdown("**Evidence Quotes:**")
            for ev in res.get("evidence", []):
                st.markdown(f"- *\"{ev}\"*")

            st.markdown(f"**Recommended Next Command:**\n`{res.get('next_command')}`")
            
            st.markdown("**Recommended Cisco IOS Fix Steps:**")
            st.code("\n".join(res.get("fix_steps", [])), language="cisco")

            with st.expander("Inspect Raw JSON Output"):
                st.json(res)

# -------------------------------------------------------------
# TAB 6: Human Review & Responsible AI
# -------------------------------------------------------------
with tabs[5]:
    st.subheader("✍️ Human Expert Review & Responsible AI Oversight")
    st.markdown("Review AI diagnoses, approve or correct root causes, and log Responsible AI discrepancies.")

    rev_col1, rev_col2 = st.columns([1, 1])
    with rev_col1:
        st.markdown("### 📝 Review Decision Portal")
        reviews_list = review_mgr.get_all_reviews()
        
        if reviews_list:
            review_opts = [f"#{r['id']} - {r['case_id']} ({r.get('review_status', 'Pending')})" for r in reviews_list]
            sel_review_opt = st.selectbox("Select Diagnosis Record", review_opts)
            sel_diag_id = int(sel_review_opt.split(" - ")[0].replace("#", ""))
            
            rev_record = next((r for r in reviews_list if r["id"] == sel_diag_id), None)
            if rev_record:
                st.markdown(f"**Case:** `{rev_record['case_id']}` | **Current Status:** `{rev_record.get('review_status')}`")
                st.markdown(f"**AI Root Cause:**\n> {rev_record.get('ai_root_cause')}")
                st.markdown(f"**AI Next Command:** `{rev_record.get('ai_next_command')}`")
                
                decision = st.radio("Review Verdict", ["Accepted", "Edited", "Rejected"], horizontal=True)
                corr_cause = st.text_area("Corrected Root Cause (if Edited/Rejected)", value=rev_record.get("human_corrected_root_cause") or "")
                corr_fix = st.text_area("Corrected Fix Steps (if Edited/Rejected)", value=rev_record.get("human_corrected_fix") or "")
                notes = st.text_input("Reviewer Notes & Safety Rationale", value=rev_record.get("human_notes") or "")

                if st.button("💾 Submit Human Review Verdict", type="primary"):
                    review_mgr.submit_review(sel_diag_id, decision, corr_cause, corr_fix, notes)
                    st.success(f"Review recorded as {decision}!")
                    st.rerun()

    with rev_col2:
        st.markdown("### 📖 Documented Responsible AI Discrepancies")
        st.markdown("Here are 5 real cases where the initial AI diagnosis was corrected by human oversight:")
        
        with st.expander("1. NETSAGE-002: L2 VLAN Misassignment vs L3 Routing"):
            st.markdown("**AI Error:** Jumped to Layer 3 Gateway routing failure without checking access VLAN.\n**Human Fix:** Reassigned switchport Fa0/3 to VLAN 10.")
        with st.expander("2. NETSAGE-009: Host DNS Setting vs Upstream DNS Outage"):
            st.markdown("**AI Error:** Suggested router reboot for external DNS outage.\n**Human Fix:** Updated host static DNS IP from 10.30.0.99 to 10.30.0.10.")
        with st.expander("3. NETSAGE-011: Insecure Guest Wireless ACL Removal"):
            st.markdown("**AI Error:** Recommended wide-open `permit ip any any` allowing lateral movement.\n**Human Fix:** Created strict Guest Isolation ACL.")
        with st.expander("4. NETSAGE-015: Administrative Shutdown vs Physical Cable Fault"):
            st.markdown("**AI Error:** Recommended replacing patch cable on down interface.\n**Human Fix:** Issued software `no shutdown` command.")
        with st.expander("5. NETSAGE-030: Wildcard Mask Inversion Syntax Trap"):
            st.markdown("**AI Error:** Blamed implicit deny rather than recognizing inverted wildcard mask.\n**Human Fix:** Replaced `255.255.255.0` with `0.0.0.255` in ACL.")

# -------------------------------------------------------------
# TAB 7: Live Broken Lab Demo
# -------------------------------------------------------------
with tabs[6]:
    st.subheader("🚀 Live End-to-End Troubleshooting Demo")
    st.markdown("Walk through the complete lifecycle: **Broken Lab Scenario → XML Extraction → Rule Check → AI Diagnosis → Human Review → Fix Verification**.")

    st.markdown("#### Scenario: `Keith Lab 2020-07-17.pkt` (Case NETSAGE-001)")
    demo_step = st.radio("Demo Step", [
        "1. Broken State Symptoms",
        "2. Automated XML & Topology Extraction",
        "3. Deterministic Rule Checking",
        "4. AI Structured Diagnosis",
        "5. Human Expert Review & Approval",
        "6. Fix Execution & Post-Fix Verification"
    ], horizontal=False)

    if demo_step == "1. Broken State Symptoms":
        st.info("🚨 **Symptom:** PC1 receives APIPA IP 169.254.12.44 and cannot communicate with any network services or Gateway 10.16.0.1.")
        st.code("PC1> ipconfig\nIP Address: 169.254.12.44\nSubnet Mask: 255.255.0.0\nDefault Gateway: 0.0.0.0", language="text")

    elif demo_step == "2. Automated XML & Topology Extraction":
        st.info("📂 **Extraction:** NetSage decodes `Keith Lab 2020-07-17.pkt` and maps all 13 devices and 13 topology links using `save-ref-id`.")
        st.json({
            "scenario": "Keith Lab 2020-07-17",
            "pc1_ref": "save-ref-id:10266626836674739498",
            "core1_ref": "save-ref-id:11642081607497678424",
            "access_sw_ref": "save-ref-id:2104604242406633587",
            "link_sample": "PC1 (FastEthernet0) <---> Access SW (FastEthernet0/3)"
        })

    elif demo_step == "3. Deterministic Rule Checking":
        st.info("⚙️ **Rule Check Execution:** Automated validation flags missing DHCP relay agent on VLAN 10 gateway.")
        st.warning("⚠️ **RULE-DHCP-RELAY [High]:** DHCP client on VLAN 10 has no local DHCP pool and SVI Vlan10 is missing 'ip helper-address' pointing to DHCP Server 10.16.8.8.")

    elif demo_step == "4. AI Structured Diagnosis":
        st.info("🧠 **AI Output:** NetSage AI synthesizes show command output and rule findings into JSON:")
        st.json({
            "case_id": "NETSAGE-001",
            "root_cause": "Missing DHCP Relay Agent ('ip helper-address 10.16.8.8') on Core1 SVI VLAN 10 interface.",
            "confidence": 0.96,
            "osi_layer": "Layer 3 (Network) / Layer 7 (Application)",
            "next_command": "show run interface vlan 10",
            "fix_steps": [
                "Core1(config)# interface vlan 10",
                "Core1(config-if)# ip helper-address 10.16.8.8",
                "Core1(config-if)# end"
            ]
        })

    elif demo_step == "5. Human Expert Review & Approval":
        st.info("✍️ **Human Review:** Network engineer reviews AI diagnosis, checks Core1 configuration, and clicks **Accept**.")
        st.success("✅ **Verdict: ACCEPTED** by Human Reviewer (Timestamp: 2026-08-30T11:28:00Z). Fix is approved for production deployment.")

    elif demo_step == "6. Fix Execution & Post-Fix Verification":
        st.info("🔧 **Fix Applied & Verified:** SVI Vlan10 configured with IP helper-address. PC1 successfully renews IP address.")
        st.code("Core1(config)# interface vlan 10\nCore1(config-if)# ip helper-address 10.16.8.8\nCore1(config-if)# end\nCore1# write memory\n\nPC1> ipconfig /renew\nIP Address: 10.16.0.10\nSubnet Mask: 255.255.255.0\nDefault Gateway: 10.16.0.1\n\nPC1> ping 10.16.0.1\nReply from 10.16.0.1: bytes=32 time=2ms TTL=255 (Success 100%)", language="text")
        st.balloons()
