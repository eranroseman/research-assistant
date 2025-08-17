# Detecting emergencies in patient portal messages using large language models and knowledge graph-based retrieval-augmented generation

**Authors:** Siru Liu, Aileen P Wright, Allison B McCoy, Sean S Huang, Bryan Steitz, Adam Wright  
**Year:** 2025  
**Journal:** Journal of the American Medical Informatics Association  
**Volume:** 32  
**Issue:** 6  
**Pages:** 1032-1039  
**DOI:** 10.1093/jamia/ocaf059  

## Abstract
Abstract
            
              Objectives
              This study aims to develop and evaluate an approach using large language models (LLMs) and a knowledge graph to triage patient messages that need emergency care. The goal is to notify patients when their messages indicate an emergency, guiding them to seek immediate help rather than using the patient portal, to improve patient safety.
            
            
              Materials and Methods
              We selected 1020 messages sent to Vanderbilt University Medical Center providers between January 1, 2022 and March 7, 2023. We developed four models to triage these messages for emergencies: (1) Prompt-Only: the patient message was input with a prompt directly into the LLM; (2) Naïve Retrieval Augmented Generation (RAG): provided retrieved information as context to the LLM; (3) RAG from Knowledge Graph with Local Search: a knowledge graph was used to retrieve locally relevant information based on semantic similarities; (4) RAG from Knowledge Graph with Global Search: a knowledge graph was used to retrieve globally relevant information through hierarchical community detection. The knowledge base was a triage book covering 225 protocols.
            
            
              Results
              The RAG from Knowledge Graph model with global search outperformed other models, achieving an accuracy of 0.99, a sensitivity of 0.98, and a specificity of 0.99. It demonstrated significant improvements in triaging emergency messages compared to LLM without RAG and naïve RAG.
            
            
              Discussion
              The traditional LLM without any retrieval mechanism underperformed compared to models with RAG, which aligns with the expected benefits of augmenting LLMs with domain-specific knowledge sources. Our results suggest that providing external knowledge, especially in a structured manner and in community summaries, can improve LLM performance in triaging patient portal messages.
            
            
              Conclusion
              LLMs can effectively assist in triaging emergency patient messages after integrating with a knowledge graph about a nurse triage book. Future research should focus on expanding the knowledge graph and deploying the system to evaluate its impact on patient outcomes.

