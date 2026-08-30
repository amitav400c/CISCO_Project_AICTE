"""
NetSage AI - Cisco Packet Tracer Feature Extractor
Extracts XML features from decrypted .pkt files, including:
- Device Metadata & SAVE_REF_ID for every device
- Interface & Port Configuration (IP, Subnet, MAC, Admin Status, Link Status, Gateway, DNS, DHCP)
- Running and Startup Configurations (clean parsed lines)
- VLANs, VTP, STP, and Routing Configurations
- Full Physical & Logical Topology Links using save-ref-id resolution
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional

class PacketTracerFeatureExtractor:
    def __init__(self):
        pass

    def extract_from_xml(self, xml_path: Path) -> Dict[str, Any]:
        """
        Parses decrypted Packet Tracer XML and extracts all key features.
        """
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"XML file not found: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()

        version = root.findtext("VERSION", "Unknown")
        network = root.find("NETWORK")
        if network is None:
            raise ValueError("Invalid Packet Tracer XML: Missing <NETWORK> element")

        devices_elem = network.find("DEVICES")
        links_elem = network.find("LINKS")

        devices = []
        device_ref_map = {}  # save_ref_id -> device dict

        if devices_elem is not None:
            for dev_elem in devices_elem:
                engine = dev_elem.find("ENGINE")
                if engine is None:
                    continue

                dev_data = self._parse_device(engine)
                devices.append(dev_data)
                if dev_data["save_ref_id"]:
                    device_ref_map[dev_data["save_ref_id"]] = dev_data

        # Parse links using save_ref_id mapping
        links = []
        if links_elem is not None:
            for link_elem in links_elem:
                link_data = self._parse_link(link_elem, device_ref_map)
                if link_data:
                    links.append(link_data)

        # Build summary data
        scenario_data = {
            "scenario_name": xml_path.stem,
            "packet_tracer_version": version,
            "device_count": len(devices),
            "link_count": len(links),
            "devices": devices,
            "topology_links": links,
            "device_ref_map": {k: v["name"] for k, v in device_ref_map.items()}
        }

        return scenario_data

    def _parse_device(self, engine: ET.Element) -> Dict[str, Any]:
        """
        Extracts structured device information including save_ref_id, interfaces, configs.
        """
        save_ref_id = engine.findtext("SAVE_REF_ID", "").strip()
        dev_name = engine.findtext("NAME", "Unknown").strip()
        dev_type = engine.findtext("TYPE", "Unknown").strip()
        model = engine.findtext("MODEL", "").strip()
        sys_name = engine.findtext("SYS_NAME", "").strip()
        power = engine.findtext("POWER", "true").strip().lower() == "true"
        serial_number = engine.findtext("SERIALNUMBER", "").strip()

        # Parse Running Configuration
        running_config = []
        rc_elem = engine.find("RUNNINGCONFIG")
        if rc_elem is not None:
            for line in rc_elem.findall("LINE"):
                if line.text:
                    running_config.append(line.text.rstrip())

        # Parse Startup Configuration
        startup_config = []
        sc_elem = engine.find("STARTUPCONFIG")
        if sc_elem is not None:
            for line in sc_elem.findall("LINE"):
                if line.text:
                    startup_config.append(line.text.rstrip())

        # Parse VLANs
        vlans = []
        vlans_elem = engine.find("VLANS")
        if vlans_elem is not None:
            for vlan in vlans_elem:
                vid = vlan.findtext("ID", "").strip()
                vname = vlan.findtext("NAME", "").strip()
                if vid:
                    vlans.append({"id": vid, "name": vname})

        # Parse Ports / Interfaces
        ports = []
        for port_elem in engine.iter("PORT"):
            port_data = self._parse_port(port_elem)
            if port_data:
                ports.append(port_data)

        # Parse Console Outputs / History if present
        console_history = []
        for cmd_elem in engine.findall(".//CURRENT_COMMAND_SET/COMMAND"):
            if cmd_elem.text:
                console_history.append(cmd_elem.text.strip())

        return {
            "save_ref_id": save_ref_id,
            "name": dev_name,
            "type": dev_type,
            "model": model,
            "sys_name": sys_name,
            "power": power,
            "serial_number": serial_number,
            "ports": ports,
            "vlans": vlans,
            "running_config": running_config,
            "running_config_text": "\n".join(running_config),
            "startup_config": startup_config,
            "console_history": console_history
        }

    def _parse_port(self, port_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """
        Extracts individual port configuration.
        """
        port_type = port_elem.findtext("TYPE", "").strip()
        port_name = port_elem.findtext("NAME", "").strip()
        if not port_name:
            port_name = port_type

        ip = port_elem.findtext("IP", "").strip()
        subnet = port_elem.findtext("SUBNET", "").strip()
        mac = port_elem.findtext("MACADDRESS", "").strip()
        gateway = port_elem.findtext("PORT_GATEWAY", "").strip()
        dns = port_elem.findtext("PORT_DNS", "").strip()
        dhcp_enabled = port_elem.findtext("PORT_DHCP_ENABLE", "false").strip().lower() == "true"
        bandwidth = port_elem.findtext("BANDWIDTH", "").strip()
        full_duplex = port_elem.findtext("FULLDUPLEX", "true").strip().lower() == "true"
        description = port_elem.findtext("DESCRIPTION", "").strip()
        up_method = port_elem.findtext("UP_METHOD", "").strip()

        # Check interface sub-element if present
        admin_down = False
        link_status = "Up"
        iface_elem = port_elem.find("INTERFACE")
        if iface_elem is not None:
            if iface_elem.findtext("IP_ADDRESS"):
                ip = iface_elem.findtext("IP_ADDRESS").strip()
            if iface_elem.findtext("SUBNET_MASK"):
                subnet = iface_elem.findtext("SUBNET_MASK").strip()
            if iface_elem.findtext("MAC_ADDRESS"):
                mac = iface_elem.findtext("MAC_ADDRESS").strip()
            admin_down = iface_elem.findtext("IS_ADMINISTRATIVELY_DOWN", "false").strip().lower() == "true"
            link_status = iface_elem.findtext("LINK_STATUS", "Up").strip()

        # If IP is present or it's a known port type
        return {
            "name": port_name,
            "type": port_type,
            "ip_address": ip,
            "subnet_mask": subnet,
            "mac_address": mac,
            "gateway": gateway,
            "dns": dns,
            "dhcp_enabled": dhcp_enabled,
            "bandwidth": bandwidth,
            "full_duplex": full_duplex,
            "description": description,
            "admin_down": admin_down,
            "link_status": link_status,
            "up_method": up_method
        }

    def _parse_link(self, link_elem: ET.Element, device_ref_map: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses a connection link and maps save_ref_id to device names.
        """
        link_type = link_elem.findtext("TYPE", "").strip()
        cable = link_elem.find("CABLE")
        if cable is None:
            return None

        from_ref = cable.findtext("FROM", "").strip()
        to_ref = cable.findtext("TO", "").strip()

        ports = cable.findall("PORT")
        from_port = ports[0].text.strip() if len(ports) > 0 and ports[0].text else "Unknown"
        to_port = ports[1].text.strip() if len(ports) > 1 and ports[1].text else "Unknown"

        from_device = device_ref_map.get(from_ref, {}).get("name", from_ref)
        to_device = device_ref_map.get(to_ref, {}).get("name", to_ref)
        from_type = device_ref_map.get(from_ref, {}).get("type", "Unknown")
        to_type = device_ref_map.get(to_ref, {}).get("type", "Unknown")

        from_mem = cable.findtext("FROM_DEVICE_MEM_ADDR", "").strip()
        to_mem = cable.findtext("TO_DEVICE_MEM_ADDR", "").strip()

        return {
            "cable_type": link_type,
            "from_ref": from_ref,
            "from_device": from_device,
            "from_device_type": from_type,
            "from_port": from_port,
            "to_ref": to_ref,
            "to_device": to_device,
            "to_device_type": to_type,
            "to_port": to_port,
            "from_mem_addr": from_mem,
            "to_mem_addr": to_mem
        }

    def export_features_to_json(self, xml_path: Path, output_json_path: Path) -> Path:
        """
        Extracts features and writes JSON to output_json_path.
        """
        features = self.extract_from_xml(xml_path)
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(features, f, indent=2)
        return output_json_path

    def batch_extract(self, xml_dir: Path, json_dir: Path) -> List[Dict[str, Any]]:
        """
        Extracts features for all XML files in a directory.
        """
        json_dir.mkdir(parents=True, exist_ok=True)
        all_features = []
        for xml_file in xml_dir.glob("*.xml"):
            out_file = json_dir / f"{xml_file.stem}_features.json"
            features = self.extract_from_xml(xml_file)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(features, f, indent=2)
            all_features.append(features)
            print(f"[+] Extracted features for {xml_file.name} -> {out_file.name}")
        return all_features


if __name__ == "__main__":
    extractor = PacketTracerFeatureExtractor()
    root = Path(__file__).resolve().parent.parent
    xml_dir = root / "data" / "pkt_test_files" / "output"
    if not xml_dir.exists():
        xml_dir = root / "pkt_test_files" / "output"
    json_dir = root / "data" / "extracted_features"
    extractor.batch_extract(xml_dir, json_dir)
