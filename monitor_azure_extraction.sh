#!/bin/bash
# Monitor extraction progress on Azure VMs

RESOURCE_GROUP="grobid-fileshare-rg"

while true; do
    clear
    echo "=========================================="
    echo "AZURE GROBID EXTRACTION MONITOR"
    echo "$(date)"
    echo "=========================================="

    for i in 1 2 3; do
        VM_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv 2>/dev/null)
        echo ""
        echo "VM $i ($VM_IP):"
        echo "-------------------"
        ssh -o ConnectTimeout=5 azureuser@$VM_IP "tail -5 extraction_vm_${i}.log 2>/dev/null || echo 'No log yet'" 2>/dev/null
    done

    echo ""
    echo "=========================================="
    echo "Press Ctrl+C to exit monitoring"
    echo "Refreshing in 30 seconds..."
    sleep 30
done
