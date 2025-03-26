# 🤖 JIRA AI Copilot

A ChatGPT-style Streamlit app powered by LangChain and Anthropic Claude that allows you to create, search, and edit JIRA issues using natural language.

---

## 🚀 Features
- Create JIRA issues (epics, stories, bugs, tasks) via chat
- Search JIRA issues using JQL
- Edit issue fields (summary, description, status, etc.)
- Memory-enabled chat with multi-turn understanding

---

## 📁 Project Structure

```
jira-ai-chatbot/
├── agent_app.py              # Streamlit + LangChain app
├── jira_utils.py             # JIRA API wrappers
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── tools/
    └── jira_tools.py         # LangChain tool wrappers
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/jira-ai-chatbot.git
cd jira-ai-chatbot
```

### 2. Create `.env` file
```bash
cp .env.example .env
```
Fill in your credentials:
- `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- `CLAUDE_API_KEY` (from Anthropic)

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
streamlit run agent_app.py
```

---

## 🧠 Example Prompts
- "Create a new bug in project ABC with title 'Login fails on Safari'"
- "Search all open issues assigned to me last week"
- "Update the description of issue ABC-123 to include error stack trace"

---

## 🛠 Tech Stack
- [Streamlit](https://streamlit.io/)
- [LangChain](https://www.langchain.com/)
- [Anthropic Claude 3](https://www.anthropic.com/)
- [Atlassian JIRA](https://www.atlassian.com/software/jira)

---

## 📬 License / Contribution
Open to contributions!
