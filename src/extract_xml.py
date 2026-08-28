import sys
from pathlib import Path
import xml.etree.ElementTree as ET

#Root path via Path
root = Path(__file__).resolve().parent.parent
sub_path = root / "Unpacket"
#Add recurive path import for the files inside sub_path
sys.path.insert(0, str(sub_path))


def extract_xml(input_files: Path, output_files: Path) -> None:
	from Decipher.pt_crypto import decrypt_pkt

	output_files.mkdir(parents=True, exist_ok=True)
	for packet_file in input_files.glob("*.pkt"):
		print(f"Processing: {packet_file}")

		try:
			with packet_file.open("rb") as file:
				xml_data = decrypt_pkt(file.read())

			xml_root = ET.fromstring(xml_data)
			tree = ET.ElementTree(xml_root)
			if hasattr(ET, "indent"):
				ET.indent(tree, space="  ")

			output_file = output_files / packet_file.with_suffix(".xml").name
			tree.write(output_file, encoding="utf-8", xml_declaration=True)
			print(f"[+] Created {output_file.name}")
		except Exception as error:
			print(f"[-] Failed: {packet_file.name}: {error}")