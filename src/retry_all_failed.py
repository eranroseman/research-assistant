#!/usr/bin/env python3
"""Retry all 11 failed papers with extended timeout."""

import requests
import time
import json
from pathlib import Path

failed_papers = [
    "/home/eranr/Zotero/storage/2UJKSRJP/Abdelnour Nocera et al. - 2023 - Human-Computer Interaction – INTERACT 2023 19th IFIP TC13 International Conference, York, UK, Augus.pdf",
    "/home/eranr/Zotero/storage/25K2R9P9/Baumeister and Montag - 2019 - Digital Phenotyping and Mobile Sensing New Developments in Psychoinformatics.pdf",
    "/home/eranr/Zotero/storage/GKENC8DW/Byonanebye et al. - 2021 - An interactive voice response software to improve the quality of life of people living with HIV in U.pdf",
    "/home/eranr/Zotero/storage/UTTF5S8I/Cradock et al. - 2024 - The Handbook of Health Behavior Change.pdf",
    "/home/eranr/Zotero/storage/J7TAK6MQ/Health behavior and health education by Karen Glanz.pdf",
    "/home/eranr/Zotero/storage/3TSJGWCP/Kurosu and Hashizume - 2023 - Human-Computer Interaction Thematic Area, HCI 2023, Held as Part of the 25th HCI International Conf.pdf",
    "/home/eranr/Zotero/storage/WUZZWBL5/McKenzie et al. - 2013 - Planning, implementing, and evaluating health promotion programs a primer.pdf",
    "/home/eranr/Zotero/storage/K83K7D5W/Rehg et al. - 2017 - Mobile Health Sensors, Analytic Methods, and Applications.pdf",
    "/home/eranr/Zotero/storage/6WL2F7EE/Rowling - 2010 - Theoretical foundations of health education and health promotion.pdf",
    "/home/eranr/Zotero/storage/HQUKLSNB/Virani et al. - 2021 - Heart Disease and Stroke Statistics—2021 Update A Report From the American Heart Association.pdf",
    "/home/eranr/Zotero/storage/J9DHX5TT/Xu et al. - 2019 - Lay health supporters aided by mobile text messaging to improve adherence, symptoms, and functioning.pdf",
]

output_dir = Path("retry_failed_extractions")
output_dir.mkdir(exist_ok=True)

print("=" * 70)
print("RETRYING 11 FAILED PAPERS")
print("=" * 70)

results = []

for i, pdf_path in enumerate(failed_papers, 1):
    pdf_name = Path(pdf_path).name[:60] + "..."
    print(f"\n[{i}/11] {pdf_name}")

    if not Path(pdf_path).exists():
        print("  ❌ File not found")
        results.append({"file": pdf_name, "status": "not_found"})
        continue

    size_mb = Path(pdf_path).stat().st_size / 1024 / 1024
    print(f"  Size: {size_mb:.1f} MB")

    # Use simpler extraction for large files
    if size_mb > 10:
        print("  Using header-only extraction for large file...")
        endpoint = "/api/processHeaderDocument"
        timeout = 300
    else:
        print("  Using full extraction...")
        endpoint = "/api/processFulltextDocument"
        timeout = 600

    start = time.time()

    try:
        with open(pdf_path, "rb") as f:
            response = requests.post(
                f"http://localhost:8070{endpoint}",
                files={"input": f},
                data={"consolidateHeader": "0"},  # No consolidation
                timeout=timeout,
            )

        elapsed = time.time() - start

        if response.status_code == 200:
            print(f"  ✅ SUCCESS in {elapsed:.1f}s")

            # Save output
            pdf_id = Path(pdf_path).parent.name
            output_file = output_dir / f"{pdf_id}.xml"
            output_file.write_text(response.text, encoding="utf-8")

            results.append(
                {
                    "file": pdf_name,
                    "status": "success",
                    "time": elapsed,
                    "size_mb": size_mb,
                    "method": endpoint,
                }
            )
        else:
            print(f"  ❌ HTTP {response.status_code} after {elapsed:.1f}s")
            results.append(
                {
                    "file": pdf_name,
                    "status": f"http_{response.status_code}",
                    "time": elapsed,
                    "size_mb": size_mb,
                }
            )

    except requests.Timeout:
        print(f"  ❌ Timeout after {timeout}s")
        results.append({"file": pdf_name, "status": "timeout", "timeout": timeout, "size_mb": size_mb})
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")
        results.append({"file": pdf_name, "status": "error", "error": str(e)[:200], "size_mb": size_mb})

# Save results
results_file = output_dir / "results.json"
with open(results_file, "w") as f:
    json.dump(results, f, indent=2)

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

success_count = sum(1 for r in results if r["status"] == "success")
failed_count = len(results) - success_count

print(f"✅ Successful: {success_count}/11")
print(f"❌ Failed: {failed_count}/11")

if success_count > 0:
    print("\nSuccessfully extracted:")
    for r in results:
        if r["status"] == "success":
            print(f"  • {r['file'][:50]}... ({r['time']:.1f}s)")

if failed_count > 0:
    print("\nStill failed:")
    for r in results:
        if r["status"] != "success":
            print(f"  • {r['file'][:50]}... ({r['status']})")

print(f"\nResults saved to: {results_file}")
print(f"XML outputs in: {output_dir}/")
