"""
NetSage AI - Case Manager & Dataset Generator
Manages loading, querying, and updating the 30+ troubleshooting cases
across CSV and SQLite database storage.
"""

import os
import csv
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

CASES_DATA = [
    {
        "case_id": "NETSAGE-001",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "PC1 is unable to obtain an IP address via DHCP and receives APIPA address (169.254.x.x). Cannot reach default gateway or any network resources.",
        "topology_note": "PC1 connected to Access SW (FastEthernet0/3) in VLAN 10. Core1 acts as Layer 3 Gateway (SVI VLAN 10). DHCP Server is located on Server2 (10.16.8.8) on separate subnet.",
        "show_outputs": """PC1> ipconfig
IP Address: 169.254.12.44
Subnet Mask: 255.255.0.0
Default Gateway: 0.0.0.0

Core1# show run interface vlan 10
interface Vlan10
 ip address 10.16.0.1 255.255.255.0
!
Core1# show ip dhcp snooping
DHCP Snooping is enabled on VLAN 10""",
        "expected_fault": "Missing DHCP Relay Agent ('ip helper-address 10.16.8.8') on Core1 SVI VLAN 10 interface.",
        "osi_layer": "Layer 3 (Network) / Layer 7 (Application)",
        "concept_tag": "DHCP",
        "severity": "High",
        "deterministic_findings": "RULE_WARNING: DHCP client on VLAN 10 has no local DHCP pool and SVI Vlan10 is missing 'ip helper-address' pointing to DHCP Server 10.16.8.8.",
        "expected_next_command": "show run interface vlan 10",
        "expected_fix": "Core1(config)# interface vlan 10\nCore1(config-if)# ip helper-address 10.16.8.8\nCore1(config-if)# end\nCore1# write memory"
    },
    {
        "case_id": "NETSAGE-002",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "PC1 has static IP 10.16.0.10/24 configured but cannot ping default gateway 10.16.0.1.",
        "topology_note": "PC1 is connected to Access SW port FastEthernet0/3. Gateway 10.16.0.1 resides on Core1 SVI Vlan 10.",
        "show_outputs": """PC1> ping 10.16.0.1
Pinging 10.16.0.1 with 32 bytes of data:
Request timed out.
Request timed out.

Access SW# show vlan brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/1, Fa0/2, Fa0/4 - Fa0/24
10   USERS_VLAN                       active    
20   SERVERS_VLAN                     active    Fa0/3

Access SW# show interface FastEthernet0/3 switchport
Name: Fa0/3
Administrative Mode: static access
Access Mode VLAN: 20 (SERVERS_VLAN)""",
        "expected_fault": "Access Switch port FastEthernet0/3 assigned to wrong VLAN (VLAN 20 instead of VLAN 10).",
        "osi_layer": "Layer 2 (Data Link)",
        "concept_tag": "VLAN",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: Host PC1 IP subnet (10.16.0.0/24 - VLAN 10) connected to switchport Fa0/3 configured with Access VLAN 20.",
        "expected_next_command": "show interface FastEthernet0/3 switchport",
        "expected_fix": "Access SW(config)# interface FastEthernet0/3\nAccess SW(config-if)# switchport mode access\nAccess SW(config-if)# switchport access vlan 10\nAccess SW(config-if)# end"
    },
    {
        "case_id": "NETSAGE-003",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Inter-VLAN communication fails: PC1 (VLAN 10) cannot reach Server3 (VLAN 30). Gateway ping to 10.16.0.1 succeeds.",
        "topology_note": "Trunk connection between Access SW (Fa0/1) and Core1 (Gi1/0/4) carries VLAN traffic.",
        "show_outputs": """Access SW# show interfaces trunk
Port        Mode         Encapsulation  Status        Native vlan
Fa0/1       on           802.1q         trunking      1

Port        Vlans allowed on trunk
Fa0/1       10,20

Core1# show interfaces trunk
Port        Mode         Encapsulation  Status        Native vlan
Gi1/0/4     on           802.1q         trunking      1

Port        Vlans allowed on trunk
Gi1/0/4     1-4094""",
        "expected_fault": "Trunk port Fa0/1 on Access SW is missing VLAN 30 in the allowed VLAN list.",
        "osi_layer": "Layer 2 (Data Link)",
        "concept_tag": "VLAN",
        "severity": "Medium",
        "deterministic_findings": "RULE_WARNING: Trunk link Access SW:Fa0/1 to Core1:Gi1/0/4 allowed VLAN list '10,20' excludes active VLAN 30.",
        "expected_next_command": "show interfaces Fa0/1 switchport",
        "expected_fix": "Access SW(config)# interface FastEthernet0/1\nAccess SW(config-if)# switchport trunk allowed vlan add 30\nAccess SW(config-if)# end"
    },
    {
        "case_id": "NETSAGE-004",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Intermittent connectivity to Gateway 10.16.0.1 from PC1. Duplicate IP address collision logged.",
        "topology_note": "Core1 SVI Vlan 10 has IP 10.16.0.1. A rogue or misconfigured Server was recently connected to SW2.",
        "show_outputs": """Core1# show log
%IP-4-DUPADDR: Duplicate address 10.16.0.1 on Vlan10, sourced by 0001.974c.6b79

SW2# show mac address-table | include 0001.974c.6b79
10    0001.974c.6b79    DYNAMIC     Fa0/2

Server2# show ip interface brief
FastEthernet0       10.16.0.1       YES manual up                    up""",
        "expected_fault": "Duplicate IP address configured on Server2 (10.16.0.1) conflicting with Core1 Gateway IP.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "Gateway",
        "severity": "Critical",
        "deterministic_findings": "RULE_ERROR: Duplicate IP Address detected: 10.16.0.1 is configured on both Core1 (Vlan10) and Server2 (FastEthernet0).",
        "expected_next_command": "show ip interface brief",
        "expected_fix": "Server2(config)# interface FastEthernet0\nServer2(config-if)# ip address 10.16.8.8 255.255.255.0\nServer2(config-if)# end"
    },
    {
        "case_id": "NETSAGE-005",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "PC1 (10.16.0.10) cannot reach Server2 (10.16.8.8). Ping from PC1 to R1 (10.16.6.5) succeeds, but ping to 10.16.8.8 fails.",
        "topology_note": "Core1 connects to R1 via Gi1/0/3. R1 connects to R2 via MetroE. R2 connects to Server2 via SW2.",
        "show_outputs": """R1# show ip route 10.16.8.0
% Subnet not in table

R1# show ip route
Gateway of last resort is not set
     10.0.0.0/8 is variably subnetted, 4 subnets, 2 masks
C       10.16.6.0/24 is directly connected, GigabitEthernet0/0
C       10.16.7.0/28 is directly connected, GigabitEthernet0/2
C       192.168.1.0/24 is directly connected, GigabitEthernet0/1

R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   FULL/BDR        00:00:33    10.16.7.6       GigabitEthernet0/2""",
        "expected_fault": "Missing route to destination subnet 10.16.8.0/24 on Router R1; R2 is not advertising 10.16.8.0/24 into OSPF.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "Routing",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: No route to destination subnet 10.16.8.0/24 found in R1 routing table.",
        "expected_next_command": "show ip ospf neighbor on R2 and show run | section router ospf",
        "expected_fix": "R2(config)# router ospf 1\nR2(config-router)# network 10.16.8.0 0.0.0.255 area 0\nR2(config-router)# end"
    },
    {
        "case_id": "NETSAGE-006",
        "lab_source": "2020-06-18 OSPF.pkt",
        "symptom": "OSPF neighbor adjacency between R1 and R2 is stuck in EXSTART/EXCHANGE state and never reaches FULL.",
        "topology_note": "R1 and R2 connect over point-to-point GigabitEthernet0/2 link.",
        "show_outputs": """R1# show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           1   EXSTART/ -      00:00:38    10.16.7.6       GigabitEthernet0/2

R1# show interface GigabitEthernet0/2 | include MTU
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec

R2# show interface GigabitEthernet0/0 | include MTU
  MTU 1400 bytes, BW 1000000 Kbit/sec, DLY 10 usec""",
        "expected_fault": "MTU mismatch on OSPF link between R1 (MTU 1500) and R2 (MTU 1400) preventing DBD packet exchange.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "OSPF",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: MTU mismatch detected on link R1:Gi0/2 (MTU 1500) <-> R2:Gi0/0 (MTU 1400).",
        "expected_next_command": "show interface GigabitEthernet0/0 | include MTU on both routers",
        "expected_fix": "R2(config)# interface GigabitEthernet0/0\nR2(config-if)# ip mtu 1500\nR2(config-if)# end"
    },
    {
        "case_id": "NETSAGE-007",
        "lab_source": "2020-06-18 OSPF.pkt",
        "symptom": "R1 and MetroE switch fail to form OSPF adjacency on point-to-point link Gi0/2 <-> Gi1/0/1.",
        "topology_note": "Link connecting R1 Gi0/2 to MetroE Gi1/0/1.",
        "show_outputs": """R1# show ip interface GigabitEthernet0/2
GigabitEthernet0/2 is up, line protocol is up
  Internet address is 10.16.7.5/28
  Broadcast address is 10.16.7.15

MetroE# show ip interface GigabitEthernet1/0/1
GigabitEthernet1/0/1 is up, line protocol is up
  Internet address is 10.16.7.1/24
  Broadcast address is 10.16.7.255""",
        "expected_fault": "Subnet mask mismatch on interconnect link: R1 configured with /28 (255.255.255.240) and MetroE with /24 (255.255.255.0).",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "OSPF",
        "severity": "Critical",
        "deterministic_findings": "RULE_ERROR: Subnet mask mismatch on link R1:Gi0/2 (255.255.255.240) <-> MetroE:Gi1/0/1 (255.255.255.0).",
        "expected_next_command": "show ip interface brief",
        "expected_fix": "MetroE(config)# interface GigabitEthernet1/0/1\nMetroE(config-if)# ip address 10.16.7.1 255.255.255.240\nMetroE(config-if)# end"
    },
    {
        "case_id": "NETSAGE-008",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "R1 is not forming OSPF adjacency with Core1 across Gi0/0 <-> Gi1/0/3 link.",
        "topology_note": "R1 connects to Core1 over subnet 10.16.6.0/24.",
        "show_outputs": """R1# show run | section router ospf
router ospf 1
 router-id 3.3.3.3
 passive-interface GigabitEthernet0/0
 network 10.16.6.0 0.0.0.255 area 0
 network 10.16.7.0 0.0.0.15 area 0

R1# show ip ospf neighbor
% No neighbors found on GigabitEthernet0/0""",
        "expected_fault": "Interface GigabitEthernet0/0 is configured as passive-interface under OSPF on R1, suppressing Hello packets.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "OSPF",
        "severity": "Medium",
        "deterministic_findings": "RULE_WARNING: Interface GigabitEthernet0/0 is set to passive-interface under router ospf 1 despite having an active router neighbor.",
        "expected_next_command": "show ip ospf interface GigabitEthernet0/0",
        "expected_fix": "R1(config)# router ospf 1\nR1(config-router)# no passive-interface GigabitEthernet0/0\nR1(config-router)# end"
    },
    {
        "case_id": "NETSAGE-009",
        "lab_source": "2020-05-20 Routing  NTP and more WTW.pkt",
        "symptom": "PC2 cannot open web page 'thekeithbarker.com' in web browser, but direct ping to Server IP 10.30.0.10 succeeds.",
        "topology_note": "PC2 is on corporate LAN. Web and DNS services are hosted on Server (10.30.0.10).",
        "show_outputs": """PC2> ping thekeithbarker.com
Host name could not be resolved: thekeithbarker.com

PC2> ping 10.30.0.10
Pinging 10.30.0.10 with 32 bytes of data:
Reply from 10.30.0.10: bytes=32 time=4ms TTL=126

PC2> ipconfig /all
IP Address: 10.30.10.50
Subnet Mask: 255.255.255.0
Default Gateway: 10.30.10.1
DNS Server: 10.30.0.99""",
        "expected_fault": "Incorrect DNS Server IP configured on PC2 (10.30.0.99 instead of 10.30.0.10).",
        "osi_layer": "Layer 7 (Application)",
        "concept_tag": "DNS",
        "severity": "Medium",
        "deterministic_findings": "RULE_ERROR: Host PC2 DNS server IP 10.30.0.99 does not match known DNS server 10.30.0.10.",
        "expected_next_command": "ipconfig /all on PC2 and nslookup thekeithbarker.com",
        "expected_fix": "Configure PC2 network settings with DNS Server: 10.30.0.10."
    },
    {
        "case_id": "NETSAGE-010",
        "lab_source": "2020-05-16 AAA NTP For Learnersv3.pkt",
        "symptom": "Bob (Wireless Employee device, 10.30.20.50) cannot SSH to MLS1 management IP 10.30.0.1. Connection refused or timed out.",
        "topology_note": "Employee wireless client subnet 10.30.20.0/24 connects via WLC and MLS1.",
        "show_outputs": """Bob> ssh -l admin 10.30.0.1
Connection to 10.30.0.1 closed by remote host.

MLS1# show access-lists 100
Extended IP access list 100
    10 permit tcp 10.30.10.0 0.0.0.255 any eq 22 (45 matches)
    20 deny ip any any (120 matches)

MLS1# show run | section line vty
line vty 0 4
 access-class 100 in
 login authentication default
 transport input ssh""",
        "expected_fault": "Access-class ACL 100 on MLS1 VTY lines is missing permit statement for Employee subnet (10.30.20.0/24).",
        "osi_layer": "Layer 4 (Transport) / Layer 7 (Application)",
        "concept_tag": "ACL",
        "severity": "High",
        "deterministic_findings": "RULE_WARNING: ACL 100 on line vty explicitly denies subnet 10.30.20.0/24 with implicit deny rule.",
        "expected_next_command": "show access-lists 100 and show run | section line vty",
        "expected_fix": "MLS1(config)# ip access-list extended 100\nMLS1(config-ext-nacl)# 15 permit tcp 10.30.20.0 0.0.0.255 any eq 22\nMLS1(config-ext-nacl)# end"
    },
    {
        "case_id": "NETSAGE-011",
        "lab_source": "2020-05-02 WLC and RADIUS5.pkt",
        "symptom": "Security audit failure: Guest Wi-Fi devices (10.30.30.0/24) can access internal corporate database servers on 10.30.0.0/24.",
        "topology_note": "Guest clients associate with GuestWiFi WLAN on WLC. Traffic routed through MLS1.",
        "show_outputs": """Guest Device> ping 10.30.0.10
Reply from 10.30.0.10: bytes=32 time=5ms TTL=127

MLS1# show ip access-group
Interface Vlan30: Inbound access list is not set

MLS1# show run interface vlan 30
interface Vlan30
 description Guest WiFi Gateway
 ip address 10.30.30.1 255.255.255.0""",
        "expected_fault": "Missing Guest Isolation ACL on MLS1 SVI Vlan30 allowing unrestricted guest access to internal enterprise networks.",
        "osi_layer": "Layer 4 (Transport)",
        "concept_tag": "Wireless",
        "severity": "Critical",
        "deterministic_findings": "RULE_WARNING: Guest VLAN interface Vlan30 has no inbound ACL applied to restrict internal subnet access.",
        "expected_next_command": "show run interface vlan 30 and show access-lists",
        "expected_fix": "MLS1(config)# ip access-list extended GUEST_ISOLATION\nMLS1(config-ext-nacl)# permit udp any any eq domain\nMLS1(config-ext-nacl)# permit udp any any eq bootps\nMLS1(config-ext-nacl)# deny ip any 10.30.0.0 0.0.255.255\nMLS1(config-ext-nacl)# permit ip any any\nMLS1(config-ext-nacl)# exit\nMLS1(config)# interface vlan 30\nMLS1(config-if)# ip access-group GUEST_ISOLATION in\nMLS1(config-if)# end"
    },
    {
        "case_id": "NETSAGE-012",
        "lab_source": "2020-05-02 WLC and RADIUS5.pkt",
        "symptom": "Corporate Wireless clients fail 802.1X authentication when attempting to associate with CorpWiFi.",
        "topology_note": "WLC (10.30.0.2) authenticates wireless clients via RADIUS server on 10.30.0.10.",
        "show_outputs": """WLC CLI> show radius summary
Vendor ID........................................ 0
Radius Authentication Servers:
Server Index 1: IP: 10.30.0.10, Port: 1812, Status: Active

Server# show radius-server status
RADIUS Server: 10.30.0.10
Auth Port: 1812, Key: Cisco!23
Failed Access-Requests: 14 (Invalid Authenticator / Key Mismatch)""",
        "expected_fault": "RADIUS shared secret key mismatch configured between WLC and AAA/RADIUS Server.",
        "osi_layer": "Layer 7 (Application)",
        "concept_tag": "Wireless",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: RADIUS authentication failures logged on Server 10.30.0.10 due to key mismatch.",
        "expected_next_command": "show radius summary on WLC and check RADIUS client config on Server",
        "expected_fix": "Configure matching RADIUS shared secret key 'Cisco!23' on WLC WLAN Security settings for RADIUS Authentication Server."
    },
    {
        "case_id": "NETSAGE-013",
        "lab_source": "2020-05-16 AAA NTP For Learnersv3.pkt",
        "symptom": "MLS1 clock is not synchronizing with NTP server 10.30.0.10; show ntp status shows unsynchronized.",
        "topology_note": "NTP Server 10.30.0.10 requires authenticated NTP with Key 1 md5 Cisco!23.",
        "show_outputs": """MLS1# show ntp status
Clock is unsynchronized, stratum 16, no reference clock
nominal freq is 250.0000 Hz, actual freq is 250.0000 Hz, precision is 2**18

MLS1# show ntp associations
      address         ref clock     st   when     poll    reach  delay   offset    disp
 ~10.30.0.10          .INIT.        16      -       64        0  0.000    0.000 15937.5
 * master (synced), # master (unsynced), + selected, - candidate, ~ configured

MLS1# show run | include ntp
ntp server 10.30.0.10 key 1
ntp authenticate
ntp authentication-key 1 md5 WrongSecret!""",
        "expected_fault": "NTP authentication key secret mismatch on MLS1 (configured with 'WrongSecret!' instead of 'Cisco!23').",
        "osi_layer": "Layer 7 (Application)",
        "concept_tag": "NTP",
        "severity": "Low",
        "deterministic_findings": "RULE_WARNING: NTP status is unsynchronized (stratum 16); NTP authentication enabled with key mismatch.",
        "expected_next_command": "show ntp associations and show run | include ntp",
        "expected_fix": "MLS1(config)# ntp authentication-key 1 md5 Cisco!23\nMLS1(config)# ntp trusted-key 1\nMLS1(config)# end"
    },
    {
        "case_id": "NETSAGE-014",
        "lab_source": "2020-05-20 Routing  NTP and more WTW.pkt",
        "symptom": "Branch office PCs cannot access public internet IP addresses. Ping to router inside interface succeeds, but translation fails.",
        "topology_note": "Router R1 provides NAT/PAT for LAN subnet 192.168.1.0/24 to ISP on Gi0/1.",
        "show_outputs": """R1# show ip nat translations
% No active translations

R1# show ip nat statistics
Total active translations: 0 (0 static, 0 dynamic, 0 extended)
Outside interfaces: GigabitEthernet0/1
Inside interfaces: GigabitEthernet0/0
Hits: 0  Misses: 24

R1# show run | include ip nat
ip nat inside source list 1 interface GigabitEthernet0/1
access-list 1 permit 192.168.1.0 0.0.0.255""",
        "expected_fault": "Missing 'overload' keyword on 'ip nat inside source list' command, preventing Port Address Translation (PAT) for multiple hosts.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "NAT",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: Dynamic NAT configured without 'overload' keyword on single public IP interface.",
        "expected_next_command": "show ip nat statistics and show run | include nat",
        "expected_fix": "R1(config)# no ip nat inside source list 1 interface GigabitEthernet0/1\nR1(config)# ip nat inside source list 1 interface GigabitEthernet0/1 overload\nR1(config)# end"
    },
    {
        "case_id": "NETSAGE-015",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "R1 cannot ping Core1; link state is down on R1 side.",
        "topology_note": "R1 GigabitEthernet0/0 connects to Core1 GigabitEthernet1/0/3.",
        "show_outputs": """R1# show ip interface brief
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     10.16.6.5       YES manual administratively down down    
GigabitEthernet0/1     192.168.1.5     YES manual up                    up      
GigabitEthernet0/2     10.16.7.5       YES manual up                    up      

Core1# show ip interface brief
GigabitEthernet1/0/3   10.16.6.1       YES manual up                    down""",
        "expected_fault": "Interface GigabitEthernet0/0 on R1 is administratively down (shutdown).",
        "osi_layer": "Layer 1 (Physical)",
        "concept_tag": "Gateway",
        "severity": "Critical",
        "deterministic_findings": "RULE_ERROR: Interface R1:GigabitEthernet0/0 is administratively down (shutdown).",
        "expected_next_command": "show ip interface brief on R1",
        "expected_fix": "R1(config)# interface GigabitEthernet0/0\nR1(config-if)# no shutdown\nR1(config-if)# end"
    },
    {
        "case_id": "NETSAGE-016",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "High packet loss and late collisions observed between SW2 and R2.",
        "topology_note": "Link between SW2 FastEthernet0/1 and R2 GigabitEthernet0/1.",
        "show_outputs": """SW2# show interfaces FastEthernet0/1
FastEthernet0/1 is up, line protocol is up
  Half-duplex, 100Mb/s, media type is 100BaseTX
  342 late collision, 1294 collision, 0 CRC

R2# show interfaces GigabitEthernet0/1
GigabitEthernet0/1 is up, line protocol is up
  Full-duplex, 100Mb/s, media type is 100BaseTX
  0 late collision, 0 CRC""",
        "expected_fault": "Duplex mismatch: SW2 FastEthernet0/1 is forced to Half-duplex while R2 is set to Full-duplex.",
        "osi_layer": "Layer 2 (Data Link)",
        "concept_tag": "STP",
        "severity": "Medium",
        "deterministic_findings": "RULE_WARNING: Duplex mismatch detected on link SW2:Fa0/1 (Half) <-> R2:Gi0/1 (Full).",
        "expected_next_command": "show interfaces FastEthernet0/1 status",
        "expected_fix": "SW2(config)# interface FastEthernet0/1\nSW2(config-if)# duplex auto\nSW2(config-if)# speed auto\nSW2(config-if)# end"
    },
    {
        "case_id": "NETSAGE-017",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Newly connected desktop to Access SW port FastEthernet0/5 loses link immediately. Port LED turns amber.",
        "topology_note": "Access SW has Port Security configured on user ports.",
        "show_outputs": """Access SW# show interfaces FastEthernet0/5 status
Port      Name               Status       Vlan       Duplex  Speed Type
Fa0/5                        err-disabled 10           auto   auto 10/100BaseTX

Access SW# show port-security interface FastEthernet0/5
Port Security              : Enabled
Port Status                : Secure-shutdown
Violation Mode             : Shutdown
Aging Time                 : 0 mins
Max MAC Addresses          : 1
Total MAC Addresses        : 1
Configured MAC Addresses   : 1
Last Source Address:Vlan   : 0050.7966.6805:10
Security Violation Count   : 1""",
        "expected_fault": "Port security violation: Unauthorized MAC address connected to FastEthernet0/5 exceeding max MAC count (err-disabled).",
        "osi_layer": "Layer 2 (Data Link)",
        "concept_tag": "Security",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: Interface Access SW:Fa0/5 is in err-disabled state due to Port Security violation.",
        "expected_next_command": "show port-security interface FastEthernet0/5",
        "expected_fix": "Access SW(config)# interface FastEthernet0/5\nAccess SW(config-if)# shutdown\nAccess SW(config-if)# switchport port-security mac-address sticky\nAccess SW(config-if)# no shutdown\nAccess SW(config-if)# end"
    },
    {
        "case_id": "NETSAGE-018",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Spanning-tree topology instability; Access SW unexpectedly became the Root Bridge for VLAN 10.",
        "topology_note": "Core1, Core2, and Access SW participate in PVST+.",
        "show_outputs": """Access SW# show spanning-tree vlan 10
VLAN0010
  Spanning tree enabled protocol ieee
  Root ID    Priority    32778
             Address     0001.42a1.1101
             This bridge is the root

Core1# show spanning-tree vlan 10
VLAN0010
  Spanning tree enabled protocol ieee
  Root ID    Priority    32778
             Address     0001.42a1.1101
             Cost        4
  Bridge ID  Priority    32778 (priority 32768 sys-id-ext 10)
             Address     0005.5e59.7301""",
        "expected_fault": "STP Priority was left at default (32768) on all switches; Access SW won election due to lowest MAC address.",
        "osi_layer": "Layer 2 (Data Link)",
        "concept_tag": "STP",
        "severity": "Medium",
        "deterministic_findings": "RULE_WARNING: Core1/Core2 STP priority is default 32768; Root bridge is non-core switch Access SW.",
        "expected_next_command": "show spanning-tree vlan 10 on all switches",
        "expected_fix": "Core1(config)# spanning-tree vlan 10 root primary\nCore2(config)# spanning-tree vlan 10 root secondary\nCore1(config)# end"
    },
    {
        "case_id": "NETSAGE-019",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "PC1 has IP 10.16.0.50/24 but cannot ping its gateway or any remote host.",
        "topology_note": "PC1 is in subnet 10.16.0.0/24. True Gateway is Core1 (10.16.0.1).",
        "show_outputs": """PC1> ipconfig
IP Address: 10.16.0.50
Subnet Mask: 255.255.255.0
Default Gateway: 10.16.1.1

PC1> ping 10.16.1.1
Pinging 10.16.1.1 with 32 bytes of data:
Request timed out.

Core1# show ip interface brief | include Vlan10
Vlan10                 10.16.0.1       YES manual up                    up""",
        "expected_fault": "Gateway IP mismatch: PC1 default gateway configured as 10.16.1.1 instead of 10.16.0.1.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "Gateway",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: Host PC1 default gateway 10.16.1.1 is in a different subnet than host IP 10.16.0.50/24.",
        "expected_next_command": "ipconfig on PC1 and show ip interface brief on Gateway",
        "expected_fix": "Update PC1 configuration: set Default Gateway to 10.16.0.1."
    },
    {
        "case_id": "NETSAGE-020",
        "lab_source": "2020-06-18 OSPF.pkt",
        "symptom": "Traffic from Bob to Server2 is taking sub-optimal route across slow WAN link instead of fast local path.",
        "topology_note": "MLS1 can reach Server2 via R2 (Gigabit) or R3 (Serial/Backup).",
        "show_outputs": """MLS1# show ip route 10.16.16.0
Routing entry for 10.16.16.0/24
  Known via "ospf 1", distance 110, metric 550, type intra area
  Routing Descriptor Blocks:
  * 10.16.7.7, from 3.3.3.3, via GigabitEthernet1/0/3

MLS1# show ip ospf interface GigabitEthernet1/0/2
GigabitEthernet1/0/2 is up, line protocol is up
  Internet Address 10.16.7.1/28, Area 0
  Process ID 1, Router ID 1.1.1.1, Network Type BROADCAST, Cost: 500""",
        "expected_fault": "Sub-optimal routing caused by manually configured high OSPF cost ('ip ospf cost 500') on GigabitEthernet1/0/2.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "OSPF",
        "severity": "Medium",
        "deterministic_findings": "RULE_WARNING: High OSPF cost (500) manually set on high-speed interface Gi1/0/2 causing sub-optimal path selection.",
        "expected_next_command": "show ip ospf interface GigabitEthernet1/0/2",
        "expected_fix": "MLS1(config)# interface GigabitEthernet1/0/2\nMLS1(config-if)# no ip ospf cost\nMLS1(config-if)# end"
    },
    {
        "case_id": "NETSAGE-021",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "CDP native VLAN mismatch errors flooding switch console between SW2 and SW3.",
        "topology_note": "Trunk cable connecting SW2 Fa0/24 to SW3 Fa0/24.",
        "show_outputs": """SW2#
%CDP-4-NATIVE_VLAN_MISMATCH: Native VLAN mismatch discovered on FastEthernet0/24 (1), with SW3 FastEthernet0/24 (99).

SW2# show interfaces FastEthernet0/24 trunk
Port        Mode         Encapsulation  Status        Native vlan
Fa0/24      on           802.1q         trunking      1

SW3# show interfaces FastEthernet0/24 trunk
Port        Mode         Encapsulation  Status        Native vlan
Fa0/24      on           802.1q         trunking      99""",
        "expected_fault": "Native VLAN mismatch across 802.1Q trunk link (SW2 has Native VLAN 1, SW3 has Native VLAN 99).",
        "osi_layer": "Layer 2 (Data Link)",
        "concept_tag": "VLAN",
        "severity": "Medium",
        "deterministic_findings": "RULE_ERROR: Native VLAN mismatch on trunk link SW2:Fa0/24 (VLAN 1) <-> SW3:Fa0/24 (VLAN 99).",
        "expected_next_command": "show interfaces trunk on both switches",
        "expected_fix": "SW2(config)# interface FastEthernet0/24\nSW2(config-if)# switchport trunk native vlan 99\nSW2(config-if)# end"
    },
    {
        "case_id": "NETSAGE-022",
        "lab_source": "2020-05-20 Routing  NTP and more WTW.pkt",
        "symptom": "Branch router R1 cannot forward outbound packets; default route next-hop is unreachable.",
        "topology_note": "R1 default route points to ISP next-hop.",
        "show_outputs": """R1# show ip route static
S*    0.0.0.0/0 [1/0] via 192.168.1.254

R1# show ip interface brief GigabitEthernet0/1
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/1     192.168.1.5     YES manual up                    up

R1# show arp | include 192.168.1.254
% Incomplete ARP entry for 192.168.1.254""",
        "expected_fault": "Static default route configured with incorrect next-hop IP (192.168.1.254 instead of 192.168.1.1).",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "Routing",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: Static route next-hop 192.168.1.254 has incomplete ARP and is unresponsive.",
        "expected_next_command": "show ip route static and show arp",
        "expected_fix": "R1(config)# no ip route 0.0.0.0 0.0.0.0 192.168.1.254\nR1(config)# ip route 0.0.0.0 0.0.0.0 192.168.1.1\nR1(config)# end"
    },
    {
        "case_id": "NETSAGE-023",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Access-list applied to prevent external attacks is inadvertently blocking all outbound web traffic from internal hosts.",
        "topology_note": "Extended ACL 101 applied on router outside interface Gi0/1.",
        "show_outputs": """R1# show access-lists 101
Extended IP access list 101
    10 permit tcp any any established
    20 deny ip any any (452 matches)

R1# show run interface GigabitEthernet0/1
interface GigabitEthernet0/1
 ip address 192.168.1.5 255.255.255.0
 ip access-group 101 out""",
        "expected_fault": "ACL 101 was applied in the 'out' direction instead of 'in' on interface Gi0/1, blocking outbound client requests.",
        "osi_layer": "Layer 4 (Transport)",
        "concept_tag": "ACL",
        "severity": "Critical",
        "deterministic_findings": "RULE_ERROR: Directional ACL misapplication: Inbound filter applied as 'out' on interface GigabitEthernet0/1.",
        "expected_next_command": "show run interface GigabitEthernet0/1 and show access-lists 101",
        "expected_fix": "R1(config)# interface GigabitEthernet0/1\nR1(config-if)# no ip access-group 101 out\nR1(config-if)# ip access-group 101 in\nR1(config-if)# end"
    },
    {
        "case_id": "NETSAGE-024",
        "lab_source": "2020-05-16 AAA NTP For Learnersv3.pkt",
        "symptom": "DHCP clients receive IP address and DNS, but cannot reach internet or gateway.",
        "topology_note": "MLS1 runs local DHCP pool for LAN clients.",
        "show_outputs": """PC1> ipconfig
IP Address: 10.30.10.25
Subnet Mask: 255.255.255.0
Default Gateway: 10.30.10.254

MLS1# show run | section ip dhcp pool
ip dhcp pool LAN_POOL
 network 10.30.10.0 255.255.255.0
 default-router 10.30.10.254
 dns-server 10.30.0.10

MLS1# show ip interface brief | include Vlan10
Vlan10                 10.30.10.1      YES manual up                    up""",
        "expected_fault": "DHCP pool option 'default-router' configured with wrong IP (10.30.10.254 instead of router SVI IP 10.30.10.1).",
        "osi_layer": "Layer 7 (Application) / Layer 3 (Network)",
        "concept_tag": "DHCP",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: DHCP pool 'LAN_POOL' default-router 10.30.10.254 does not match SVI Vlan10 IP 10.30.10.1.",
        "expected_next_command": "show run | section ip dhcp pool",
        "expected_fix": "MLS1(config)# ip dhcp pool LAN_POOL\nMLS1(dhcp-config)# default-router 10.30.10.1\nMLS1(dhcp-config)# end"
    },
    {
        "case_id": "NETSAGE-025",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Network administrator cannot Telnet or SSH to SW2 management IP; connection is immediately closed.",
        "topology_note": "SW2 is an Access Switch in management subnet 192.168.1.0/24.",
        "show_outputs": """Admin_PC> telnet 192.168.1.100
Trying 192.168.1.100 ...
% Connection closed by foreign host.

SW2# show run | section line vty
line vty 0 4
 transport input all
! (missing password / login / login local)""",
        "expected_fault": "VTY lines missing 'login' / 'login local' or password configuration on SW2, causing Cisco IOS to reject unauthenticated remote connections.",
        "osi_layer": "Layer 7 (Application)",
        "concept_tag": "Management",
        "severity": "Medium",
        "deterministic_findings": "RULE_WARNING: VTY lines 0-4 on SW2 have no login method or password configured.",
        "expected_next_command": "show run | section line vty",
        "expected_fix": "SW2(config)# line vty 0 4\nSW2(config-line)# login local\nSW2(config-line)# transport input ssh\nSW2(config-line)# end"
    },
    {
        "case_id": "NETSAGE-026",
        "lab_source": "2020-05-20 Routing  NTP and more WTW.pkt",
        "symptom": "Both Core1 and Core2 claim Active HSRP state, causing packet flapping and ARP table thrashing.",
        "topology_note": "Core1 and Core2 provide redundant first-hop routing for VLAN 10.",
        "show_outputs": """Core1# show standby brief
                     P indicates configured to preempt.
                     |
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Vl10        1    110 P Active  local           10.16.0.3       10.16.0.1

Core2# show standby brief
Interface   Grp  Pri P State   Active          Standby         Virtual IP
Vl10        1    100   Active  local           unknown         10.16.0.254""",
        "expected_fault": "HSRP Virtual IP mismatch in Group 1: Core1 configured with virtual IP 10.16.0.1, while Core2 configured with 10.16.0.254.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "Gateway",
        "severity": "Critical",
        "deterministic_findings": "RULE_ERROR: HSRP Group 1 Virtual IP mismatch: Core1 (10.16.0.1) vs Core2 (10.16.0.254).",
        "expected_next_command": "show standby brief on both core switches",
        "expected_fix": "Core2(config)# interface vlan 10\nCore2(config-if)# standby 1 ip 10.16.0.1\nCore2(config-if)# end"
    },
    {
        "case_id": "NETSAGE-027",
        "lab_source": "2020-05-20 Routing  NTP and more WTW.pkt",
        "symptom": "NAT translation fails for LAN clients on R1; 'show ip nat translations' remains empty.",
        "topology_note": "R1 acts as NAT gateway between LAN (Gi0/0) and WAN (Gi0/1).",
        "show_outputs": """R1# show ip nat statistics
Total active translations: 0
Outside interfaces: GigabitEthernet0/1
Inside interfaces: (none)

R1# show run interface GigabitEthernet0/0
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
! (Missing 'ip nat inside')""",
        "expected_fault": "Interface GigabitEthernet0/0 is missing 'ip nat inside' configuration.",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "NAT",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: Router R1 has no 'ip nat inside' interface defined.",
        "expected_next_command": "show ip nat statistics and show run interface GigabitEthernet0/0",
        "expected_fix": "R1(config)# interface GigabitEthernet0/0\nR1(config-if)# ip nat inside\nR1(config-if)# end"
    },
    {
        "case_id": "NETSAGE-028",
        "lab_source": "2020-05-02 WLC and RADIUS5.pkt",
        "symptom": "Access Point AP1 status on WLC shows 'Not Joined' (Registration Request Timeout).",
        "topology_note": "AP1 (10.30.40.10) discovers WLC (10.30.0.2) via Option 43 in DHCP.",
        "show_outputs": """WLC# show ap summary
Number of APs.................................... 0

AP1# show capwap client status
CAPWAP State: Discovery
Discovery Request sent to: 255.255.255.255
Discovery Response: None received

DHCP_Server# show run | section ip dhcp pool AP_POOL
ip dhcp pool AP_POOL
 network 10.30.40.0 255.255.255.0
 default-router 10.30.40.1
! (Missing Option 43 hex for WLC IP 10.30.0.2)""",
        "expected_fault": "DHCP Scope for Access Points missing Option 43 (or DNS 'cisco-capwap-controller') specifying WLC IP address 10.30.0.2.",
        "osi_layer": "Layer 7 (Application) / Layer 3 (Network)",
        "concept_tag": "Wireless",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: AP DHCP pool missing Option 43 WLC controller IP attribute.",
        "expected_next_command": "show capwap client status on AP and check DHCP pool on server",
        "expected_fix": "DHCP_Server(config)# ip dhcp pool AP_POOL\nDHCP_Server(dhcp-config)# option 43 hex f1040a1e0002\nDHCP_Server(dhcp-config)# end"
    },
    {
        "case_id": "NETSAGE-029",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Access switch port Fa0/10 was shut down automatically when a student connected an unmanaged switch.",
        "topology_note": "Access SW has BPDU Guard enabled on PortFast enabled ports.",
        "show_outputs": """Access SW# show interfaces FastEthernet0/10 status
Port      Name               Status       Vlan       Duplex  Speed Type
Fa0/10                       err-disabled 10           auto   auto 10/100BaseTX

Access SW# show log
%SPANTREE-2-BLOCK_BPDUGUARD: Received BPDU on port Fa0/10 with BPDU Guard enabled. Disabling port.""",
        "expected_fault": "BPDU Guard triggered on PortFast-enabled port Fa0/10 upon receiving BPDUs from unauthorized switch.",
        "osi_layer": "Layer 2 (Data Link)",
        "concept_tag": "STP",
        "severity": "Medium",
        "deterministic_findings": "RULE_WARNING: Port Fa0/10 err-disabled by Spanning Tree BPDU Guard.",
        "expected_next_command": "show spanning-tree summary and show interfaces status err-disabled",
        "expected_fix": "Disconnect rogue switch, then:\nAccess SW(config)# interface FastEthernet0/10\nAccess SW(config-if)# shutdown\nAccess SW(config-if)# no shutdown\nAccess SW(config-if)# end"
    },
    {
        "case_id": "NETSAGE-030",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Standard ACL 10 fails to permit host traffic from 192.168.1.0/24 subnet; all packets dropped.",
        "topology_note": "ACL 10 applied on router R1.",
        "show_outputs": """R1# show access-lists 10
Standard IP access list 10
    10 permit 192.168.1.0, wildcard bits 255.255.255.0 (0 matches)
    20 deny any (1420 matches)

R1# show run | include access-list 10
access-list 10 permit 192.168.1.0 255.255.255.0""",
        "expected_fault": "Wildcard mask inversion syntax error in ACL 10: configured with subnet mask '255.255.255.0' instead of wildcard mask '0.0.0.255'.",
        "osi_layer": "Layer 4 (Transport)",
        "concept_tag": "ACL",
        "severity": "High",
        "deterministic_findings": "RULE_ERROR: Inverted wildcard mask in ACL 10: '255.255.255.0' used instead of '0.0.0.255'.",
        "expected_next_command": "show access-lists 10",
        "expected_fix": "R1(config)# no access-list 10\nR1(config)# access-list 10 permit 192.168.1.0 0.0.0.255\nR1(config)# end"
    },
    {
        "case_id": "NETSAGE-031",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "Dynamic ARP Inspection (DAI) dropping valid ARP replies on trunk link between Access SW and Core1.",
        "topology_note": "DAI enabled globally on VLAN 10.",
        "show_outputs": """Access SW# show ip arp inspection vlan 10
Vlan 10: Enabled

Access SW# show ip arp inspection statistics vlan 10
 Vlan 10:
  Forwarded: 0
  Dropped: 254 (DHCP snooping permit/deny drops)

Access SW# show interfaces Fa0/1 switchport
Port Fa0/1 is Trunk port to Core1
ARP Inspection Trust: Disabled""",
        "expected_fault": "Uplink trunk port Fa0/1 is not configured as an ARP inspection trusted port ('ip arp inspection trust').",
        "osi_layer": "Layer 2 (Data Link)",
        "concept_tag": "Security",
        "severity": "High",
        "deterministic_findings": "RULE_WARNING: Trunk uplink port Fa0/1 has ARP inspection trust disabled, causing legitimate ARP drops.",
        "expected_next_command": "show ip arp inspection interfaces",
        "expected_fix": "Access SW(config)# interface FastEthernet0/1\nAccess SW(config-if)# ip arp inspection trust\nAccess SW(config-if)# end"
    },
    {
        "case_id": "NETSAGE-032",
        "lab_source": "Keith Lab 2020-07-17.pkt",
        "symptom": "IPv6 end device cannot route packets across router R1; neighbor discovery fails.",
        "topology_note": "R1 configured with IPv6 addresses on interfaces.",
        "show_outputs": """R1# show ipv6 interface brief
GigabitEthernet0/0     [up/up]
    FE80::1
    2001:DB8:10:16::1
GigabitEthernet0/1     [up/up]
    FE80::2
    2001:DB8:192:168::1

R1# show run | include ipv6 unicast-routing
% No matches found""",
        "expected_fault": "IPv6 unicast routing is disabled globally on Router R1 (missing 'ipv6 unicast-routing').",
        "osi_layer": "Layer 3 (Network)",
        "concept_tag": "Routing",
        "severity": "Medium",
        "deterministic_findings": "RULE_ERROR: Global IPv6 routing disabled on Router R1 ('ipv6 unicast-routing' missing).",
        "expected_next_command": "show ipv6 route and show run | include ipv6",
        "expected_fix": "R1(config)# ipv6 unicast-routing\nR1(config)# end"
    }
]

class CaseManager:
    def __init__(self, db_path: Optional[Path] = None, csv_path: Optional[Path] = None):
        root = Path(__file__).resolve().parent.parent
        self.db_path = db_path or (root / "data" / "netsage.db")
        self.csv_path = csv_path or (root / "data" / "cases.csv")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes SQLite database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                lab_source TEXT,
                symptom TEXT,
                topology_note TEXT,
                show_outputs TEXT,
                expected_fault TEXT,
                osi_layer TEXT,
                concept_tag TEXT,
                severity TEXT,
                deterministic_findings TEXT,
                expected_next_command TEXT,
                expected_fix TEXT
            )
        """)

        # Diagnoses & Reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diagnoses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                ai_root_cause TEXT,
                ai_confidence REAL,
                ai_confidence_level TEXT,
                ai_evidence TEXT,
                ai_next_command TEXT,
                ai_fix_steps TEXT,
                ai_osi_layer TEXT,
                ai_fault_type TEXT,
                review_status TEXT DEFAULT 'Pending',
                human_corrected_root_cause TEXT,
                human_corrected_fix TEXT,
                human_notes TEXT,
                reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(case_id) REFERENCES cases(case_id)
            )
        """)

        conn.commit()
        conn.close()

    def populate_initial_cases(self):
        """Populates cases into SQLite and writes CSV."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for c in CASES_DATA:
            cursor.execute("""
                INSERT OR REPLACE INTO cases (
                    case_id, lab_source, symptom, topology_note, show_outputs,
                    expected_fault, osi_layer, concept_tag, severity,
                    deterministic_findings, expected_next_command, expected_fix
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["case_id"], c["lab_source"], c["symptom"], c["topology_note"],
                c["show_outputs"], c["expected_fault"], c["osi_layer"], c["concept_tag"],
                c["severity"], c["deterministic_findings"], c["expected_next_command"], c["expected_fix"]
            ))

        conn.commit()
        conn.close()

        # Write to CSV
        self.export_to_csv()
        print(f"[+] Populated {len(CASES_DATA)} troubleshooting cases into SQLite and CSV.")

    def export_to_csv(self):
        """Exports all cases from SQLite to CSV."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY case_id")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(list(row))

    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Returns all cases as list of dicts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY case_id")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Returns a single case by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

if __name__ == "__main__":
    mgr = CaseManager()
    mgr.populate_initial_cases()
