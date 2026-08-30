"""
NetSage AI - Topology Builder
Reconstructs the network topology graph from extracted Packet Tracer data,
utilizing save-ref-id mappings, device types, and link endpoints.
"""

from typing import Dict, List, Any, Optional
import networkx as nx

class TopologyBuilder:
    def __init__(self):
        pass

    def build_graph_from_scenario(self, scenario_data: Dict[str, Any]) -> nx.Graph:
        """
        Creates a NetworkX Graph representing the network topology.
        """
        G = nx.Graph()

        # Add nodes with metadata
        for dev in scenario_data.get("devices", []):
            name = dev["name"]
            dev_type = dev.get("type", "Unknown")
            save_ref_id = dev.get("save_ref_id", "")
            
            # Count configured IPs
            ips = []
            for p in dev.get("ports", []):
                if p.get("ip_address"):
                    ips.append(f"{p['name']}:{p['ip_address']}")

            G.add_node(
                name,
                device_type=dev_type,
                save_ref_id=save_ref_id,
                model=dev.get("model", ""),
                ips=ips,
                vlans=[v["id"] for v in dev.get("vlans", [])]
            )

        # Add edges with interface labels
        for link in scenario_data.get("topology_links", []):
            u = link.get("from_device")
            v = link.get("to_device")
            if u and v:
                G.add_edge(
                    u,
                    v,
                    cable_type=link.get("cable_type", "Copper"),
                    from_port=link.get("from_port", ""),
                    to_port=link.get("to_port", ""),
                    from_ref=link.get("from_ref", ""),
                    to_ref=link.get("to_ref", "")
                )

        return G

    def get_topology_elements_for_vis(self, scenario_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generates nodes and edges JSON suitable for vis.js / Streamlit custom components.
        """
        nodes = []
        edges = []

        type_color_map = {
            "Router": "#2563eb",             # Blue
            "MultiLayerSwitch": "#7c3aed",   # Purple
            "Switch": "#059669",             # Green
            "Server": "#dc2626",             # Red
            "Pc": "#d97706",                 # Amber
            "Pda": "#ea580c",                # Orange
            "WirelessLanController": "#0891b2",# Cyan
            "LightWeightAccessPoint": "#4f46e5",# Indigo
            "Power Distribution Device": "#6b7280" # Gray
        }

        for dev in scenario_data.get("devices", []):
            name = dev["name"]
            dev_type = dev.get("type", "Unknown")
            color = type_color_map.get(dev_type, "#4b5563")

            ips = [f"{p['name']}: {p['ip_address']}" for p in dev.get("ports", []) if p.get("ip_address")]
            ip_str = "\n".join(ips) if ips else "No IP"

            nodes.append({
                "id": name,
                "label": f"{name}\n({dev_type})",
                "title": f"<b>{name}</b><br>Type: {dev_type}<br>Ref ID: {dev.get('save_ref_id', 'N/A')}<br>IPs:<br>{ip_str}",
                "color": color,
                "shape": "box" if "Switch" in dev_type or "Router" in dev_type else "ellipse"
            })

        for link in scenario_data.get("topology_links", []):
            edges.append({
                "from": link.get("from_device"),
                "to": link.get("to_device"),
                "label": f"{link.get('from_port')} - {link.get('to_port')}",
                "title": f"{link.get('cable_type')}: {link.get('from_device')}:{link.get('from_port')} -> {link.get('to_device')}:{link.get('to_port')}",
                "color": "#9ca3af"
            })

        return {"nodes": nodes, "edges": edges}
