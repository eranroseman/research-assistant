#!/bin/bash
# Setup VMs with local storage approach since Azure File Share creation is blocked
# This will copy PDFs directly to each VM instead of using shared storage

set -e

RESOURCE_GROUP="grobid-fileshare-rg"

echo "=========================================="
echo "SETTING UP VMS WITH LOCAL STORAGE"
echo "=========================================="
echo "Working with 2 VMs (processing will take ~5.5 hours)"
echo "=========================================="

# Get VM IPs
VM1_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-1 --query publicIps -o tsv)
VM3_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-3 --query publicIps -o tsv)

echo "VM 1: $VM1_IP"
echo "VM 3: $VM3_IP"

# Add to known hosts
ssh-keyscan -H $VM1_IP >> ~/.ssh/known_hosts 2>/dev/null
ssh-keyscan -H $VM3_IP >> ~/.ssh/known_hosts 2>/dev/null

# Step 1: Create VM setup script
echo ""
echo "Step 1: Creating setup script for VMs..."
cat > vm_setup.sh << 'SETUP'
#!/bin/bash
set -e

echo "[$(date)] Starting VM setup..."

# Install Docker
echo "Installing Docker..."
sudo apt-get update
curl -fsSL https://get.docker.com | sudo sh

# Install required packages
echo "Installing packages..."
sudo apt-get install -y python3-pip
pip3 install requests tqdm

# Pull Grobid (17GB)
echo "[$(date)] Pulling Grobid Docker image (17GB)..."
sudo docker pull lfoppiano/grobid:0.8.2-full

# Start Grobid
echo "[$(date)] Starting Grobid..."
sudo docker run -d --name grobid \
  -p 8070:8070 \
  --memory="6g" \
  --memory-swap="6g" \
  --restart unless-stopped \
  lfoppiano/grobid:0.8.2-full

# Create directory for PDFs
mkdir -p ~/pdfs

echo "[$(date)] VM setup complete!"
SETUP

# Step 2: Setup both VMs in parallel
echo ""
echo "Step 2: Setting up VMs with Docker and Grobid..."
for VM_IP in $VM1_IP $VM3_IP; do
    echo "Setting up VM at $VM_IP..."
    scp vm_setup.sh azureuser@$VM_IP:~/
    ssh azureuser@$VM_IP "chmod +x vm_setup.sh && nohup ./vm_setup.sh > setup.log 2>&1 &" &
done

# Step 3: Split PDFs for each VM
echo ""
echo "Step 3: Preparing PDFs for distribution..."
cat > split_pdfs_local.py << 'SPLIT'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import shutil

# Find all PDFs in Zotero
zotero_path = Path.home() / "Zotero" / "storage"
pdf_files = sorted(list(zotero_path.glob("*/*.pdf")))
print(f"Found {len(pdf_files)} PDFs to process")

# Create directories for each VM
os.makedirs("vm1_pdfs", exist_ok=True)
os.makedirs("vm3_pdfs", exist_ok=True)  # VM2 doesn't exist

# Split PDFs between 2 VMs
for i, pdf_path in enumerate(pdf_files):
    if i % 2 == 0:
        # VM1 gets even indices
        dest_dir = "vm1_pdfs"
    else:
        # VM3 gets odd indices
        dest_dir = "vm3_pdfs"

    # Maintain directory structure
    relative_path = pdf_path.relative_to(zotero_path)
    dest_path = Path(dest_dir) / relative_path
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(pdf_path, dest_path)

vm1_count = len(list(Path("vm1_pdfs").glob("*/*.pdf")))
vm3_count = len(list(Path("vm3_pdfs").glob("*/*.pdf")))
print(f"VM1: {vm1_count} PDFs")
print(f"VM3: {vm3_count} PDFs")
SPLIT

python3 split_pdfs_local.py

# Step 4: Create extraction script for VMs
echo ""
echo "Step 4: Creating extraction script..."
cat > extract_local.py << 'EXTRACT'
#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

class GrobidExtractor:
    def __init__(self, vm_id):
        self.vm_id = vm_id
        self.grobid_url = "http://localhost:8070"
        self.output_dir = Path(f"extraction_vm_{vm_id}")
        self.output_dir.mkdir(exist_ok=True)

        # Checkpoint file
        self.checkpoint_file = self.output_dir / "checkpoint.json"
        self.processed_files = self.load_checkpoint()

        # Log file
        self.log_file = self.output_dir / f"extraction_vm_{vm_id}.log"

    def load_checkpoint(self):
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return set(json.load(f))
        return set()

    def save_checkpoint(self):
        with open(self.checkpoint_file, 'w') as f:
            json.dump(list(self.processed_files), f)

    def log(self, message):
        timestamp = datetime.now().isoformat()
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + '\n')

    def wait_for_grobid(self):
        """Wait for Grobid to be ready"""
        self.log("Waiting for Grobid to be ready...")
        max_attempts = 60
        for i in range(max_attempts):
            try:
                response = requests.get(f"{self.grobid_url}/api/isalive")
                if response.status_code == 200:
                    self.log("Grobid is ready!")
                    return True
            except:
                pass
            time.sleep(5)
        return False

    def extract_pdf(self, pdf_path):
        """Extract all data from PDF using Grobid"""
        pdf_name = pdf_path.name
        output_base = self.output_dir / pdf_path.parent.name / pdf_path.stem
        output_base.parent.mkdir(parents=True, exist_ok=True)

        # Skip if already processed
        if str(pdf_path) in self.processed_files:
            return True

        try:
            with open(pdf_path, 'rb') as f:
                files = {'input': (pdf_name, f, 'application/pdf')}

                # Full text extraction with all options
                params = {
                    'consolidateHeader': '2',
                    'consolidateCitations': '2',
                    'consolidateFunders': '1',
                    'processFigures': '1',
                    'processTables': '1',
                    'processEquations': '1',
                    'segmentSentences': '1',
                    'includeRawCitations': '1',
                    'includeRawAffiliations': '1',
                    'teiCoordinates': 'all'
                }

                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files=files,
                    data=params,
                    timeout=120
                )

                if response.status_code == 200:
                    # Save TEI XML
                    with open(f"{output_base}_full.xml", 'w') as out:
                        out.write(response.text)

                    # Mark as processed
                    self.processed_files.add(str(pdf_path))

                    # Save checkpoint every 10 files
                    if len(self.processed_files) % 10 == 0:
                        self.save_checkpoint()

                    return True
                else:
                    self.log(f"Failed to process {pdf_name}: {response.status_code}")
                    return False

        except Exception as e:
            self.log(f"Error processing {pdf_name}: {e}")
            return False

    def run(self):
        """Main extraction loop"""
        if not self.wait_for_grobid():
            self.log("Grobid failed to start!")
            return

        # Find all PDFs
        pdf_dir = Path.home() / "pdfs"
        pdf_files = sorted(list(pdf_dir.glob("*/*.pdf")))

        self.log(f"Found {len(pdf_files)} PDFs to process")
        self.log(f"Already processed: {len(self.processed_files)}")

        # Process PDFs
        failed = []
        for pdf_path in tqdm(pdf_files, desc=f"VM {self.vm_id}"):
            if not self.extract_pdf(pdf_path):
                failed.append(pdf_path)

        # Final checkpoint
        self.save_checkpoint()

        # Report results
        self.log(f"Extraction complete!")
        self.log(f"Processed: {len(self.processed_files)}")
        self.log(f"Failed: {len(failed)}")

        if failed:
            self.log("Failed files:")
            for f in failed:
                self.log(f"  - {f}")

if __name__ == "__main__":
    vm_id = sys.argv[1] if len(sys.argv) > 1 else "1"
    extractor = GrobidExtractor(vm_id)
    extractor.run()
EXTRACT

# Step 5: Wait for VMs to be ready
echo ""
echo "Step 5: Waiting for VMs to complete setup (10-15 minutes)..."
echo "This includes pulling the 17GB Grobid Docker image..."
sleep 300  # Wait 5 minutes minimum

# Check if Grobid is running
for VM_IP in $VM1_IP $VM3_IP; do
    echo "Checking VM at $VM_IP..."
    while ! ssh azureuser@$VM_IP "sudo docker ps | grep grobid" &>/dev/null; do
        echo "  Still setting up..."
        sleep 30
    done
    echo "  ✓ Grobid is running!"
done

# Step 6: Copy PDFs to VMs
echo ""
echo "Step 6: Copying PDFs to VMs (this will take several minutes)..."

echo "Copying to VM1 ($VM1_IP)..."
scp -r vm1_pdfs/* azureuser@$VM1_IP:~/pdfs/ &
VM1_COPY=$!

echo "Copying to VM3 ($VM3_IP)..."
scp -r vm3_pdfs/* azureuser@$VM3_IP:~/pdfs/ &
VM3_COPY=$!

# Wait for copies to complete
wait $VM1_COPY
echo "✓ VM1 copy complete"
wait $VM3_COPY
echo "✓ VM3 copy complete"

# Step 7: Copy extraction script and start extraction
echo ""
echo "Step 7: Starting extraction on VMs..."

scp extract_local.py azureuser@$VM1_IP:~/
ssh azureuser@$VM1_IP "nohup python3 extract_local.py 1 > extraction.log 2>&1 &"
echo "✓ VM1 extraction started"

scp extract_local.py azureuser@$VM3_IP:~/
ssh azureuser@$VM3_IP "nohup python3 extract_local.py 3 > extraction.log 2>&1 &"
echo "✓ VM3 extraction started"

echo ""
echo "=========================================="
echo "SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Working with 2 VMs:"
echo "  VM1: $VM1_IP (processing ~1,110 PDFs)"
echo "  VM3: $VM3_IP (processing ~1,111 PDFs)"
echo ""
echo "Expected completion: ~5.5 hours"
echo ""
echo "To monitor progress:"
echo "  ssh azureuser@$VM1_IP 'tail -f extraction.log'"
echo "  ssh azureuser@$VM3_IP 'tail -f extraction.log'"
echo ""
echo "To collect results when done:"
echo "  ./collect_azure_results.sh"
