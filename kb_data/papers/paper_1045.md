# Text Message Analysis Using Machine Learning to Assess Predictors of Engagement With Mobile Health Chronic Disease Prevention Programs: Content Analysis

**Authors:** Harry Klimis, Joel Nothman, Di Lu, Chao Sun, N Wah Cheung, Julie Redfern, Aravinda Thiagalingam, Clara K Chow  
**Year:** 2021  
**Journal:** JMIR mHealth and uHealth  
**Volume:** 9  
**Issue:** 11  
**Pages:** e27779  
**DOI:** 10.2196/27779  

## Abstract
Background
              SMS text messages as a form of mobile health are increasingly being used to support individuals with chronic diseases in novel ways that leverage the mobility and capabilities of mobile phones. However, there are knowledge gaps in mobile health, including how to maximize engagement.
            
            
              Objective
              This study aims to categorize program SMS text messages and participant replies using machine learning (ML) and to examine whether message characteristics are associated with premature program stopping and engagement.
            
            
              Methods
              We assessed communication logs from SMS text message–based chronic disease prevention studies that encouraged 1-way (SupportMe/ITM) and 2-way (TEXTMEDS [Text Messages to Improve Medication Adherence and Secondary Prevention]) communication. Outgoing messages were manually categorized into 5 message intents (informative, instructional, motivational, supportive, and notification) and replies into 7 groups (stop, thanks, questions, reporting healthy, reporting struggle, general comment, and other). Grid search with 10-fold cross-validation was implemented to identify the best-performing ML models and evaluated using nested cross-validation. Regression models with interaction terms were used to compare the association of message intent with premature program stopping and engagement (replied at least 3 times and did not prematurely stop) in SupportMe/ITM and TEXTMEDS.
            
            
              Results
              We analyzed 1550 messages and 4071 participant replies. Approximately 5.49% (145/2642) of participants responded with stop, and 11.7% (309/2642) of participants were engaged. Our optimal ML model correctly classified program message intent with 76.6% (95% CI 63.5%-89.8%) and replies with 77.8% (95% CI 74.1%-81.4%) balanced accuracy (average area under the curve was 0.95 and 0.96, respectively). Overall, supportive (odds ratio [OR] 0.53, 95% CI 0.35-0.81) messages were associated with reduced chance of stopping, as were informative messages in SupportMe/ITM (OR 0.35, 95% CI 0.20-0.60) but not in TEXTMEDS (for interaction, P<.001). Notification messages were associated with a higher chance of stopping in SupportMe/ITM (OR 5.76, 95% CI 3.66-9.06) but not TEXTMEDS (for interaction, P=.01). Overall, informative (OR 1.76, 95% CI 1.46-2.12) and instructional (OR 1.47, 95% CI 1.21-1.80) messages were associated with higher engagement but not motivational messages (OR 1.18, 95% CI 0.82-1.70; P=.37). For supportive messages, the association with engagement was opposite with SupportMe/ITM (OR 1.77, 95% CI 1.21-2.58) compared with TEXTMEDS (OR 0.77, 95% CI 0.60-0.98; for interaction, P<.001). Notification messages were associated with reduced engagement in SupportMe/ITM (OR 0.07, 95% CI 0.05-0.10) and TEXTMEDS (OR 0.28, 95% CI 0.20-0.39); however, the strength of the association was greater in SupportMe/ITM (for interaction P<.001).
            
            
              Conclusions
              ML models enable monitoring and detailed characterization of program messages and participant replies. Outgoing message intent may influence premature program stopping and engagement, although the strength and direction of association appear to vary by program type. Future studies will need to examine whether modifying message characteristics can optimize engagement and whether this leads to behavior change.

