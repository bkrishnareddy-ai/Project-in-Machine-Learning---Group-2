🧠 MemoriAI – AI-Powered Cognitive Assistant for Alzheimer’s Care
📘 Overview
MemoriAI is an AI-powered digital companion designed to support individuals with Alzheimer’s disease and dementia.
It provides cognitive recall assistance, adaptive reminders, and a caregiver dashboard—helping patients maintain independence and enabling caregivers to monitor well-being.
The system integrates FastAPI microservices, LangChain-based AI inference, SQLite + VectorDB storage, and GitHub Actions CI/CD pipelines deployed in Azure.
________________________________________
🧩 Key Features
•	🧠 Cognitive & Identity Assist – Personalized memory recall and word-aid service.
•	⏰ Daily Reminders & Safety Alerts – Smart reminders with adherence tracking.
•	📊 Caregiver Dashboard – Summaries, visual insights, and adherence metrics.
•	🔒 Security by Design – OAuth2 + JWT, RBAC, PHIPA/HIPAA compliance.
•	⚙️ Scalable Microservices – FastAPI, Docker, and Azure App Service deployment.
________________________________________
🏗️ System Architecture
The system follows a Service-Oriented Microservice Architecture with clear separation of concerns:
•	Frontend: Streamlit-based caregiver dashboard (web/mobile).
•	Backend: FastAPI-based services (Cognitive, Reminders, Dashboard).
•	Storage: SQLite (structured) + VectorDB (semantic memory).
•	AI Engine: LangChain + Guardrailed LLM for safe phrasing (no medical advice).
•	MLOps/DevOps: GitHub Actions → Docker → Azure Deployment → Monitoring (Grafana/Prometheus).
(See /docs/MemoriAI_Architecture_Overview_v3.docx for diagrams and design details.)
________________________________________
🧠 Core Microservices
Service	Purpose	Key Endpoint	Auth	Latency (p95)
Cognitive Service	Memory recall, word-aid, identity questions	/api/v1/cognitive/ask	JWT	< 800 ms
Reminder Service	Scheduling and reminders	/api/v1/reminder/create	JWT	< 500 ms
Dashboard Service	Caregiver insights & summaries	/api/v1/dashboard/summary	JWT	< 600 ms
________________________________________
🗂️ Repository Structure
MemoriAI/
│
├── src/                # Core application code
│   ├── cognitive/      # Cognitive service (FastAPI)
│   ├── reminders/      # Reminder service
│   ├── dashboard/      # Dashboard service
│   └── auth/           # OAuth2/JWT implementation
│
├── data/               # Datasets and embeddings
├── api/                # API routes and schemas
├── tests/              # Unit tests
├── docs/               # Design & architecture documents
│   ├── MemoriAI_HLD_v2_Advanced.docx
│   ├── MemoriAI_Architecture_Overview_v3.docx
│   └── MemoriAI_Highlevel_Design.docx
├── .github/workflows/  # GitHub Actions CI/CD pipelines
└── README.md           # You are here
________________________________________
⚙️ Setup Instructions
1. Clone the Repository
git clone https://github.com/<your-org>/MemoriAI.git
cd MemoriAI
2. Create Virtual Environment
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
3. Run the Services
uvicorn src.cognitive.main:app --reload --port 8001
uvicorn src.reminders.main:app --reload --port 8002
uvicorn src.dashboard.main:app --reload --port 8003
4. Access the APIs
•	Swagger UI: http://localhost:8001/docs
•	Dashboard UI: http://localhost:8501
________________________________________
🔗 Integration Links
•	Azure DevOps Board: https://dev.azure.com/.../MemoriAI_Project
•	GitHub Repository: https://github.com/.../MemoriAI
•	Approved Pull Request: PR #1 – Instructor Review
________________________________________
👥 Team Roles
Member	Role	Responsibilities
Tessa Nejla Ayvazoglu	AI Lead / Coordinator	Project coordination, cognitive module, final documentation
Krishna Reddy Bovilla	Backend Developer	Reminder & Auth microservices
Adhitya Kondeti	DevOps Engineer	Dockerization, CI/CD, Azure setup
Bhupender Sejwal	UI/UX & GitHub Lead	Repo setup, README, documentation, PR submission
Kumari Nikitha Singh	Frontend / Dashboard Developer	Streamlit dashboard, caregiver interface
________________________________________
✅ Pull Request (Instructor Review)
The instructor has been granted repository access and approved one Pull Request for evaluation purposes.
This PR contains the initial repository setup, folder structure, and README documentation.
________________________________________
🧩 Future Enhancements
•	Integration with wearable sensors for activity tracking
•	Voice-based recall assistant (Whisper / SpeechT5)
•	Predictive caregiver stress analytics
•	Multilingual support

## 👥 Team Members
- Tessa Ayvazoglu  
- Krishna Reddy Bovilla  
- Adhitya Kondeti  
- Bhupender Sejwal  
- Kumari Nikitha Singh

