#  OrbitAI Multi-Agent Assistant

OrbitAI Multi-Agent Assistant is an AI-powered automation platform built with Python and local Large Language Models (LLMs). The system is composed of four specialized agents that collaborate to analyze emails, qualify business opportunities, generate professional responses, and assist with meeting planning.

##  Features

-  **Email Analysis Agent**
  - Connects to Gmail using the Gmail API
  - Reads recent emails
  - Classifies email priority
  - Categorizes incoming messages
  - Generates concise summaries
  - Suggests the next action

-  **Commercial Agent**
  - Identifies potential customers
  - Qualifies business opportunities
  - Recommends relevant Orbit products
  - Uses pricing and product knowledge bases

-  **Reply Agent**
  - Generates professional email replies
  - Adapts responses based on the email context
  - Produces clear and business-friendly communication

-  **Planning Agent**
  - Assists with meeting scheduling
  - Uses calendar configuration
  - Suggests available meeting times


##  Technologies

- Python 3.x
- Ollama
- Qwen LLM
- Gmail API
- Google OAuth2
- PyYAML
- JSON

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/majda-soussia/OrbitAI-MultiAgent.git
```

Move into the project directory:

```bash
cd OrbitAI-MultiAgent
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

##  Configuration

Create the following configuration files inside the `config/` folder:

- `credentials.json`
- `token.json`
- `gmail.yaml`
- `calendar.yaml`
- `llm.yaml`

> **Note:** OAuth credentials and tokens are intentionally excluded from this repository for security reasons.

---

##  Run

```bash
python main.py
```

---

##  Security

This repository does **not** include:

- Google OAuth credentials
- Gmail access tokens
- API keys
- Sensitive configuration files

Please create your own credentials before running the application.

---

##  Future Improvements

- CRM integration
- Calendar synchronization
- Retrieval-Augmented Generation (RAG)
- Long-term memory
- Multi-agent orchestration
- Web dashboard
- Docker support
- REST API

---

##  Author

**Majda Soussia**

AI & Software Engineering Student

---

## 📄 License

This project is intended for educational and research purposes.
