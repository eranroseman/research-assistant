# Federated Learning with Pareto Optimality for Resource Efficiency and Fast Model Convergence in Mobile Environments

**Authors:** June-Pyo Jung, Young-Bae Ko, Sung-Hwa Lim  
**Year:** 2024  
**Journal:** Sensors  
**Volume:** 24  
**Issue:** 8  
**Pages:** 2476  
**DOI:** 10.3390/s24082476  

## Abstract
Federated learning (FL) is an emerging distributed learning technique through which models can be trained using the data collected by user devices in resource-constrained situations while protecting user privacy. However, FL has three main limitations: First, the parameter server (PS), which aggregates the local models that are trained using local user data, is typically far from users. The large distance may burden the path links between the PS and local nodes, thereby increasing the consumption of the network and computing resources. Second, user device resources are limited, but this aspect is not considered in the training of the local model and transmission of the model parameters. Third, the PS-side links tend to become highly loaded as the number of participating clients increases. The links become congested owing to the large size of model parameters. In this study, we propose a resource-efficient FL scheme. We follow the Pareto optimality concept with the biased client selection to limit client participation, thereby ensuring efficient resource consumption and rapid model convergence. In addition, we propose a hierarchical structure with location-based clustering for device-to-device communication using k-means clustering. Simulation results show that with prate at 0.75, the proposed scheme effectively reduced transmitted and received network traffic by 75.89% and 78.77%, respectively, compared to the FedAvg method. It also achieves faster model convergence compared to other FL mechanisms, such as FedAvg and D2D-FedAvg.

