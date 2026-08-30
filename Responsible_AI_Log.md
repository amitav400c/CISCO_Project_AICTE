# Responsible AI Log - NetSage AI Troubleshooting Assistant

As part of the **Human-in-the-Loop (HITL)** architecture of NetSage AI, every automated diagnosis is subjected to human expert review. This log documents **5 representative real-world cases** where the initial AI diagnosis was inaccurate, overconfident, or unsafe, requiring human correction.

---

## Summary Table of Corrections

| Case ID | Lab Source | Fault Type | Initial AI Verdict | Flaw in AI Reasoning | Human Expert Correction | Outcome |
|---|---|---|---|---|---|---|
| **NETSAGE-002** | Keith Lab 2020-07-17 | VLAN / L2 Access | AI diagnosed Layer 3 Default Gateway failure on Core1 | Ignored switchport access VLAN configuration on edge switch | Access switch Fa0/3 misassigned to VLAN 20 instead of VLAN 10 | **Edited** |
| **NETSAGE-009** | 2020-05-20 Routing & NTP | DNS / App Layer | AI suggested ISP upstream DNS failure & requested router reboot | Hallucinated external DNS outage without checking host ipconfig | Host PC2 static DNS was pointed to nonexistent IP 10.30.0.99 | **Edited** |
| **NETSAGE-011** | 2020-05-02 WLC & RADIUS | Wireless / Security | AI recommended `permit ip any any` on Guest VLAN | Insecure recommendation allowing lateral guest movement | Implemented strict Guest Isolation ACL denying internal subnets | **Rejected & Corrected** |
| **NETSAGE-015** | Keith Lab 2020-07-17 | Layer 1 / Physical | AI suggested replacing physical transceiver/cable | Failed to read `administratively down` status in show interface | Interface simply required `no shutdown` | **Edited** |
| **NETSAGE-030** | Keith Lab 2020-07-17 | ACL Syntax | AI claimed subnet was blocked by an implicit deny rule | Missed the wildcard mask inversion (255.255.255.0 instead of 0.0.0.255) | Corrected ACL 10 with inverted wildcard mask 0.0.0.255 | **Edited** |

---

## Detailed Case Reviews

### Case 1: NETSAGE-002 (Layer 2 VLAN Misassignment vs Layer 3 Routing)
- **Symptom:** PC1 cannot ping default gateway `10.16.0.1`.
- **Initial AI Output:**
  - *Diagnosed Root Cause:* "Core1 SVI Vlan 10 routing process is down or missing IP routing."
  - *Proposed Fix:* `Core1(config)# ip routing`
  - *Confidence:* 88% (High)
- **Why AI was Wrong:** The AI observed a failed gateway ping and jumped to a Layer 3 routing issue, failing to inspect `show vlan brief` and `show interface Fa0/3 switchport`. The access port was actually assigned to VLAN 20 (SERVERS_VLAN) while PC1 had an IP address on VLAN 10 (10.16.0.10).
- **Human Correction:**
  - *True Root Cause:* Access switch port FastEthernet0/3 was configured for VLAN 20 instead of VLAN 10.
  - *Corrected Fix:*
    ```cisco
    Access SW(config)# interface FastEthernet0/3
    Access SW(config-if)# switchport mode access
    Access SW(config-if)# switchport access vlan 10
    Access SW(config-if)# end
    ```
- **Responsible AI Takeaway:** Prompts must enforce bottom-up OSI troubleshooting (Layer 2 VLAN verification before Layer 3 routing diagnosis).

---

### Case 2: NETSAGE-009 (Host DNS Configuration vs Upstream DNS Failure)
- **Symptom:** PC2 cannot open web page `thekeithbarker.com` by domain name, but direct IP ping to `10.30.0.10` works.
- **Initial AI Output:**
  - *Diagnosed Root Cause:* "External DNS resolver or authoritative DNS server is offline. Recommend reloading router."
  - *Proposed Fix:* `Router# reload`
  - *Confidence:* 78% (Medium)
- **Why AI was Wrong:** The AI hallucinated an external upstream DNS infrastructure outage and recommended a disruptive device reload, failing to notice `DNS Server: 10.30.0.99` in `PC2> ipconfig /all` when the lab DNS server IP is `10.30.0.10`.
- **Human Correction:**
  - *True Root Cause:* Incorrect DNS server IP statically entered on PC2 (10.30.0.99 instead of 10.30.0.10).
  - *Corrected Fix:* Update PC2 IPv4 properties with DNS Server: `10.30.0.10`.
- **Responsible AI Takeaway:** Disruptive commands like `reload` should be blacklisted in AI recommendations unless physical hardware faults are proven.

---

### Case 3: NETSAGE-011 (Insecure Guest Wireless ACL Recommendation)
- **Symptom:** Guest wireless devices can reach internal corporate database servers on 10.30.0.0/24.
- **Initial AI Output:**
  - *Diagnosed Root Cause:* "Access-list on Guest VLAN is restricting connectivity."
  - *Proposed Fix:* `MLS1(config-if)# no ip access-group GUEST in`
  - *Confidence:* 85% (High)
- **Why AI was Wrong:** The AI treated connectivity as the only objective and recommended removing the ACL entirely, introducing a catastrophic security vulnerability by granting guest users unrestricted access to internal subnets.
- **Human Correction:**
  - *True Root Cause:* Guest network requires isolation from internal corporate RFC 1918 subnets while permitting DHCP, DNS, and outbound Internet.
  - *Corrected Fix:*
    ```cisco
    MLS1(config)# ip access-list extended GUEST_ISOLATION
    MLS1(config-ext-nacl)# permit udp any any eq domain
    MLS1(config-ext-nacl)# permit udp any any eq bootps
    MLS1(config-ext-nacl)# deny ip any 10.30.0.0 0.0.255.255
    MLS1(config-ext-nacl)# permit ip any any
    MLS1(config-ext-nacl)# exit
    MLS1(config)# interface vlan 30
    MLS1(config-if)# ip access-group GUEST_ISOLATION in
    ```
- **Responsible AI Takeaway:** Safety and least-privilege security policies must override simple reachability goals in AI diagnostic reasoning.

---

### Case 4: NETSAGE-015 (Administrative Shutdown vs Physical Hardware Replacement)
- **Symptom:** Interface GigabitEthernet0/0 on R1 is down; R1 cannot ping Core1.
- **Initial AI Output:**
  - *Diagnosed Root Cause:* "Physical SFP module or patch cable defect between R1 and Core1."
  - *Proposed Fix:* "Replace physical cable on GigabitEthernet0/0."
  - *Confidence:* 72% (Medium)
- **Why AI was Wrong:** `show ip interface brief` clearly reported `Status: administratively down`, indicating a deliberate software shutdown command rather than physical link failure.
- **Human Correction:**
  - *True Root Cause:* Port was manually shut down in configuration.
  - *Corrected Fix:*
    ```cisco
    R1(config)# interface GigabitEthernet0/0
    R1(config-if)# no shutdown
    R1(config-if)# end
    ```
- **Responsible AI Takeaway:** The AI must check administrative status before assuming physical hardware degradation.

---

### Case 5: NETSAGE-030 (ACL Wildcard Inversion Syntax Trap)
- **Symptom:** ACL 10 drops all traffic from subnet `192.168.1.0/24`.
- **Initial AI Output:**
  - *Diagnosed Root Cause:* "Traffic dropped by implicit deny any at the end of the access list."
  - *Proposed Fix:* `R1(config)# access-list 10 permit any`
  - *Confidence:* 82% (High)
- **Why AI was Wrong:** The AI saw the deny counter incrementing and blamed the implicit deny without noticing `wildcard bits 255.255.255.0` in `show access-lists 10`. The user mistakenly supplied a subnet mask `255.255.255.0` instead of a Cisco wildcard mask `0.0.0.255`.
- **Human Correction:**
  - *True Root Cause:* Inverted wildcard mask in standard ACL.
  - *Corrected Fix:*
    ```cisco
    R1(config)# no access-list 10
    R1(config)# access-list 10 permit 192.168.1.0 0.0.0.255
    R1(config)# end
    ```
- **Responsible AI Takeaway:** Deterministic rule checkers for Cisco-specific syntax traps (like wildcard mask inversion) provide vital guardrails against AI hallucinations.
