# jira_utils.py

from jira import JIRA
import os
import pandas as pd
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

jira = JIRA(
    server=os.getenv("JIRA_URL"),
    basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
)

# Global holders for table display
last_search_data = []
last_search_dataframe = pd.DataFrame()

def create_issue(raw_input: str):
    import re

    # Try key=value format first
    if "=" in raw_input:
        pattern = re.compile(r"(\w+)=([^,]+)")
        fields = dict(pattern.findall(raw_input))

        project_key = fields.get("project_key", "").strip()
        summary = fields.get("summary", "").strip()
        description = fields.get("description", "").strip()
        issue_type = fields.get("issue_type", "Task").strip()
        parent_key = fields.get("parent_key")
    else:
        # Fallback: comma-separated
        parts = [p.strip() for p in raw_input.split(",")]
        project_key = parts[0] if len(parts) > 0 else ""
        summary = parts[1] if len(parts) > 1 else ""
        description = parts[2] if len(parts) > 2 else ""
        issue_type = parts[3] if len(parts) > 3 else "Task"
        parent_key = None

    # ✅ Validate project key
    if not project_key or not project_key.isalpha():
        return "❌ Missing or invalid `project_key`. Please specify a valid JIRA project like `SCRUM`, `CRIC`, etc."

    if not all([summary, description]):
        return "❌ Missing required fields: `summary` or `description`."

    issue_dict = {
        "project": {"key": project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type}
    }

    if parent_key:
        issue_dict["parent"] = {"key": parent_key}

    new_issue = jira.create_issue(fields=issue_dict)
    return f"✅ Created issue [{new_issue.key}]({new_issue.permalink()}) in project {project_key}."


def edit_issue(raw_input: str):
    import re

    # Attempt to split by comma first
    parts = [p.strip() for p in raw_input.split(",")]

    if len(parts) == 3:
        issue_key, field, value = parts

    elif len(parts) == 2 and "=" in parts[1]:
        # Support fallback format like: SCRUM-522, parent=SCRUM-525
        field_part = parts[1]
        field_match = re.match(r"([\w\-]+)\s*=\s*(.+)", field_part)
        if field_match:
            issue_key = parts[0]
            field, value = field_match.groups()
        else:
            raise ValueError("Unrecognized format. Use: ISSUE-KEY, field, value")
    else:
        raise ValueError("Invalid format. Use: ISSUE-KEY, field, value (e.g. SCRUM-522, parent, SCRUM-525)")

    # Handle known field quirks
    if field == "labels":
        value = [v.strip() for v in value.split(",")]
    elif field == "parent":
        value = {"key": value.strip()}

    # Perform the update
    issue = jira.issue(issue_key)
    issue.update(fields={field: value})

    return f"✅ Updated `{field}` of {issue_key} to:\n\n{value}"


def search_issues(jql_query):
    global last_search_data, last_search_dataframe

    try:
        issues = jira.search_issues(jql_query)
        if not issues:
            last_search_data = []
            last_search_dataframe = pd.DataFrame()
            return "No issues found."

        last_search_data = [
            {
                "Key": issue.key,
                "Summary": issue.fields.summary,
                "Status": issue.fields.status.name,
                "Assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "Type": issue.fields.issuetype.name,
                "Priority": issue.fields.priority.name if issue.fields.priority else "None"
            }
            for issue in issues
        ]

        last_search_dataframe = pd.DataFrame(last_search_data)
        return f"Found {len(last_search_data)} issues for query: `{jql_query}`. Table will appear below."

    except Exception as e:
        return f"❌ Error fetching JIRA issues: {str(e)}"


def generate_epics_and_stories(input_text: str):
    from jira import JIRAError
    import json
    import re
    import os
    from langchain_anthropic import ChatAnthropic

    # Call Claude
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20240620",
        temperature=0.3,
        max_tokens=4096,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    # Extract the project key and requirement text from the input.
    # Expected format: "Project Key: <PROJECT_KEY>, Requirement: <REQUIREMENT_TEXT>"
    match = re.match(r"Project Key:\s*(\w+)\s*,\s*Requirement:\s*(.*)", input_text, re.DOTALL)
    if not match:
        return "❌ Input format incorrect. Please provide input as 'Project Key: <KEY>, Requirement: <requirement>'"

    project_key = match.group(1).strip()
    requirement_text = match.group(2).strip()

    # Claude prompt with strict instructions for JSON-only output.
    prompt = f"""
You are a product analyst. Given the business requirement below, break it down into a structured list of epics and user stories.
Return ONLY a valid JSON array with no additional text or commentary.
The JSON must follow this exact format:
[
  {{
    "epic": "Epic Title",
    "epic description": "Epic Description:....... \n Acceptance Criteria:......",
    "stories": ["Story 1", "Story 2"]
  }},
  ...
]

Requirement:
{requirement_text}
"""
    # Call Claude
    '''llm = ChatAnthropic(
        model="claude-3-5-sonnet-20240620",
        temperature=0.3,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )'''
    response_obj = llm.invoke(prompt)

    # If response_obj is a Message-like object, extract its content as a string
    if hasattr(response_obj, "content"):
        response_str = response_obj.content
    else:
        # If it's already a string, just cast to string
        response_str = str(response_obj)

    # Try to parse the response as JSON
    try:
        epics_and_stories = json.loads(response_str)
    except Exception:
        # Attempt to extract JSON content between the first '[' and the last ']'
        start = response_str.find('[')
        end = response_str.rfind(']') + 1
        if start != -1 and end != -1:
            try:
                epics_and_stories = json.loads(response_str[start:end])
            except Exception:
                return f"❌ Failed to parse extracted JSON:\n{response_str}"
        else:
            return f"❌ Failed to locate JSON in response:\n{response_str}"

    if not isinstance(epics_and_stories, list):
        return f"❌ Claude returned an unexpected format:\n{response_str}"

    # Create epics & stories in JIRA
    from jira_utils import jira  # or wherever you import JIRA
    results = []

    for item in epics_and_stories:
        epic_title = item["epic"]
        #epic_desc = f"Auto-generated epic from requirement: {requirement_text}"
        epic_desc = item["epic description"]

        # Create Epic using the extracted project key
        epic_issue = jira.create_issue(fields={
            "project": {"key": project_key},
            "summary": epic_title,
            "description": epic_desc,
            "issuetype": {"name": "Epic"}
        })
        results.append(f"🟣 Epic created: {epic_issue.key} - {epic_title}")

######################
        prompt_story = f"""
    You are a product analyst. Given the business requirement below, break it down into a structured list of user stories for the concerned epics.
    Return ONLY a valid JSON array with no additional text or commentary.
    The JSON must follow this exact format:
    [
    {{
        "summary": "Story Title",
        "description": "Story Description:....... \n Acceptance Criteria:......"
    }},
    ...
    ]

    Concerned Parent Epic Name: {epic_title}
    Concerned Parent Epic Description: {epic_desc}

    Requirement:
    {requirement_text}
    """
        # Call Claude
        response_obj_story = llm.invoke(prompt_story)

        # If response_obj_story is a Message-like object, extract its content as a string
        if hasattr(response_obj_story, "content"):
            response_str_story = response_obj_story.content
        else:
            # If it's already a string, just cast to string
            response_str_story = str(response_obj_story)

        # Try to parse the response as JSON
        try:
            stories = json.loads(response_str_story)
            print(stories)
        except Exception:
            # Attempt to extract JSON content between the first '[' and the last ']'
            start = response_str_story.find('[')
            end = response_str_story.rfind(']') + 1
            if start != -1 and end != -1:
                try:
                    stories = json.loads(response_str_story[start:end])
                    print(stories)
                except Exception:
                    return f"❌ Failed to parse extracted JSON:\n{response_str_story}"
            else:
                return f"❌ Failed to locate JSON in response:\n{response_str_story}"

        if not isinstance(stories, list):
            return f"❌ Claude returned an unexpected format:\n{response_str_story}"
######################

        # Create stories linked to the epic
        for story in stories:
            story_title = story["summary"]
            story_desc = story["description"]
            story_issue = jira.create_issue(fields={
                "project": {"key": project_key},
                "summary": story_title,
                "description": story_desc,
                "issuetype": {"name": "Story"},
                "parent": {"key": epic_issue.key},
            })
            results.append(f"🟢 Story created: {story_issue.key} - linked to {epic_issue.key}")

    return "\n".join(results)


