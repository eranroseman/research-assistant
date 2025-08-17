# Natural language processing system for rapid detection and intervention of mental health crisis chat messages

**Authors:** Akshay Swaminathan, Iván López, Rafael Antonio Garcia Mar, Tyler Heist, Tom McClintock, Kaitlin Caoili, Madeline Grace, Matthew Rubashkin, Michael N. Boggs, Jonathan H. Chen, Olivier Gevaert, David Mou, Matthew K. Nock  
**Year:** 2023  
**Journal:** npj Digital Medicine  
**Volume:** 6  
**Issue:** 1  
**DOI:** 10.1038/s41746-023-00951-3  

## Abstract
AbstractPatients experiencing mental health crises often seek help through messaging-based platforms, but may face long wait times due to limited message triage capacity. Here we build and deploy a machine-learning-enabled system to improve response times to crisis messages in a large, national telehealth provider network. We train a two-stage natural language processing (NLP) system with key word filtering followed by logistic regression on 721 electronic medical record chat messages, of which 32% are potential crises (suicidal/homicidal ideation, domestic violence, or non-suicidal self-injury). Model performance is evaluated on a retrospective test set (4/1/21–4/1/22, N = 481) and a prospective test set (10/1/22–10/31/22, N = 102,471). In the retrospective test set, the model has an AUC of 0.82 (95% CI: 0.78–0.86), sensitivity of 0.99 (95% CI: 0.96–1.00), and PPV of 0.35 (95% CI: 0.309–0.4). In the prospective test set, the model has an AUC of 0.98 (95% CI: 0.966–0.984), sensitivity of 0.98 (95% CI: 0.96–0.99), and PPV of 0.66 (95% CI: 0.626–0.692). The daily median time from message receipt to crisis specialist triage ranges from 8 to 13 min, compared to 9 h before the deployment of the system. We demonstrate that a NLP-based machine learning model can reliably identify potential crisis chat messages in a telehealth setting. Our system integrates into existing clinical workflows, suggesting that with appropriate training, humans can successfully leverage ML systems to facilitate triage of crisis messages.

