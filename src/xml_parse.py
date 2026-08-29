import xml.etree.ElementTree as ET
from pathlib import Path
import json


# ============================================================
# PATHS
# ============================================================

# Folder containing XML files
XML_FOLDER = Path(__file__).parent.parent / "pkt_test_files" / "output"

# Folder where individual extracted feature files will be saved
FEATURES_FOLDER = (
    Path(__file__).parent.parent
    / "pkt_test_files"
    / "useful_features"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(text):
    """Clean XML text safely."""
    if text is None:
        return ""

    return text.strip()


def get_tag(element):
    """
    Return the XML tag in uppercase.

    Also handles XML namespaces if they exist.
    """
    tag = element.tag

    if "}" in tag:
        tag = tag.split("}", 1)[1]

    return tag.upper()


# ============================================================
# EXTRACT ONE DEVICE
# ============================================================

def extract_device(device):

    data = {
        "device_name": "",
        "device_type": "",
        "interfaces": [],
        "configuration": {}
    }

    # --------------------------------------------------------
    # DEVICE NAME AND DEVICE TYPE
    # --------------------------------------------------------

    engine = None

    for child in device:
        if get_tag(child) == "ENGINE":
            engine = child
            break

    if engine is not None:

        for child in engine:

            tag = get_tag(child)

            if tag in ["NAME", "DEVICE_NAME"]:
                data["device_name"] = clean_text(child.text)

            elif tag in ["TYPE", "DEVICE_TYPE"]:
                data["device_type"] = clean_text(child.text)

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if not data["device_name"] or not data["device_type"]:

        for child in device:

            tag = get_tag(child)

            if tag in ["NAME", "DEVICE_NAME"]:
                if not data["device_name"]:
                    data["device_name"] = clean_text(child.text)

            elif tag in ["TYPE", "DEVICE_TYPE"]:
                if not data["device_type"]:
                    data["device_type"] = clean_text(child.text)

    # --------------------------------------------------------
    # INTERFACES / PORTS
    # --------------------------------------------------------

    for port in device.iter():

        if get_tag(port) != "PORT":
            continue

        interface = {}

        for item in port.iter():

            tag = get_tag(item)

            # Interface name
            if tag in [
                "NAME",
                "PORT_NAME",
                "INTERFACE",
                "INTERFACE_NAME"
            ]:

                value = clean_text(item.text)

                if value:
                    interface["name"] = value

            # IPv4 / IPv6 address
            elif tag in [
                "IP_ADDRESS",
                "IPV4_ADDRESS",
                "IPV6_ADDRESS",
                "IPADDRESS"
            ]:

                value = clean_text(item.text)

                if value:
                    interface["ip_address"] = value

            # MAC address
            elif tag in [
                "MAC_ADDRESS",
                "MAC",
                "MACADDRESS"
            ]:

                value = clean_text(item.text)

                if value:
                    interface["mac_address"] = value

            # Interface type
            elif tag in [
                "PORT_TYPE",
                "TYPE"
            ]:

                value = clean_text(item.text)

                if value:
                    interface["type"] = value

            # Port status
            elif tag in [
                "STATUS",
                "PORT_STATUS"
            ]:

                value = clean_text(item.text)

                if value:
                    interface["status"] = value

        # Add interface only if something was actually found
        if interface:
            data["interfaces"].append(interface)

    # --------------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------------

    configuration_keywords = [
        "CONFIG",
        "IP",
        "DHCP",
        "DNS",
        "GATEWAY",
        "ROUT",
        "OSPF",
        "BGP",
        "VLAN",
        "MASK",
        "FIREWALL",
        "SERVER",
        "DEFAULT",
        "DESCRIPTION",
        "AUTHENTICATE",
        "WIRELESS",
        "SSID",
        "HOST",
        "START",
        "END"
    ]

    # Keep track of XML elements belonging to PORTs.
    port_elements = set()

    for port in device.iter():

        if get_tag(port) == "PORT":

            for item in port.iter():
                port_elements.add(id(item))

    # Extract configuration values

    for item in device.iter():

        # Skip anything inside a PORT
        if id(item) in port_elements:
            continue

        tag = get_tag(item)

        # Skip structural/device identity tags
        if tag in [
            "DEVICE",
            "ENGINE",
            "MODULE",
            "SLOT",
            "PORT",
            "NAME",
            "TYPE",
            "DEVICE_NAME",
            "DEVICE_TYPE"
        ]:
            continue

        # Only process leaf elements
        if len(item) == 0 and item.text:

            value = clean_text(item.text)

            if not value:
                continue

            # Check whether this looks like configuration
            if any(
                word in tag
                for word in configuration_keywords
            ):

                data["configuration"][tag] = value

    return data


# ============================================================
# EXTRACT ONE XML FILE
# ============================================================

def extract_xml(xml_file):

    print(f"\nReading: {xml_file.name}")

    # Parse XML
    tree = ET.parse(xml_file)

    root = tree.getroot()

    # Result structure
    result = {
        "file": xml_file.name,
        "devices": [],
        "topology": []
    }

    # ========================================================
    # DEVICE EXTRACTION
    # ========================================================

    for element in root.iter():

        if get_tag(element) == "DEVICE":

            device_data = extract_device(element)

            result["devices"].append(device_data)

    # ========================================================
    # TOPOLOGY / CONNECTION EXTRACTION
    # ========================================================

    topology_tags = [
        "LINK",
        "CONNECTION",
        "CONNECT",
        "CABLE",
        "NETWORK_LINK",
        "EDGE"
    ]

    for element in root.iter():

        if get_tag(element) in topology_tags:

            connection = {}

            # Extract leaf values inside the connection
            for item in element.iter():

                if len(item) == 0 and item.text:

                    tag = get_tag(item)

                    value = clean_text(item.text)

                    if value:
                        connection[tag] = value

            # Only save non-empty connections
            if connection:
                result["topology"].append(connection)

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    # Create useful_features folder if it doesn't exist
    FEATURES_FOLDER.mkdir(parents=True, exist_ok=True)

    # Find all XML files
    xml_files = list(
        XML_FOLDER.glob("*.xml")
    )

    print(
        f"Found {len(xml_files)} XML files."
    )

    # ========================================================
    # PROCESS EACH XML FILE
    # ========================================================

    for xml_file in xml_files:

        try:

            data = extract_xml(xml_file)

            # ------------------------------------------------
            # Create one JSON file for EACH XML file
            # ------------------------------------------------

            output_name = xml_file.stem + "_features.json"

            output_file = FEATURES_FOLDER / output_name

            with open(
                output_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    data,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

            print(
                f"    Devices found: "
                f"{len(data['devices'])}"
            )

            print(
                f"    Topology entries: "
                f"{len(data['topology'])}"
            )

            print(
                f"    Saved features to: "
                f"{output_file}"
            )

        except Exception as error:

            print(
                f"ERROR reading "
                f"{xml_file.name}: {error}"
            )

    # ========================================================
    # FINISHED
    # ========================================================

    print("\n--------------------------------")
    print("Extraction completed!")
    print(
        f"Feature files saved in: {FEATURES_FOLDER}"
    )
    print("--------------------------------")


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()