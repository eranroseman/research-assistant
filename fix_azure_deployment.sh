#!/bin/bash
# Fix the partial deployment and continue

set -e

RESOURCE_GROUP="grobid-fileshare-rg"
LOCATION="westus2"
STORAGE_ACCOUNT="grobidpdfs$(date +%s | tail -c 10)"  # Shorter unique name
FILE_SHARE_NAME="pdfs"

echo "=========================================="
echo "FIXING AZURE DEPLOYMENT"
echo "=========================================="
echo "Current status:"
echo "  ✓ Resource group created"
echo "  ✓ 2 VMs running (grobid-vm-1, grobid-vm-3)"
echo "  ✗ Storage account missing"
echo "  ✗ VM 2 missing"
echo "=========================================="

# Step 1: Create storage account with shorter name
echo ""
echo "Step 1: Creating storage account..."
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2

echo "Storage account created: $STORAGE_ACCOUNT"

# Get storage key
STORAGE_KEY=$(az storage account keys list \
    --resource-group $RESOURCE_GROUP \
    --account-name $STORAGE_ACCOUNT \
    --query "[0].value" -o tsv)

# Step 2: Create file share
echo ""
echo "Step 2: Creating file share..."
az storage share create \
    --name $FILE_SHARE_NAME \
    --account-name $STORAGE_ACCOUNT \
    --account-key "$STORAGE_KEY" \
    --quota 5

# Step 3: Try to create VM 2
echo ""
echo "Step 3: Attempting to create VM 2..."
az vm create \
    --resource-group $RESOURCE_GROUP \
    --name grobid-vm-2 \
    --image Ubuntu2204 \
    --size Standard_D2s_v3 \
    --admin-username azureuser \
    --generate-ssh-keys \
    --public-ip-sku Standard || echo "VM 2 creation failed (quota?), continuing with 2 VMs"

# Step 4: Setup existing VMs
echo ""
echo "Step 4: Setting up VMs with Docker and Grobid..."

# Get VM IPs
VM1_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-1 --query publicIps -o tsv)
VM3_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-3 --query publicIps -o tsv)

echo "VM 1: $VM1_IP"
echo "VM 3: $VM3_IP"

# Add to known hosts
ssh-keyscan -H $VM1_IP >> ~/.ssh/known_hosts 2>/dev/null
ssh-keyscan -H $VM3_IP >> ~/.ssh/known_hosts 2>/dev/null

# Create setup script
cat > vm_setup.sh << 'SETUP'
#!/bin/bash
set -e

echo "Installing Docker..."
curl -fsSL https://get.docker.com | sudo sh

echo "Installing packages..."
sudo apt-get update
sudo apt-get install -y cifs-utils python3-pip
pip3 install requests tqdm azure-storage-file-share

echo "Pulling Grobid (17GB)..."
sudo docker pull lfoppiano/grobid:0.8.2-full

echo "Starting Grobid..."
sudo docker run -d --name grobid \
  -p 8070:8070 \
  --memory="6g" \
  --memory-swap="6g" \
  --restart unless-stopped \
  lfoppiano/grobid:0.8.2-full

echo "Setup complete!"
SETUP

# Copy and run setup on both VMs
for VM_IP in $VM1_IP $VM3_IP; do
    echo "Setting up VM at $VM_IP..."
    scp vm_setup.sh azureuser@$VM_IP:~/
    ssh azureuser@$VM_IP "chmod +x vm_setup.sh && nohup ./vm_setup.sh > setup.log 2>&1 &" &
done

# Step 5: Upload PDFs while VMs setup
echo ""
echo "Step 5: Uploading PDFs to Azure File Share..."
echo "Storage Account: $STORAGE_ACCOUNT"
echo "File Share: $FILE_SHARE_NAME"

# Create upload script
cat > upload_pdfs.py << UPLOAD
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

storage_account = "$STORAGE_ACCOUNT"
storage_key = """$STORAGE_KEY"""
share_name = "$FILE_SHARE_NAME"

print(f"Uploading to {storage_account}/{share_name}")

try:
    from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
    from tqdm import tqdm
except ImportError:
    print("Installing required packages...")
    os.system("pip install azure-storage-file-share tqdm")
    from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
    from tqdm import tqdm

# Find all PDFs
zotero_path = Path.home() / "Zotero" / "storage"
pdf_files = list(zotero_path.glob("*/*.pdf"))
print(f"Found {len(pdf_files)} PDFs to upload")

# Upload each PDF
for pdf_path in tqdm(pdf_files, desc="Uploading PDFs"):
    relative_path = pdf_path.relative_to(zotero_path)
    dir_name = str(relative_path.parent)

    # Create directory
    dir_client = ShareDirectoryClient(
        account_url=f"https://{storage_account}.file.core.windows.net",
        share_name=share_name,
        directory_path=dir_name,
        credential=storage_key
    )
    try:
        dir_client.create_directory()
    except:
        pass

    # Upload file
    file_client = ShareFileClient(
        account_url=f"https://{storage_account}.file.core.windows.net",
        share_name=share_name,
        file_path=str(relative_path),
        credential=storage_key
    )

    with open(pdf_path, "rb") as f:
        file_client.upload_file(f)

print("Upload complete!")
UPLOAD

# Run upload
python3 upload_pdfs.py &
UPLOAD_PID=$!

echo ""
echo "=========================================="
echo "PARALLEL OPERATIONS IN PROGRESS"
echo "=========================================="
echo "1. VMs installing Docker and Grobid (10-15 min)"
echo "2. PDFs uploading to Azure (2-9 min)"
echo ""

# Wait for upload
wait $UPLOAD_PID
echo "✓ PDF upload complete!"

# Wait for VMs to be ready
echo ""
echo "Waiting for VMs to complete setup..."
sleep 300  # Wait 5 minutes minimum

# Check if Grobid is running
for VM_IP in $VM1_IP $VM3_IP; do
    echo "Checking VM at $VM_IP..."
    ssh azureuser@$VM_IP "sudo docker ps | grep grobid || echo 'Still setting up...'"
done

# Step 6: Mount file shares
echo ""
echo "Step 6: Mounting file shares on VMs..."

for VM_IP in $VM1_IP $VM3_IP; do
    echo "Mounting on $VM_IP..."
    ssh azureuser@$VM_IP << MOUNT
sudo mkdir -p /mnt/pdfs
sudo mount -t cifs //${STORAGE_ACCOUNT}.file.core.windows.net/${FILE_SHARE_NAME} /mnt/pdfs \
  -o vers=3.0,username=${STORAGE_ACCOUNT},password="${STORAGE_KEY}",dir_mode=0777,file_mode=0777,serverino

ls /mnt/pdfs | head -3
echo "Mounted successfully!"
MOUNT
done

echo ""
echo "=========================================="
echo "DEPLOYMENT FIXED!"
echo "=========================================="
echo ""
echo "Working with 2 VMs (processing will take ~5.5 hours instead of 3.7)"
echo ""
echo "Storage Account: $STORAGE_ACCOUNT"
echo "File Share: $FILE_SHARE_NAME"
echo ""
echo "Next: Adjust extraction script for 2 VMs and start processing"
