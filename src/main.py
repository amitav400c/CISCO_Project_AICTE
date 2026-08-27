from pathlib import Path
from extract_xml import extract_xml

def main():
    project_root = Path(__file__).resolve().parent.parent

    input_dir = project_root / "pkt_test_files" / "input"
    output_dir = project_root / "pkt_test_files" / "output"

    print(f"Input directory : {input_dir}")
    print(f"Output directory: {output_dir}")

    extract_xml(input_dir, output_dir)

if __name__ == "__main__":
    main()
