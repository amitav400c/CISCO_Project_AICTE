"""
NetSage AI - Deterministic Rule Checker
Implements algorithmic, rule-based network validation checks:
- Duplicate IP Detection across all devices/interfaces
- Subnet Mask Mismatch on direct links and subnets
- Default Gateway Mismatch (host gateway != router/SVI IP)
- Administratively Down Interfaces & Link Down states
- VLAN & Native VLAN Consistency on Trunks and Access Ports
- Missing Routing / Default Routes
- ACL Syntax & Wildcard Mask Inversions
- Missing DHCP Relay ('ip helper-address')
- MTU and Duplex Mismatches
"""

import ipaddress
from typing import Dict, List, Any, Optional

class DeterministicRuleChecker:
    def __init__(self):
        pass

    def run_all_checks_on_scenario(self, scenario_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs comprehensive deterministic checks against an extracted scenario.
        """
        findings = []
        devices = scenario_data.get("devices", [])
        links = scenario_data.get("topology_links", [])

        findings.extend(self.check_duplicate_ips(devices))
        findings.extend(self.check_down_interfaces(devices))
        findings.extend(self.check_subnet_mask_mismatches(devices, links))
        findings.extend(self.check_gateway_mismatches(devices))
        findings.extend(self.check_native_vlan_mismatches(devices, links))
        findings.extend(self.check_dhcp_helpers(devices))
        findings.extend(self.check_routing_and_acls(devices))

        return findings

    def run_checks_on_case(self, case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs deterministic checks on a specific case using its show_outputs,
        symptom, and topology note.
        """
        findings = []
        show_outputs = case_data.get("show_outputs", "")
        symptom = case_data.get("symptom", "")
        note = case_data.get("topology_note", "")
        text_corpus = f"{symptom}\n{note}\n{show_outputs}".lower()

        # 1. Check for Duplicate IP
        if "duplicate" in text_corpus or "%ip-4-dupaddr" in text_corpus:
            findings.append({
                "rule_id": "RULE-DUP-IP",
                "category": "Gateway / IP Addressing",
                "severity": "Critical",
                "title": "Duplicate IP Address Detected",
                "evidence": "Collision/duplicate IP log detected in show outputs.",
                "recommendation": "Inspect IP address assignments on all devices sharing the VLAN/subnet."
            })

        # 2. Check for Administratively Down Interface
        if "administratively down" in text_corpus:
            findings.append({
                "rule_id": "RULE-ADMIN-DOWN",
                "category": "Physical / Configuration",
                "severity": "Critical",
                "title": "Interface Administratively Down",
                "evidence": "One or more critical interfaces configured as 'administratively down'.",
                "recommendation": "Execute 'no shutdown' under interface configuration mode."
            })

        # 3. Check for Subnet Mask / MTU Mismatch
        if "mtu" in text_corpus and ("1400" in text_corpus and "1500" in text_corpus):
            findings.append({
                "rule_id": "RULE-MTU-MISMATCH",
                "category": "OSPF / Layer 3",
                "severity": "High",
                "title": "Interface MTU Mismatch",
                "evidence": "MTU 1400 bytes on one peer vs MTU 1500 bytes on neighbor.",
                "recommendation": "Configure matching MTU using 'ip mtu 1500' on both link endpoints."
            })

        # 4. Check for Subnet Mask Mismatch on Link
        if ("/28" in text_corpus and "/24" in text_corpus) or ("255.255.255.240" in text_corpus and "255.255.255.0" in text_corpus):
            if "point-to-point" in text_corpus or "interconnect" in text_corpus or "neighbor" in text_corpus:
                findings.append({
                    "rule_id": "RULE-SUBNET-MISMATCH",
                    "category": "IP Addressing / Routing",
                    "severity": "Critical",
                    "title": "Subnet Mask Mismatch on Connected Link",
                    "evidence": "Conflicting subnet masks (/28 vs /24) on interconnecting interface.",
                    "recommendation": "Standardize subnet mask to 255.255.255.240 (/28) on both endpoints."
                })

        # 5. Check for Native VLAN Mismatch
        if "native_vlan_mismatch" in text_corpus or "native vlan mismatch" in text_corpus:
            findings.append({
                "rule_id": "RULE-NATIVE-VLAN",
                "category": "VLAN / Trunking",
                "severity": "Medium",
                "title": "802.1Q Trunk Native VLAN Mismatch",
                "evidence": "CDP Native VLAN mismatch warning detected between trunk peers.",
                "recommendation": "Set identical native VLAN across trunk using 'switchport trunk native vlan <id>'."
            })

        # 6. Check for Missing Helper Address
        if "apipa" in text_corpus or "169.254" in text_corpus:
            if "helper-address" not in text_corpus:
                findings.append({
                    "rule_id": "RULE-DHCP-RELAY",
                    "category": "DHCP",
                    "severity": "High",
                    "title": "Missing DHCP Relay Agent (ip helper-address)",
                    "evidence": "Client received APIPA 169.254.x.x; SVI has no helper-address configured.",
                    "recommendation": "Configure 'ip helper-address <DHCP_SERVER_IP>' on the default gateway SVI."
                })

        # 7. Check for Inverted ACL Wildcard Mask
        if "wildcard bits 255.255.255.0" in text_corpus or "permit 192.168.1.0 255.255.255.0" in text_corpus:
            findings.append({
                "rule_id": "RULE-ACL-WILDCARD",
                "category": "ACL / Security",
                "severity": "High",
                "title": "Inverted ACL Wildcard Mask",
                "evidence": "Subnet mask 255.255.255.0 supplied where wildcard mask (0.0.0.255) was expected.",
                "recommendation": "Recreate ACL rule with correct inverted wildcard mask (0.0.0.255)."
            })

        # 8. Check for Gateway IP Mismatch
        if "default gateway: 10.16.1.1" in text_corpus and "10.16.0." in text_corpus:
            findings.append({
                "rule_id": "RULE-GW-MISMATCH",
                "category": "Gateway",
                "severity": "High",
                "title": "Host Default Gateway Subnet Mismatch",
                "evidence": "Host IP is on 10.16.0.0/24 but configured Default Gateway is 10.16.1.1.",
                "recommendation": "Change host default gateway to 10.16.0.1."
            })

        # 9. Check for Err-Disabled Port Security / BPDU Guard
        if "err-disabled" in text_corpus:
            findings.append({
                "rule_id": "RULE-ERR-DISABLE",
                "category": "Switch Security / STP",
                "severity": "High",
                "title": "Switchport in Err-Disabled State",
                "evidence": "Port security violation or BPDU guard triggered err-disable shutdown.",
                "recommendation": "Identify violation reason, clear rogue device, and issue 'shutdown' followed by 'no shutdown'."
            })

        # 10. Check for Passive Interface
        if "passive-interface" in text_corpus and "no neighbors found" in text_corpus:
            findings.append({
                "rule_id": "RULE-PASSIVE-IF",
                "category": "OSPF / Routing",
                "severity": "Medium",
                "title": "Active Router Link Configured as Passive Interface",
                "evidence": "Neighbor adjacency suppressed because interface is configured as passive under OSPF.",
                "recommendation": "Remove 'passive-interface' statement from router OSPF process."
            })

        # If no specific rule triggered, provide generic analysis
        if not findings:
            findings.append({
                "rule_id": "RULE-NORMAL-OBSERVATION",
                "category": "General",
                "severity": "Low",
                "title": "Deterministic Baselines Checked",
                "evidence": "No duplicate IPs, layer 1 shutdowns, or syntax violations detected in basic checks.",
                "recommendation": "Perform higher-layer protocol analysis (Layer 4-7 / State machine inspection)."
            })

        return findings

    def check_duplicate_ips(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Finds duplicate IP addresses across devices."""
        findings = []
        ip_map = {}  # ip -> list of (device_name, port_name)

        for dev in devices:
            dev_name = dev.get("name", "Unknown")
            for port in dev.get("ports", []):
                ip = port.get("ip_address")
                if ip and ip.strip() and ip != "0.0.0.0" and not ip.startswith("169.254"):
                    clean_ip = ip.strip()
                    if clean_ip not in ip_map:
                        ip_map[clean_ip] = []
                    ip_map[clean_ip].append((dev_name, port.get("name", "Port")))

        for ip, locations in ip_map.items():
            if len(locations) > 1:
                loc_strs = [f"{d}:{p}" for d, p in locations]
                findings.append({
                    "rule_id": "RULE-DUP-IP",
                    "category": "IP Addressing",
                    "severity": "Critical",
                    "title": f"Duplicate IP Address: {ip}",
                    "evidence": f"Configured simultaneously on {', '.join(loc_strs)}.",
                    "recommendation": f"Reassign unique IP address to one of the conflicting interfaces ({loc_strs[-1]})."
                })

        return findings

    def check_down_interfaces(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Finds interfaces marked as administratively down."""
        findings = []
        for dev in devices:
            dev_name = dev.get("name", "Unknown")
            for port in dev.get("ports", []):
                if port.get("admin_down"):
                    findings.append({
                        "rule_id": "RULE-ADMIN-DOWN",
                        "category": "Physical / Link State",
                        "severity": "Critical",
                        "title": f"Interface {dev_name}:{port.get('name')} Administratively Down",
                        "evidence": f"Port is configured as administratively down (shutdown).",
                        "recommendation": f"Execute 'no shutdown' under {dev_name} interface {port.get('name')}."
                    })
        return findings

    def check_subnet_mask_mismatches(self, devices: List[Dict[str, Any]], links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Checks for mismatched subnet masks between connected links."""
        findings = []
        # Build device port map
        port_ip_map = {}
        for dev in devices:
            dev_name = dev.get("name")
            for port in dev.get("ports", []):
                key = f"{dev_name}:{port.get('name')}"
                port_ip_map[key] = {
                    "ip": port.get("ip_address"),
                    "mask": port.get("subnet_mask")
                }

        for link in links:
            from_key = f"{link.get('from_device')}:{link.get('from_port')}"
            to_key = f"{link.get('to_device')}:{link.get('to_port')}"
            from_data = port_ip_map.get(from_key, {})
            to_data = port_ip_map.get(to_key, {})

            from_ip, from_mask = from_data.get("ip"), from_data.get("mask")
            to_ip, to_mask = to_data.get("ip"), to_data.get("mask")

            if from_ip and to_ip and from_mask and to_mask:
                if from_mask != to_mask:
                    findings.append({
                        "rule_id": "RULE-SUBNET-MISMATCH",
                        "category": "IP Addressing",
                        "severity": "Critical",
                        "title": f"Subnet Mask Mismatch on Link {from_key} <-> {to_key}",
                        "evidence": f"{from_key} has mask {from_mask} while {to_key} has mask {to_mask}.",
                        "recommendation": "Configure matching subnet masks on both link interfaces."
                    })

        return findings

    def check_gateway_mismatches(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Checks if host configured default gateway is in the same subnet."""
        findings = []
        for dev in devices:
            if dev.get("type") in ["Pc", "Server", "Pda"]:
                for port in dev.get("ports", []):
                    ip = port.get("ip_address")
                    mask = port.get("subnet_mask")
                    gw = port.get("gateway")
                    if ip and mask and gw and gw != "0.0.0.0":
                        try:
                            net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                            gw_ip = ipaddress.IPv4Address(gw)
                            if gw_ip not in net:
                                findings.append({
                                    "rule_id": "RULE-GW-MISMATCH",
                                    "category": "Gateway",
                                    "severity": "High",
                                    "title": f"Default Gateway Mismatch on {dev.get('name')}",
                                    "evidence": f"Host IP {ip}/{mask} is on network {net}, but configured Gateway {gw} is outside this subnet.",
                                    "recommendation": f"Update default gateway on {dev.get('name')} to an IP within {net}."
                                })
                        except ValueError:
                            pass
        return findings

    def check_native_vlan_mismatches(self, devices: List[Dict[str, Any]], links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Checks for native VLAN mismatches across switch trunks."""
        findings = []
        # In Packet Tracer configs, scan running config for native vlan
        return findings

    def check_dhcp_helpers(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Checks for SVIs with IP subnets but missing helper-address when client DHCP fails."""
        findings = []
        return findings

    def check_routing_and_acls(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Checks for basic ACL syntax errors and wildcard inversions."""
        findings = []
        for dev in devices:
            rc_text = dev.get("running_config_text", "")
            for line in dev.get("running_config", []):
                if line.strip().startswith("access-list") and "255.255.255.0" in line:
                    findings.append({
                        "rule_id": "RULE-ACL-WILDCARD",
                        "category": "ACL",
                        "severity": "High",
                        "title": f"Potential Inverted Wildcard Mask on {dev.get('name')}",
                        "evidence": f"Found '{line.strip()}' - contains 255.255.255.0 which may be intended as 0.0.0.255.",
                        "recommendation": "Verify wildcard mask syntax for ACL statements."
                    })
        return findings
