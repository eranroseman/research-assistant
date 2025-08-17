# Learning From Others Without Sacrificing Privacy: Simulation Comparing Centralized and Federated Machine Learning on Mobile Health Data

**Authors:** Jessica Chia Liu, Jack Goetz, Srijan Sen, Ambuj Tewari  
**Year:** 2021  
**Journal:** JMIR mHealth and uHealth  
**Volume:** 9  
**Issue:** 3  
**Pages:** e23728  
**DOI:** 10.2196/23728  

## Abstract
Background
              The use of wearables facilitates data collection at a previously unobtainable scale, enabling the construction of complex predictive models with the potential to improve health. However, the highly personal nature of these data requires strong privacy protection against data breaches and the use of data in a way that users do not intend. One method to protect user privacy while taking advantage of sharing data across users is federated learning, a technique that allows a machine learning model to be trained using data from all users while only storing a user’s data on that user’s device. By keeping data on users’ devices, federated learning protects users’ private data from data leaks and breaches on the researcher’s central server and provides users with more control over how and when their data are used. However, there are few rigorous studies on the effectiveness of federated learning in the mobile health (mHealth) domain.
            
            
              Objective
              We review federated learning and assess whether it can be useful in the mHealth field, especially for addressing common mHealth challenges such as privacy concerns and user heterogeneity. The aims of this study are to describe federated learning in an mHealth context, apply a simulation of federated learning to an mHealth data set, and compare the performance of federated learning with the performance of other predictive models.
            
            
              Methods
              We applied a simulation of federated learning to predict the affective state of 15 subjects using physiological and motion data collected from a chest-worn device for approximately 36 minutes. We compared the results from this federated model with those from a centralized or server model and with the results from training individual models for each subject.
            
            
              Results
              In a 3-class classification problem using physiological and motion data to predict whether the subject was undertaking a neutral, amusing, or stressful task, the federated model achieved 92.8% accuracy on average, the server model achieved 93.2% accuracy on average, and the individual model achieved 90.2% accuracy on average.
            
            
              Conclusions
              Our findings support the potential for using federated learning in mHealth. The results showed that the federated model performed better than a model trained separately on each individual and nearly as well as the server model. As federated learning offers more privacy than a server model, it may be a valuable option for designing sensitive data collection methods.

