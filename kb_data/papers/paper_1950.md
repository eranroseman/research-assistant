# Machine learning approaches to predict the 1-year-after-initial-AMI survival of elderly patients

**Authors:** Jisoo Lee, Sulyun Lee, W. Nick Street, Linnea A. Polgreen  
**Year:** None  
**Journal:** BMC Medical Informatics and Decision Making  
**Volume:** 22  
**Issue:** 1  
**Pages:** 115  
**DOI:** 10.1186/s12911-022-01854-1  

## Abstract
Abstract
            
              Background
              While multiple randomized controlled trials (RCTs) are available, their results may not be generalizable to older, unhealthier or less-adherent patients. Observational data can be used to predict outcomes and evaluate treatments; however, exactly which strategy should be used to analyze the outcomes of treatment using observational data is currently unclear. This study aimed to determine the most accurate machine learning technique to predict 1-year-after-initial-acute-myocardial-infarction (AMI) survival of elderly patients and to identify the association of angiotensin-converting- enzyme inhibitors and angiotensin-receptor blockers (ACEi/ARBs) with survival.
            
            
              Methods
              We built a cohort of 124,031 Medicare beneficiaries who experienced an AMI in 2007 or 2008. For analytical purposes, all variables were categorized into nine different groups: ACEi/ARB use, demographics, cardiac events, comorbidities, complications, procedures, medications, insurance, and healthcare utilization. Our outcome of interest was 1-year-post-AMI survival. To solve this classification task, we used lasso logistic regression (LLR) and random forest (RF), and compared their performance depending on category selection, sampling methods, and hyper-parameter selection. Nested 10-fold cross-validation was implemented to obtain an unbiased estimate of performance evaluation. We used the area under the receiver operating curve (AUC) as our primary measure for evaluating the performance of predictive algorithms.
            
            
              Results
              LLR consistently showed best AUC results throughout the experiments, closely followed by RF. The best prediction was yielded with LLR based on the combination of demographics, comorbidities, procedures, and utilization. The coefficients from the final LLR model showed that AMI patients with many comorbidities, older ages, or living in a low-income area have a higher risk of mortality 1-year after an AMI. In addition, treating the AMI patients with ACEi/ARBs increases the 1-year-after-initial-AMI survival rate of the patients.
            
            
              Conclusions
              Given the many features we examined, ACEi/ARBs were associated with increased 1-year survival among elderly patients after an AMI. We found LLR to be the best-performing model over RF to predict 1-year survival after an AMI. LLR greatly improved the generalization of the model by feature selection, which implicitly indicates the association between AMI-related variables and survival can be defined by a relatively simple model with a small number of features. Some comorbidities were associated with a greater risk of mortality, such as heart failure and chronic kidney disease, but others were associated with survival such as hypertension, hyperlipidemia, and diabetes. In addition, patients who live in urban areas and areas with large numbers of immigrants have a higher probability of survival. Machine learning methods are helpful to determine outcomes when RCT results are not available.

