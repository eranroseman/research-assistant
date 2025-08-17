# Use of a Machine Learning Program to Correctly Triage Incoming Text Messaging Replies From a Cardiovascular Text–Based Secondary Prevention Program: Feasibility Study

**Authors:** Nicole Lowres, Andrew Duckworth, Julie Redfern, Aravinda Thiagalingam, Clara K Chow  
**Year:** 2020  
**Journal:** JMIR mHealth and uHealth  
**Volume:** 8  
**Issue:** 6  
**Pages:** e19200  
**DOI:** 10.2196/19200  

## Abstract
Background
              SMS text messaging programs are increasingly being used for secondary prevention, and have been shown to be effective in a number of health conditions including cardiovascular disease. SMS text messaging programs have the potential to increase the reach of an intervention, at a reduced cost, to larger numbers of people who may not access traditional programs. However, patients regularly reply to the SMS text messages, leading to additional staffing requirements to monitor and moderate the patients’ SMS text messaging replies. This additional staff requirement directly impacts the cost-effectiveness and scalability of SMS text messaging interventions.
            
            
              Objective
              This study aimed to test the feasibility and accuracy of developing a machine learning (ML) program to triage SMS text messaging replies (ie, identify which SMS text messaging replies require a health professional review).
            
            
              Methods
              SMS text messaging replies received from 2 clinical trials were manually coded (1) into “Is staff review required?” (binary response of yes/no); and then (2) into 12 general categories. Five ML models (Naïve Bayes, OneVsRest, Random Forest Decision Trees, Gradient Boosted Trees, and Multilayer Perceptron) and an ensemble model were tested. For each model run, data were randomly allocated into training set (2183/3118, 70.01%) and test set (935/3118, 29.98%). Accuracy for the yes/no classification was calculated using area under the receiver operating characteristics curve (AUC), false positives, and false negatives. Accuracy for classification into 12 categories was compared using multiclass classification evaluators.
            
            
              Results
              A manual review of 3118 SMS text messaging replies showed that 22.00% (686/3118) required staff review. For determining need for staff review, the Multilayer Perceptron model had highest accuracy (AUC 0.86; 4.85% false negatives; and 4.63% false positives); with addition of heuristics (specified keywords) fewer false negatives were identified (3.19%), with small increase in false positives (7.66%) and AUC 0.79. Application of this model would result in 26.7% of SMS text messaging replies requiring review (true + false positives). The ensemble model produced the lowest false negatives (1.43%) at the expense of higher false positives (16.19%). OneVsRest was the most accurate (72.3%) for the 12-category classification.
            
            
              Conclusions
              The ML program has high sensitivity for identifying the SMS text messaging replies requiring staff input; however, future research is required to validate the models against larger data sets. Incorporation of an ML program to review SMS text messaging replies could significantly reduce staff workload, as staff would not have to review all incoming SMS text messages. This could lead to substantial improvements in cost-effectiveness, scalability, and capacity of SMS text messaging–based interventions.

