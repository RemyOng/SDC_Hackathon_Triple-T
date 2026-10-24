
---

# Orbyte GreenReady

> From Bills to Better Business, For SME

---

## Team Information

| Field                  | Details                                     
| ---------------------- | ------------------------------------------- 
| **Team Name**          | Remy Ong Jing Yi                             
| **Team Domain**        | Domain 2         
| **SDG Track (1–17)**   | SDG 8 - Decent Work and Economic Growth
| **Team Leader**        | Remy Ong Jing Yi                            
| **University**         | Asia Pacific University of Technology & Innovation                       
| **Number of Members**  | 3                              

## Links

| Resource          | Link                                           
| ----------------- | ---------------------------------------------- 
| GitHub Repository | https://github.com/RemyOng/SDC_Hackathon_Triple-T
| Live Demo         |                
| RunPod Endpoint   |    
| Slide Deck        |             
| Demo Video        |               

---

## Overview

### Problem

Describe the real-world problem you are solving in 2–4 sentences. Who is affected, and why does it matter?

### Solution

Explain how your project uses AI to solve the problem and what makes it valuable.

### Key Features

- **Feature 1** — Short description.
- **Feature 2** — Short description.
- **Feature 3** — Short description.

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | e.g. HTML, React             |
| Backend       | e.g. Python, Flask / FastAPI |
| Database      | e.g. PostgreSQL, SQLite      |
| AI / Compute  | RunPod (GPU)                 |
| Hosting / Dev | Replit                       |

---

## Project Structure

```
.
├── docs/                    # Screenshots, diagrams
├── runpod/
│   └── handler.py           # RunPod serverless handler (GPU workload)
├── src/
│   ├── main.py              # Application entry point
│   └── utils.py             # Helper functions
├── submission/              # Required submission documents
│   ├── SDC2026_TeamName_Preliminary.pdf      # Preliminary submission
│   ├── SDC2026_TeamName_TechDeclaration.pdf  # Technology declaration
│   ├── SDC2026_TeamName_Replit_POU.pdf       # Replit proof of use
│   └── SDC2026_TeamName_Runpod_POU.pdf       # RunPod proof of use
├── tests/
│   └── test_utils.py        # Unit tests
├── .env.example             # Example environment variables
├── .gitignore
├── .replit                  # Replit run configuration
├── LICENSE
├── requirements.txt         # Python dependencies
└── README.md
```

### Architecture

```
User ──► Replit (App / API) ──► RunPod Endpoint (GPU model)
                │
                └──► Response returned to user
```

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the [Replit Project](https://replit.com/@your-username/your-project), or import this repository via **Create Repl → Import from GitHub**.
2. Open the **Secrets** tab (🔒) and add the variables listed in `.env.example`:
   - `RUNPOD_API_KEY`
   - `RUNPOD_ENDPOINT_ID`
3. Click **Run** and start the app with `python src/main.py` from the repository root.

The Python application and frontend source are in `src/`. Keep `requirements.txt`,
`.env`, `credentials.json`, and `token.json` in the repository root. The app
loads those root-level files from the code location, so the launch directory
does not change where it looks for configuration or Gmail OAuth credentials.

### Option 2 — Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/your-username/your-project.git
cd your-project

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables in the repository-root .env file
#    (copy the variables from your deployment secrets)

# 5. Run the app
python src/main.py
```

### Run Tests

```bash
PYTHONPATH=src python -m unittest discover tests
```

---

## How We Use Replit *(Required)*

Describe how your team used Replit. For example:

- **Development:** Collaborative coding in a shared Repl using Multiplayer.
- **Hosting:** The app is deployed with Replit Deployments at the Live Demo link above.
- **Secrets:** API keys are stored in Replit Secrets, never in the code.

📄 Proof of use: [`submission/SDC2026_TeamName_Replit_POU.pdf`](submission/SDC2026_TeamName_Replit_POU.pdf)

## How We Use RunPod *(Required)*

Describe how your team used RunPod. For example:

- **Workload:** Model inference (e.g. text generation, image processing) runs on a RunPod GPU.
- **Setup:** `runpod/handler.py` is deployed as a **RunPod Serverless Endpoint**.
- **Integration:** The Replit app sends requests to the endpoint using `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`.

Example request:

```bash
curl -X POST https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "Hello"}}'
```

📄 Proof of use: [`submission/SDC2026_TeamName_Runpod_POU.pdf`](submission/SDC2026_TeamName_Runpod_POU.pdf)

---

## Challenges & Learnings

- What challenges did you face, and how did you overcome them?
- What did your team learn?

## Future Improvements

- [ ] Improvement 1
- [ ] Improvement 2

## Team

| Name        | Role                | GitHub                                   |
| ----------- | ------------------- | ---------------------------------------- |
| Remy Ong Jing Yi | Team Lead / Backend / Frontend | [@RemyOng](https://github.com/RemyOng) |
| Saeed Omar Abdulrahman | Backend / Replit + Runpod         | [@Omar-Saeed-OASS](https://github.com/Omar-Saeed-OASS) |
| Chua Pei Ying | Frontend / Business        | [@Peiying](https://github.com/Pyyp0409) |

---

## Submission Checklist

- [✓] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [✓] Slide deck link added
- [✓] Demo video link added
- [✓] Replit used, with proof of use in `submission/`
- [✓] RunPod used, with proof of use in `submission/`
- [✓] Preliminary submission completed (`SDC2026_TeamName_Preliminary.pdf`)
- [✓] Technology declaration completed (`SDC2026_TeamName_TechDeclaration.pdf`)
- [✓] Submission files renamed with your team name (replace `TeamName`)
- [✓] "How to Run" steps verified
- [✓] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
