import sys
from pathlib import Path
import xml.etree.ElementTree as ET

#Root path via Path
root = Path(__file__).resolve().parent.parent
sub_path = root / "Unpacket"
#Add recurive path import for the files inside sub_path
sys.path.append(str(sub_path))

from Decipher.pt_crypto import decrypt_pkt
def extract_xml(input_files: Path, output_files: Path):
    output_files.mkdir(parents=True, exist_ok=True)
    for ptf in input_files.glob("*.pkt"):
        print(f"Processing: {ptf}")

        try :
            with open(ptf, "rb") as f:
                data = f.read()
                xml_data = decrypt_pkt(data)

            root = ET.fromstring(xml_data)
            tree = ET.ElementTree(root)

            if hasattr(ET, "indent"):
                ET.indent(tree, space="  ")
                # test.pkt -> test.xml
                output_file = output_files / ptf.with_suffix(".xml").name
                tree.write(
                    output_file,
                    encoding="utf-8",
                    xml_declaration=True
                )
                print(f"[+] Created {output_file.name}")
        except Exception as e:
            print(f"[-] Failed: {ptf.name}: {e}")
