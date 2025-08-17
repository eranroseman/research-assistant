#!/usr/bin/env python3
"""
Knowledge Base Builder for Research Assistant
Converts Zotero library to portable format with semantic search
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import click
import faiss
import pdfplumber
import pypdf
import requests
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class KnowledgeBaseBuilder:
    def __init__(self, knowledge_base_path: str = "kb_data"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.papers_path = self.knowledge_base_path / "papers"
        self.index_file_path = self.knowledge_base_path / "index.faiss"
        self.metadata_file_path = self.knowledge_base_path / "metadata.json"

        self.knowledge_base_path.mkdir(exist_ok=True)
        self.papers_path.mkdir(exist_ok=True)

        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    def extract_pdf_text(self, pdf_path: str) -> str | None:
        """Extract text from PDF using multiple methods."""
        text = ""

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception:
            try:
                with open(pdf_path, "rb") as file:
                    reader = pypdf.PdfReader(file)
                    for page_num in range(len(reader.pages)):
                        page_obj = reader.pages[page_num]
                        text += page_obj.extract_text() + "\n"
            except Exception as e:
                print(f"Error extracting PDF {pdf_path}: {e}")
                return None

        return text.strip() if text else None

    def format_paper_as_markdown(self, paper_data: dict) -> str:
        """Format paper data as markdown."""
        markdown_content = f"# {paper_data['title']}\n\n"

        if paper_data.get("authors"):
            markdown_content += f"**Authors:** {', '.join(paper_data['authors'])}  \n"
        markdown_content += f"**Year:** {paper_data.get('year', 'Unknown')}  \n"

        if paper_data.get("journal"):
            markdown_content += f"**Journal:** {paper_data['journal']}  \n"
        if paper_data.get("volume"):
            markdown_content += f"**Volume:** {paper_data['volume']}  \n"
        if paper_data.get("issue"):
            markdown_content += f"**Issue:** {paper_data['issue']}  \n"
        if paper_data.get("pages"):
            markdown_content += f"**Pages:** {paper_data['pages']}  \n"
        if paper_data.get("doi"):
            markdown_content += f"**DOI:** {paper_data['doi']}  \n"

        markdown_content += "\n## Abstract\n"
        markdown_content += (
            paper_data.get("abstract", "No abstract available.") + "\n\n"
        )

        if paper_data.get("full_text"):
            markdown_content += "## Full Text\n"
            markdown_content += paper_data["full_text"] + "\n"

        return str(markdown_content)

    def process_zotero_local_library(self, api_url: str | None = None) -> list[dict]:
        """Extract papers from Zotero local library using HTTP API."""
        if api_url:
            base_url = api_url
        else:
            base_url = "http://localhost:23119/api"
        
        # Test connection to local Zotero
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Zotero local API not accessible. Ensure Zotero is running and 'Allow other applications' is enabled in Advanced settings.")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Cannot connect to Zotero local API: {e}")
        
        # Get all items from library
        try:
            response = requests.get(f"{base_url}/users/0/items", timeout=30)
            response.raise_for_status()
            items = response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to fetch items from Zotero: {e}")
        
        papers = []
        
        for item in tqdm(items, desc="Processing Zotero items"):
            if item.get("data", {}).get("itemType") not in [
                "journalArticle",
                "conferencePaper",
                "preprint",
                "book",
            ]:
                continue

            paper_data = {
                "title": item["data"].get("title", ""),
                "authors": [],
                "year": None,
                "journal": item["data"].get("publicationTitle", ""),
                "volume": item["data"].get("volume", ""),
                "issue": item["data"].get("issue", ""),
                "pages": item["data"].get("pages", ""),
                "doi": item["data"].get("DOI", ""),
                "abstract": item["data"].get("abstractNote", ""),
                "zotero_key": item.get("key", ""),
            }

            for creator in item["data"].get("creators", []):
                if creator.get("lastName"):
                    name = (
                        f"{creator.get('firstName', '')} {creator['lastName']}".strip()
                    )
                    paper_data["authors"].append(name)

            if item["data"].get("date"):
                try:
                    paper_data["year"] = int(item["data"]["date"][:4])
                except (ValueError, IndexError, KeyError):
                    pass

            # Get attachments for this item
            if "key" in item:
                try:
                    attachments_response = requests.get(
                        f"{base_url}/users/0/items/{item['key']}/children",
                        timeout=10
                    )
                    if attachments_response.status_code == 200:
                        attachments = attachments_response.json()
                        for attachment in attachments:
                            if attachment.get("data", {}).get("contentType") == "application/pdf":
                                # Try to get file path
                                if "path" in attachment.get("data", {}):
                                    pdf_path = attachment["data"]["path"]
                                    # Handle different path formats
                                    if pdf_path.startswith("attachments:"):
                                        # This is a linked file path
                                        pdf_path = pdf_path.replace("attachments:", "")
                                    paper_data["full_text"] = self.extract_pdf_text(pdf_path)
                                    break
                except Exception:
                    pass

            papers.append(paper_data)

        return papers

    def build_from_zotero_local(self, api_url: str | None = None):
        """Build knowledge base from local Zotero library."""
        print("Extracting papers from local Zotero library...")
        papers = self.process_zotero_local_library(api_url)
        self.build_from_papers(papers)

    def build_from_papers(self, papers: list[dict]):
        """Build knowledge base from a list of paper dictionaries."""
        print(f"Processing {len(papers)} papers...")

        metadata = {
            "papers": [],
            "total_papers": len(papers),
            "last_updated": datetime.now().isoformat(),
        }

        abstracts = []

        for i, paper in enumerate(tqdm(papers, desc="Building knowledge base")):
            paper_id = f"{i + 1:04d}"

            paper_metadata = {
                "id": paper_id,
                "doi": paper.get("doi", ""),
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "year": paper.get("year", None),
                "journal": paper.get("journal", ""),
                "volume": paper.get("volume", ""),
                "issue": paper.get("issue", ""),
                "pages": paper.get("pages", ""),
                "abstract": paper.get("abstract", ""),
                "filename": f"paper_{paper_id}.md",
                "embedding_index": i,
            }

            metadata["papers"].append(paper_metadata)  # type: ignore

            md_content = self.format_paper_as_markdown(paper)
            markdown_file_path = self.papers_path / f"paper_{paper_id}.md"
            with open(markdown_file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            abstracts.append(paper.get("abstract", paper.get("title", "")))

        print("Building FAISS index...")
        if abstracts:
            embeddings = self.embedding_model.encode(abstracts, show_progress_bar=True)

            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings.astype("float32"))
        else:
            # Create empty index with default dimension
            dimension = 384  # Default dimension for all-MiniLM-L6-v2
            index = faiss.IndexFlatL2(dimension)

        faiss.write_index(index, str(self.index_file_path))

        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print("Knowledge base built successfully!")
        print(f"  - Papers: {len(papers)}")
        print(f"  - Index: {self.index_file_path}")
        print(f"  - Metadata: {self.metadata_file_path}")
        print(f"  - Papers directory: {self.papers_path}")

    def build_demo_kb(self):
        """Build a demo knowledge base with sample papers."""
        demo_papers = [
            {
                "title": "Digital Health Interventions for Depression, Anxiety, and Enhancement of Psychological Well-Being",
                "authors": ["John Smith", "Jane Doe", "Alice Johnson"],
                "year": 2023,
                "journal": "Nature Digital Medicine",
                "volume": "6",
                "issue": "3",
                "pages": "123-145",
                "doi": "10.1038/s41746-023-00789-9",
                "abstract": "Digital health interventions have shown promise in addressing mental health challenges. This systematic review examines the effectiveness of mobile apps, web-based platforms, and digital therapeutics for treating depression and anxiety disorders. We analyzed 127 randomized controlled trials involving over 50,000 participants. Results indicate moderate to large effect sizes for guided digital interventions compared to waitlist controls.",
                "full_text": "Introduction\n\nThe proliferation of digital technologies has created new opportunities for mental health interventions. Mobile health (mHealth) applications, web-based cognitive behavioral therapy (CBT), and digital therapeutics represent a rapidly growing field...\n\nMethods\n\nWe conducted a systematic search of PubMed, PsycINFO, and Cochrane databases for randomized controlled trials published between 2010 and 2023. Inclusion criteria required studies to evaluate digital interventions for depression or anxiety...\n\nResults\n\nOf 3,421 articles screened, 127 met inclusion criteria. Digital CBT showed the strongest evidence base with an average effect size of d=0.73 for depression and d=0.67 for anxiety. Smartphone-based interventions demonstrated moderate effects (d=0.45-0.52) with higher engagement rates than web-based platforms...\n\nDiscussion\n\nDigital health interventions offer scalable solutions for mental health treatment gaps. However, challenges remain regarding engagement, personalization, and integration with traditional care models...",
            },
            {
                "title": "Barriers to Digital Health Adoption in Elderly Populations: A Mixed-Methods Study",
                "authors": ["Michael Chen", "Sarah Williams", "Robert Brown"],
                "year": 2024,
                "journal": "Journal of Medical Internet Research",
                "volume": "26",
                "issue": "2",
                "pages": "e45678",
                "doi": "10.2196/45678",
                "abstract": "Understanding barriers to digital health adoption among elderly populations is crucial for equitable healthcare delivery. This mixed-methods study combines survey data from 2,500 adults aged 65+ with qualitative interviews from 150 participants. Key barriers identified include technological literacy (67%), privacy concerns (54%), lack of perceived benefit (43%), and physical/cognitive limitations (38%). Facilitators included family support, simplified interfaces, and integration with existing care.",
                "full_text": "Background\n\nThe digital divide in healthcare disproportionately affects elderly populations, potentially exacerbating health disparities. As healthcare systems increasingly adopt digital solutions, understanding adoption barriers becomes critical...\n\nObjective\n\nThis study aims to identify and quantify barriers to digital health technology adoption among adults aged 65 and older, and to explore potential facilitators for increased engagement...\n\nMethods\n\nWe employed a sequential explanatory mixed-methods design. Phase 1 involved a nationally representative survey of 2,500 older adults. Phase 2 consisted of semi-structured interviews with 150 participants selected through purposive sampling...\n\nResults\n\nTechnological literacy emerged as the primary barrier, with 67% reporting difficulty navigating digital interfaces. Privacy and security concerns affected 54% of respondents, particularly regarding health data sharing. Perceived lack of benefit was cited by 43%, often due to preference for in-person care...\n\nConclusions\n\nAddressing digital health adoption barriers requires multi-faceted approaches including user-centered design, digital literacy programs, and hybrid care models that maintain human connection while leveraging technology benefits...",
            },
            {
                "title": "Artificial Intelligence in Clinical Decision Support: A Systematic Review of Diagnostic Accuracy",
                "authors": ["Emily Zhang", "David Martinez", "Lisa Anderson"],
                "year": 2023,
                "journal": "The Lancet Digital Health",
                "volume": "5",
                "issue": "8",
                "pages": "e523-e535",
                "doi": "10.1016/S2589-7500(23)00089-0",
                "abstract": "AI-based clinical decision support systems (CDSS) show promising diagnostic accuracy across multiple medical specialties. This systematic review analyzed 89 studies comparing AI diagnostic performance to clinical experts. In radiology, AI achieved 94.5% sensitivity and 95.3% specificity for detecting malignancies. Dermatology applications showed 91.2% accuracy for skin cancer detection. However, real-world implementation faces challenges including algorithm bias, interpretability, and integration with clinical workflows.",
                "full_text": "Introduction\n\nArtificial intelligence has emerged as a transformative technology in healthcare, particularly in diagnostic imaging and pattern recognition. This systematic review evaluates the current state of AI diagnostic accuracy across clinical specialties...\n\nMethods\n\nWe searched MEDLINE, Embase, and IEEE Xplore for studies published between 2018 and 2023 comparing AI diagnostic performance to human experts or established diagnostic standards. Quality assessment used QUADAS-2 criteria...\n\nResults\n\nRadiology applications dominated the literature (n=42 studies), with deep learning models achieving expert-level performance in chest X-ray interpretation (AUC 0.94), mammography (AUC 0.92), and CT lung nodule detection (sensitivity 94.5%). Dermatology studies (n=18) showed comparable accuracy to dermatologists for melanoma detection...\n\nChallenges and Limitations\n\nDespite impressive accuracy metrics, several challenges impede clinical translation. Dataset bias remains problematic, with most training data from high-resource settings. Algorithmic interpretability is limited, creating trust barriers among clinicians...\n\nConclusions\n\nAI demonstrates diagnostic accuracy comparable to or exceeding human experts in specific domains. Successful implementation requires addressing technical, ethical, and workflow integration challenges...",
            },
            {
                "title": "Telemedicine Effectiveness During COVID-19: A Global Meta-Analysis",
                "authors": ["James Wilson", "Maria Garcia", "Thomas Lee"],
                "year": 2023,
                "journal": "BMJ Global Health",
                "volume": "8",
                "issue": "4",
                "pages": "e011234",
                "doi": "10.1136/bmjgh-2023-011234",
                "abstract": "The COVID-19 pandemic accelerated telemedicine adoption globally. This meta-analysis of 156 studies across 42 countries evaluates telemedicine effectiveness for various conditions during 2020-2023. Patient satisfaction rates averaged 86%, with no significant differences in clinical outcomes compared to in-person care for chronic disease management. Cost savings averaged 23% per consultation. However, disparities in access persisted, particularly in low-resource settings.",
                "full_text": "Introduction\n\nThe COVID-19 pandemic necessitated rapid healthcare delivery transformation, with telemedicine emerging as a critical tool for maintaining care continuity. This meta-analysis synthesizes global evidence on telemedicine effectiveness during the pandemic period...\n\nMethods\n\nWe conducted a comprehensive search of multiple databases for studies evaluating telemedicine interventions during COVID-19 (March 2020 - March 2023). Random-effects meta-analysis was performed for clinical outcomes, patient satisfaction, and cost-effectiveness...\n\nResults\n\nFrom 4,567 articles screened, 156 studies met inclusion criteria, representing 2.3 million patients across 42 countries. Chronic disease management via telemedicine showed non-inferior outcomes for diabetes (HbA1c difference: -0.08%, 95% CI: -0.15 to -0.01), hypertension (systolic BP difference: -1.2 mmHg, 95% CI: -2.4 to 0.1), and mental health conditions...\n\nPatient Experience\n\nPatient satisfaction rates were high across regions (mean 86%, range 71-94%). Key satisfaction drivers included convenience (92%), reduced travel time (89%), and maintained care quality (78%). Dissatisfaction related to technical difficulties (31%) and lack of physical examination (28%)...\n\nConclusions\n\nTelemedicine proved effective for maintaining healthcare delivery during COVID-19, with outcomes comparable to traditional care for many conditions. Post-pandemic integration should address equity concerns and optimize hybrid care models...",
            },
            {
                "title": "Wearable Devices for Continuous Health Monitoring: Clinical Validation and Real-World Evidence",
                "authors": ["Kevin Park", "Jennifer White", "Christopher Davis"],
                "year": 2024,
                "journal": "npj Digital Medicine",
                "volume": "7",
                "issue": "1",
                "pages": "45",
                "doi": "10.1038/s41746-024-01012-z",
                "abstract": "Consumer wearable devices increasingly claim health monitoring capabilities, but clinical validation remains inconsistent. This study evaluated 25 popular wearables against medical-grade equipment for heart rate, blood oxygen, and activity tracking. While heart rate monitoring showed excellent accuracy (r=0.96), SpO2 measurements varied significantly (r=0.72-0.89). Real-world data from 10,000 users revealed high engagement initially (82%) declining to 34% at 6 months, highlighting adherence challenges.",
                "full_text": "Introduction\n\nThe wearable device market has expanded rapidly, with manufacturers increasingly positioning products as health monitoring tools. This study provides comprehensive clinical validation of consumer wearables and analyzes real-world usage patterns...\n\nMethods\n\nPhase 1: Laboratory validation compared 25 consumer wearables (smartwatches, fitness trackers, rings) against gold-standard medical devices. Measurements included heart rate, SpO2, sleep stages, and physical activity. Phase 2: Prospective cohort study followed 10,000 users for 12 months, tracking engagement patterns and health outcomes...\n\nValidation Results\n\nHeart rate monitoring demonstrated excellent agreement with ECG (mean absolute error: 2.3 bpm, r=0.96). Performance was consistent across activities except high-intensity exercise (MAE: 5.7 bpm). SpO2 accuracy varied by device, with newer models showing improved performance (r=0.89 vs 0.72 for older generations)...\n\nReal-World Engagement\n\nInitial engagement was high (82% daily use in month 1) but declined significantly over time. At 6 months, only 34% maintained daily use. Factors associated with sustained engagement included goal setting (OR 2.3), social features (OR 1.8), and health condition monitoring (OR 3.1)...\n\nClinical Implications\n\nWhile wearables show promise for continuous monitoring, clinical integration requires careful consideration of accuracy limitations and engagement sustainability. Hybrid models combining wearable data with periodic clinical validation may optimize outcomes...",
            },
        ]

        self.build_from_papers(demo_papers)


@click.command()
@click.option(
    "--demo", is_flag=True, help="Build demo knowledge base with sample papers"
)
@click.option(
    "--api-url", help="Custom Zotero API URL (e.g., http://host.docker.internal:23119/api for WSL)"
)
@click.option(
    "--knowledge-base-path", default="kb_data", help="Path to knowledge base directory"
)
def main(demo, api_url, knowledge_base_path):
    """Build knowledge base for research assistant.
    
    By default, connects to local Zotero library via HTTP API.
    Requires Zotero to be running with 'Allow other applications' enabled.
    
    For WSL users with Zotero on Windows host, the API URL will be auto-detected.
    """
    builder = KnowledgeBaseBuilder(knowledge_base_path)

    if demo:
        print("Building demo knowledge base...")
        builder.build_demo_kb()
    else:
        # Auto-detect WSL environment and Windows host IP if no API URL provided
        if not api_url:
            # Check if we're in WSL
            try:
                with open("/proc/version", "r") as f:
                    if "microsoft" in f.read().lower():
                        # We're in WSL, get Windows host IP
                        import subprocess
                        result = subprocess.run(
                            ["cat", "/etc/resolv.conf"], 
                            capture_output=True, 
                            text=True
                        )
                        for line in result.stdout.split('\n'):
                            if 'nameserver' in line:
                                host_ip = line.split()[1]
                                api_url = f"http://{host_ip}:23119/api"
                                print(f"Detected WSL environment. Using Windows host at {host_ip}")
                                break
            except Exception:
                pass
        
        print("Connecting to Zotero library...")
        if api_url:
            print(f"Using API URL: {api_url}")
        else:
            print("Using default: http://localhost:23119/api")
        
        print("Ensure Zotero is running and 'Allow other applications' is enabled in Advanced settings")
        
        try:
            builder.build_from_zotero_local(api_url)
        except ConnectionError as e:
            print(f"Error: {e}")
            print("\nTo enable local API access:")
            print("1. Open Zotero on your Windows host")
            print("2. Go to Edit > Settings > Advanced")
            print("3. Check 'Allow other applications on this computer to communicate with Zotero'")
            print("4. Restart Zotero if needed")
            if "WSL" in str(e) or "microsoft" in open("/proc/version").read().lower():
                print("\nFor WSL users:")
                print("- Ensure Windows Firewall allows connections on port 23119")
                print("- You may need to manually specify the API URL:")
                print("  python build_kb.py --api-url http://<windows-host-ip>:23119/api")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
