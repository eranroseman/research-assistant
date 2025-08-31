#!/bin/bash
# Monitor extraction progress on Azure VMs

RESOURCE_GROUP="grobid-fileshare-rg"

# Get VM IPs
VM1_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-1 --query publicIps -o tsv)
VM3_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-3 --query publicIps -o tsv)

while true; do
    clear
    echo "=========================================="
    echo "AZURE GROBID EXTRACTION MONITOR"
    echo "$(date)"
    echo "=========================================="

    echo ""
    echo "VM1 ($VM1_IP):"
    echo "-------------------"
    # Get last log entries
    ssh -o ConnectTimeout=5 azureuser@$VM1_IP "tail -3 extraction_vm_1/extraction_vm_1.log 2>/dev/null || echo 'Starting...'"
    # Count processed files
    VM1_COUNT=$(ssh -o ConnectTimeout=5 azureuser@$VM1_IP "find extraction_vm_1 -name '*_full.xml' 2>/dev/null | wc -l")
    echo "Processed: $VM1_COUNT / 1111 PDFs"

    echo ""
    echo "VM3 ($VM3_IP):"
    echo "-------------------"
    # Get last log entries
    ssh -o ConnectTimeout=5 azureuser@$VM3_IP "tail -3 extraction_vm_3/extraction_vm_3.log 2>/dev/null || echo 'Starting...'"
    # Count processed files
    VM3_COUNT=$(ssh -o ConnectTimeout=5 azureuser@$VM3_IP "find extraction_vm_3 -name '*_full.xml' 2>/dev/null | wc -l")
    echo "Processed: $VM3_COUNT / 1110 PDFs"

    echo ""
    echo "=========================================="
    TOTAL=$((VM1_COUNT + VM3_COUNT))
    echo "TOTAL PROGRESS: $TOTAL / 2221 PDFs ($(echo "scale=1; $TOTAL * 100 / 2221" | bc)%)"

    # Estimate time remaining
    if [ $TOTAL -gt 0 ]; then
        ELAPSED=$(ssh -o ConnectTimeout=5 azureuser@$VM1_IP "stat -c %Y extraction_vm_1/extraction_vm_1.log 2>/dev/null || echo 0")
        if [ "$ELAPSED" != "0" ]; then
            NOW=$(date +%s)
            RUNTIME=$((NOW - ELAPSED))
            RATE=$(echo "scale=2; $TOTAL / $RUNTIME" | bc)
            REMAINING=$(echo "scale=1; (2221 - $TOTAL) / ($RATE * 3600)" | bc)
            echo "Estimated time remaining: $REMAINING hours"
        fi
    fi

    echo "=========================================="
    echo "Press Ctrl+C to exit monitoring"
    echo "Refreshing in 60 seconds..."
    sleep 60
done
