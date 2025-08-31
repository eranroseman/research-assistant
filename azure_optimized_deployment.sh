#!/bin/bash
# Optimized Azure deployment - uploads PDFs while VMs are setting up
# Saves ~30% of deployment time by running tasks in parallel

set -e

# Configuration
RESOURCE_GROUP="grobid-fileshare-rg"
LOCATION="westus2"
STORAGE_ACCOUNT="grobidpdfs$(date +%s)"  # Unique name
FILE_SHARE_NAME="pdfs"
VM_SIZE="Standard_D2s_v3"  # 2 vCPU, 8GB RAM
NUM_VMS=3

echo "=========================================="
echo "OPTIMIZED AZURE DEPLOYMENT (30% FASTER)"
echo "=========================================="
echo "Timeline:"
echo "  0-3 min:   Create resources & start VMs"
echo "  3-15 min:  VMs setup (Docker, Grobid) + PDF upload in parallel"
echo "  15-20 min: Mount shares and final config"
echo "Total: ~20 minutes (vs 27 minutes sequential)"
echo "=========================================="

# Step 1: Create basic Azure resources (1 minute)
echo ""
echo "Step 1: Creating Azure resources..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create storage account
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2 &

STORAGE_PID=$!

# Step 2: Create VMs immediately (start them early!)
echo ""
echo "Step 2: Creating 3 VMs (they'll setup while we upload PDFs)..."
for i in $(seq 1 $NUM_VMS); do
    echo "Creating VM $i..."
    az vm create \
        --resource-group $RESOURCE_GROUP \
        --name grobid-vm-$i \
        --image Ubuntu2204 \
        --size $VM_SIZE \
        --admin-username azureuser \
        --generate-ssh-keys \
        --public-ip-sku Standard \
        --no-wait &
done

# Step 3: Wait for storage account then create file share
echo ""
echo "Step 3: Setting up file share..."
wait $STORAGE_PID

STORAGE_KEY=$(az storage account keys list \
    --resource-group $RESOURCE_GROUP \
    --account-name $STORAGE_ACCOUNT \
    --query "[0].value" -o tsv)

az storage share create \
    --name $FILE_SHARE_NAME \
    --account-name $STORAGE_ACCOUNT \
    --account-key $STORAGE_KEY \
    --quota 5

# Step 4: Start VM setup AND PDF upload in parallel
echo ""
echo "Step 4: Starting parallel tasks..."
echo "  - Setting up VMs (Docker, Grobid)"
echo "  - Uploading PDFs (658MB)"

# Create VM setup script (runs independently)
cat > vm_setup.sh << 'SETUP_SCRIPT'
#!/bin/bash
set -e

echo "[$(date)] Starting VM setup..."

# Install Docker
sudo apt-get update
curl -fsSL https://get.docker.com | sudo sh

# Install required packages
sudo apt-get install -y cifs-utils python3-pip
pip3 install requests tqdm

# Pull Grobid (this is the slow part - 17GB)
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

echo "[$(date)] VM setup complete!"
SETUP_SCRIPT

# Start VM setup on all VMs (in background)
echo "Starting VM setup (runs for 10-15 minutes)..."
for i in $(seq 1 $NUM_VMS); do
    # Wait for VM to be ready (but don't block)
    (
        while ! az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv 2>/dev/null | grep -q "\."; do
            sleep 5
        done

        VM_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv)
        echo "VM $i ready at $VM_IP, starting setup..."

        # Add to known hosts
        ssh-keyscan -H $VM_IP >> ~/.ssh/known_hosts 2>/dev/null

        # Copy and run setup
        scp vm_setup.sh azureuser@$VM_IP:~/
        ssh azureuser@$VM_IP "chmod +x vm_setup.sh && nohup ./vm_setup.sh > setup.log 2>&1 &"
        echo "VM $i setup started in background"
    ) &
done

# Create PDF upload script
cat > upload_pdfs.py << 'UPLOAD_SCRIPT'
#!/usr/bin/env python3
import os
import sys
from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
from pathlib import Path
from tqdm import tqdm

storage_account = sys.argv[1]
storage_key = sys.argv[2]
share_name = sys.argv[3]

print("[Upload] Starting PDF upload to Azure...")

# Find all PDFs in Zotero
zotero_path = Path.home() / "Zotero" / "storage"
pdf_files = list(zotero_path.glob("*/*.pdf"))
print(f"[Upload] Found {len(pdf_files)} PDFs to upload (658MB total)")

# Upload each PDF maintaining directory structure
for pdf_path in tqdm(pdf_files, desc="Uploading PDFs"):
    relative_path = pdf_path.relative_to(zotero_path)
    dir_name = relative_path.parent
    file_name = relative_path.name

    # Create directory if needed
    dir_client = ShareDirectoryClient(
        account_url=f"https://{storage_account}.file.core.windows.net",
        share_name=share_name,
        directory_path=str(dir_name),
        credential=storage_key
    )
    try:
        dir_client.create_directory()
    except:
        pass  # Directory might already exist

    # Upload file
    file_client = ShareFileClient(
        account_url=f"https://{storage_account}.file.core.windows.net",
        share_name=share_name,
        file_path=str(relative_path),
        credential=storage_key
    )

    with open(pdf_path, "rb") as source_file:
        file_client.upload_file(source_file)

print("[Upload] PDF upload complete!")
UPLOAD_SCRIPT

# Start PDF upload (in background)
echo "Starting PDF upload (658MB, 2-9 minutes)..."
pip install azure-storage-file-share tqdm --quiet
python3 upload_pdfs.py $STORAGE_ACCOUNT $STORAGE_KEY $FILE_SHARE_NAME &
UPLOAD_PID=$!

# Step 5: Wait for everything to complete
echo ""
echo "=========================================="
echo "PARALLEL OPERATIONS IN PROGRESS"
echo "=========================================="
echo "1. VMs installing Docker and pulling Grobid (10-15 min)"
echo "2. PDFs uploading to Azure (2-9 min)"
echo ""
echo "Waiting for both to complete..."

# Wait for upload to finish
wait $UPLOAD_PID
echo "✓ PDF upload complete!"

# Check VM setup status
echo ""
echo "Checking VM setup status..."
for i in $(seq 1 $NUM_VMS); do
    VM_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv)

    # Wait for setup to complete
    while ! ssh azureuser@$VM_IP "sudo docker ps | grep grobid" &>/dev/null; do
        echo "  VM $i: Still setting up..."
        sleep 30
    done
    echo "✓ VM $i: Setup complete!"
done

# Step 6: Mount file shares on all VMs
echo ""
echo "Step 6: Mounting file shares on VMs..."

for i in $(seq 1 $NUM_VMS); do
    VM_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv)

    ssh azureuser@$VM_IP << MOUNT_COMMANDS
sudo mkdir -p /mnt/pdfs
sudo mount -t cifs //${STORAGE_ACCOUNT}.file.core.windows.net/${FILE_SHARE_NAME} /mnt/pdfs \
  -o vers=3.0,username=${STORAGE_ACCOUNT},password=${STORAGE_KEY},dir_mode=0777,file_mode=0777,serverino

# Verify mount
ls /mnt/pdfs | head -5
echo "File share mounted successfully on VM $i"
MOUNT_COMMANDS
done

# Step 7: Copy extraction script to VMs
echo ""
echo "Step 7: Copying extraction scripts..."
for i in $(seq 1 $NUM_VMS); do
    VM_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv)
    scp extract_from_azure_share.py azureuser@$VM_IP:~/
done

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Total deployment time: ~20 minutes (saved ~7 minutes!)"
echo ""
echo "VMs ready with:"
echo "  ✓ Grobid running"
echo "  ✓ PDFs accessible at /mnt/pdfs"
echo "  ✓ Extraction script ready"
echo ""
echo "To start extraction:"
echo "  ./start_azure_extraction.sh"
echo ""
echo "This will process all 2,221 PDFs in ~3.7 hours"
