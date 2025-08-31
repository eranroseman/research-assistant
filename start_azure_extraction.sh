#!/bin/bash
# Start extraction on all Azure VMs

RESOURCE_GROUP="grobid-fileshare-rg"

echo "=========================================="
echo "STARTING EXTRACTION ON AZURE VMs"
echo "=========================================="

# Copy extraction script to all VMs
for i in 1 2 3; do
    VM_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv)
    echo "Copying extraction script to VM $i ($VM_IP)..."
    scp extract_from_azure_share.py azureuser@$VM_IP:~/
done

# Start extraction on all VMs
for i in 1 2 3; do
    VM_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv)
    echo ""
    echo "Starting extraction on VM $i..."
    ssh azureuser@$VM_IP "nohup python3 extract_from_azure_share.py $i > extraction.log 2>&1 &"
    echo "VM $i extraction started in background"
done

echo ""
echo "=========================================="
echo "EXTRACTION STARTED ON ALL VMs"
echo "=========================================="
echo ""
echo "Expected completion: ~3.7 hours"
echo ""
echo "To monitor progress:"
echo "  ./monitor_azure_extraction.sh"
echo ""
echo "To collect results when done:"
echo "  ./collect_azure_results.sh"
