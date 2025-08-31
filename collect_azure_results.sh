#!/bin/bash
# Collect extraction results from Azure VMs

RESOURCE_GROUP="grobid-fileshare-rg"
RESULTS_DIR="azure_extraction_results_$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "COLLECTING RESULTS FROM AZURE VMs"
echo "=========================================="

mkdir -p $RESULTS_DIR

for i in 1 2 3; do
    VM_IP=$(az vm show -d -g $RESOURCE_GROUP -n grobid-vm-$i --query publicIps -o tsv)
    echo "Collecting from VM $i ($VM_IP)..."

    # Copy extraction results
    scp -r azureuser@$VM_IP:~/extraction_vm_$i $RESULTS_DIR/ &
done

wait

echo ""
echo "Counting results..."
TOTAL_FILES=$(find $RESULTS_DIR -name "*_metadata.json" | wc -l)
echo "Total papers extracted: $TOTAL_FILES"

echo ""
echo "Results saved to: $RESULTS_DIR"
echo ""
echo "To cleanup Azure resources (save ~$10/day):"
echo "  az group delete --name $RESOURCE_GROUP --yes"
