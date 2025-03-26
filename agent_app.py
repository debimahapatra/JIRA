import os
import streamlit as st
from langchain_anthropic import ChatAnthropic
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
import anthropic
import pandas as pd

from jira_utils import create_issue, search_issues, edit_issue, generate_epics_and_stories
import jira_utils

# Load .env
load_dotenv()

# Claude token workaround
def dummy_count_tokens(text):
    return len(text.split())
anthropic.Anthropic.count_tokens = dummy_count_tokens

# Streamlit config
st.set_page_config(page_title="Claude JIRA Agent", layout="wide")
st.title("🤖 Claude JIRA Agent")

# Tools
tools = [
    Tool.from_function(
        func=create_issue,
        name="CreateJiraIssue",
        description="Create a JIRA issue by passing project_key, summary, description, issue_type, parent_key as a single string."
    ),
    Tool.from_function(
        func=search_issues,
        name="SearchJiraIssues",
        description="Use this tool to search JIRA issues using a JQL query string. It returns real issue data."
    ),
    Tool.from_function(
        func=edit_issue,
        name="EditJiraIssue",
        description="Edit fields of a JIRA issue such as summary, description, status, or assignee."
    ),
    Tool.from_function(
        func=generate_epics_and_stories,
        name="GenerateEpicsAndStories",
        description=(
            "Use this to convert product or business requirements into epics and stories in JIRA.\n"
            "Input must be in this format: Project Key: <KEY>, Requirement: <requirement text>\n"
            "Example: Project Key: SCRUM, Requirement: The app should support onboarding, live match updates, and notifications."
        )
    )
]

# LLM
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    temperature=0.3,
    max_tokens=8192,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Check if memory exists in session_state, otherwise create it.
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

system_prompt = """
You are an AI assistant that can answer general knowledge queries and also manage JIRA tasks with the provided tools.
Use your memory to understand the conversation flow and recall past interactions.
If the user asks about JIRA, use the JIRA tools.
Otherwise, answer from your own knowledge.
"""


# Use the persisted memory when initializing your agent.
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    memory=st.session_state.memory,
    verbose=True,
    agent_kwargs={
        "system_message": system_prompt
    }
)

# Streamlit session memory
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Render old messages
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input box
user_input = st.chat_input("Ask me to create, search, or edit JIRA issues...")

if user_input:
    # Clear search results
    jira_utils.last_search_dataframe = pd.DataFrame()

    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            try:
                response = agent.run(user_input)

                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.markdown(response)

                if hasattr(jira_utils, "last_search_dataframe") and not jira_utils.last_search_dataframe.empty:
                    st.markdown("📊 Search Results:")
                    st.dataframe(jira_utils.last_search_dataframe)

            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                st.error(error_msg)
