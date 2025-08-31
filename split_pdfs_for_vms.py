#!/usr/bin/env python3
"""Split Zotero PDFs into chunks for parallel VM processing"""

import json
from pathlib import Path
import sys


def split_zotero_pdfs(num_vms=4):
    """Split Zotero PDFs into chunks for parallel processing"""
    # Find all PDFs
    zotero_path = Path.home() / "Zotero" / "storage"

    if not zotero_path.exists():
        print(f"Error: Zotero storage not found at {zotero_path}")
        return None

    pdf_files = sorted(list(zotero_path.glob("*/*.pdf")))
    total_pdfs = len(pdf_files)

    print(f"Found {total_pdfs} PDFs in Zotero library")
    print(f"Splitting into {num_vms} chunks for parallel processing")
    print("-" * 50)

    # Calculate chunk sizes
    base_chunk_size = total_pdfs // num_vms
    remainder = total_pdfs % num_vms

    chunks = []
    start_idx = 0

    for i in range(num_vms):
        # Distribute remainder PDFs across first VMs
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        end_idx = start_idx + chunk_size

        chunk = pdf_files[start_idx:end_idx]
        chunks.append(chunk)

        # Save chunk list to file
        chunk_file = f"vm_{i + 1}_pdfs.txt"
        with open(chunk_file, "w") as f:
            for pdf in chunk:
                f.write(str(pdf) + "\n")

        print(f"VM {i + 1}: {len(chunk):4d} PDFs -> {chunk_file}")

        # Save JSON version for more details
        chunk_json = f"vm_{i + 1}_pdfs.json"
        with open(chunk_json, "w") as f:
            json.dump(
                {
                    "vm_id": i + 1,
                    "total_pdfs": len(chunk),
                    "pdf_files": [str(p) for p in chunk],
                    "estimated_hours": len(chunk) * 18 / 3600,
                },
                f,
                indent=2,
            )

        start_idx = end_idx

    # Create summary
    summary = {
        "total_pdfs": total_pdfs,
        "num_vms": num_vms,
        "chunks": [len(c) for c in chunks],
        "estimated_time": {
            "sequential_hours": total_pdfs * 18 / 3600,
            "parallel_hours": max(len(c) for c in chunks) * 18 / 3600,
        },
    }

    with open("extraction_plan.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("-" * 50)
    print(f"Sequential processing: {summary['estimated_time']['sequential_hours']:.1f} hours")
    print(f"Parallel processing:   {summary['estimated_time']['parallel_hours']:.1f} hours")
    print(
        f"Speed-up:             {summary['estimated_time']['sequential_hours'] / summary['estimated_time']['parallel_hours']:.1f}x"
    )

    return chunks


def create_extraction_package():
    """Create a package with all necessary files for VM deployment"""
    package_dir = Path("grobid_vm_package")
    package_dir.mkdir(exist_ok=True)

    # Files to include
    files_to_copy = ["extract_zotero_library_vm.py", "extraction_plan.json"]

    # Add VM PDF lists
    for vm_file in Path(".").glob("vm_*_pdfs.*"):
        files_to_copy.append(str(vm_file))

    print("\nCreating deployment package...")
    for file in files_to_copy:
        if Path(file).exists():
            # Copy file to package
            import shutil

            shutil.copy(file, package_dir)
            print(f"  Added: {file}")

    print(f"\nPackage created in: {package_dir}")
    print("Ready for VM deployment!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        num_vms = int(sys.argv[1])
    else:
        num_vms = 4

    chunks = split_zotero_pdfs(num_vms)

    if chunks:
        create_extraction_package()
