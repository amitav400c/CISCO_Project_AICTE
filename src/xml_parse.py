import xml.etree.ElementTree as ET
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

# Folder containing the original XML files
XML_FOLDER = Path(__file__).parent.parent / "pkt_test_files" / "output"

# Folder where extracted feature XML files will be saved
FEATURES_FOLDER = (
    Path(__file__).parent.parent
    / "pkt_test_files"
    / "Useful_features"
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

            # IP address
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

    # Keep track of elements inside PORT
    port_elements = set()

    for port in device.iter():

        if get_tag(port) == "PORT":

            for item in port.iter():
                port_elements.add(id(item))

    # Extract configuration
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

    # Parse original XML
    tree = ET.parse(xml_file)
    root = tree.getroot()

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

            # Extract leaf values
            for item in element.iter():

                if len(item) == 0 and item.text:

                    tag = get_tag(item)
                    value = clean_text(item.text)

                    if value:
                        connection[tag] = value

            if connection:
                result["topology"].append(connection)

    return result


# ============================================================
# CONVERT EXTRACTED DATA TO XML
# ============================================================

def add_dict_to_xml(parent, data):

    """
    Convert a Python dictionary/list structure
    into XML elements.
    """

    if isinstance(data, dict):

        for key, value in data.items():

            # Make sure the XML tag is valid
            safe_key = str(key).replace(" ", "_")

            element = ET.SubElement(parent, safe_key)

            if isinstance(value, (dict, list)):

                add_dict_to_xml(element, value)

            else:

                element.text = str(value)

    elif isinstance(data, list):

        for item in data:

            item_element = ET.SubElement(parent, "item")

            if isinstance(item, (dict, list)):

                add_dict_to_xml(item_element, item)

            else:

                item_element.text = str(item)


# ============================================================
# SAVE ONE FEATURE XML FILE
# ============================================================

def save_features_xml(data, original_file):

    # Make sure Useful_features folder exists
    FEATURES_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    # Remove .xml from original filename
    output_name = (
        original_file.stem
        + "_features.xml"
    )

    output_file = FEATURES_FOLDER / output_name

    # Root element
    root = ET.Element("extracted_features")

    # Add extracted information
    add_dict_to_xml(root, data)

    # Create XML tree
    tree = ET.ElementTree(root)

    # Pretty formatting where supported
    try:
        ET.indent(tree, space="    ")
    except AttributeError:
        pass

    # Save XML
    tree.write(
        output_file,
        encoding="utf-8",
        xml_declaration=True
    )

    return output_file


# ============================================================
# MAIN
# ============================================================

def main():

    # Find all XML files
    xml_files = list(
        XML_FOLDER.glob("*.xml")
    )

    print(
        f"Found {len(xml_files)} XML files."
    )

    if not xml_files:

        print(
            f"No XML files found in: {XML_FOLDER}"
        )

        return

    successful = 0

    # ========================================================
    # PROCESS EACH XML FILE
    # ========================================================

    for xml_file in xml_files:

        try:

            # Extract useful information
            data = extract_xml(xml_file)

            print(
                f"    Devices found: "
                f"{len(data['devices'])}"
            )

            print(
                f"    Topology entries: "
                f"{len(data['topology'])}"
            )

            # Save individual feature XML
            output_file = save_features_xml(
                data,
                xml_file
            )

            print(
                f"    Saved to: {output_file}"
            )

            successful += 1

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
        f"Successfully created "
        f"{successful} feature XML files."
    )
    print(
        f"Output folder: {FEATURES_FOLDER}"
    )
    print("--------------------------------")


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()