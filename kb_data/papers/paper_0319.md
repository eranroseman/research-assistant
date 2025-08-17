# A Deep-Learning Algorithm (ECG12Net) for Detecting Hypokalemia and Hyperkalemia by Electrocardiography: Algorithm Development

**Authors:** Chin-Sheng Lin, Chin Lin, Wen-Hui Fang, Chia-Jung Hsu, Sy-Jou Chen, Kuo-Hua Huang, Wei-Shiang Lin, Chien-Sung Tsai, Chih-Chun Kuo, Tom Chau, Stephen Jh Yang, Shih-Hua Lin  
**Year:** 2020  
**Journal:** JMIR Medical Informatics  
**Volume:** 8  
**Issue:** 3  
**Pages:** e15931  
**DOI:** 10.2196/15931  

## Abstract
Background
              The detection of dyskalemias—hypokalemia and hyperkalemia—currently depends on laboratory tests. Since cardiac tissue is very sensitive to dyskalemia, electrocardiography (ECG) may be able to uncover clinically important dyskalemias before laboratory results.
            
            
              Objective
              Our study aimed to develop a deep-learning model, ECG12Net, to detect dyskalemias based on ECG presentations and to evaluate the logic and performance of this model.
            
            
              Methods
              Spanning from May 2011 to December 2016, 66,321 ECG records with corresponding serum potassium (K+) concentrations were obtained from 40,180 patients admitted to the emergency department. ECG12Net is an 82-layer convolutional neural network that estimates serum K+ concentration. Six clinicians—three emergency physicians and three cardiologists—participated in human-machine competition. Sensitivity, specificity, and balance accuracy were used to evaluate the performance of ECG12Net with that of these physicians.
            
            
              Results
              In a human-machine competition including 300 ECGs of different serum K+ concentrations, the area under the curve for detecting hypokalemia and hyperkalemia with ECG12Net was 0.926 and 0.958, respectively, which was significantly better than that of our best clinicians. Moreover, in detecting hypokalemia and hyperkalemia, the sensitivities were 96.7% and 83.3%, respectively, and the specificities were 93.3% and 97.8%, respectively. In a test set including 13,222 ECGs, ECG12Net had a similar performance in terms of sensitivity for severe hypokalemia (95.6%) and severe hyperkalemia (84.5%), with a mean absolute error of 0.531. The specificities for detecting hypokalemia and hyperkalemia were 81.6% and 96.0%, respectively.
            
            
              Conclusions
              A deep-learning model based on a 12-lead ECG may help physicians promptly recognize severe dyskalemias and thereby potentially reduce cardiac events.

