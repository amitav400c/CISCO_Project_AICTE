import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Root path via Path
root = Path(__file__).resolve().parent.parent
sub_path = root / "Unpacket"
sys.path.append(str(sub_path))

from Decipher.pt_crypto import decrypt_pkt
from feature_extractor import PacketTracerFeatureExtractor

def extract_xml(input_files: Path, output_files: Path, extract_features: bool = True):
    """
    Decrypts Cisco Packet Tracer (.pkt) files to formatted XML and optionally
    extracts structured topology and device features.
    """
    output_files.mkdir(parents=True, exist_ok=True)
    extractor = PacketTracerFeatureExtractor()
    json_dir = root / "data" / "extracted_features"
    json_dir.mkdir(parents=True, exist_ok=True)

    extracted_results = []

    for ptf in input_files.glob("*.pkt"):
        print(f"Processing: {ptf.name}")

        try:
            with open(ptf, "rb") as f:
                data = f.read()
                xml_data = decrypt_pkt(data)

            root_elem = ET.fromstring(xml_data)
            tree = ET.ElementTree(root_elem)

            if hasattr(ET, "indent"):
                ET.indent(tree, space="  ")

            output_file = output_files / ptf.with_suffix(".xml").name
            tree.write(
                output_file,
                encoding="utf-8",
                xml_declaration=True
            )
            print(f"[+] Decrypted XML: {output_file.name}")

            if extract_features:
                out_json = json_dir / f"{ptf.stem}_features.json"
                features = extractor.extract_from_xml(output_file)
                extractor.export_features_to_json(output_file, out_json)
                extracted_results.append(features)
                print(f"[+] Extracted Topology & Features: {out_json.name} ({len(features['devices'])} devices, {len(features['topology_links'])} links)")

        except Exception as e:
            print(f"[-] Failed {ptf.name}: {e}")

    return extracted_results

if __name__ == "__main__":
    in_dir = root / "data" / "pkt_test_files" / "input"
    if not in_dir.exists():
        in_dir = root / "pkt_test_files" / "input"
    out_dir = root / "data" / "pkt_test_files" / "output"
    if not out_dir.exists() and (root / "pkt_test_files" / "output").exists():
        out_dir = root / "pkt_test_files" / "output"
    extract_xml(in_dir, out_dir)
