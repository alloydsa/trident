#!/usr/bin/env python3
"""
Script to sync GitHub issues with Jira.
Supports: creating tickets, syncing comments, and syncing status.
"""

import argparse
import json
import os
import sys
from base64 import b64encode

import requests


def get_github_issue_body(issue_number, token, repo_name):
    """Fetch the full issue body from GitHub API."""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('body', '')
    return ''

def create_jira_ticket(issue_data):
    """Create a Jira ticket from GitHub issue data."""
    
    # Get environment variables
    jira_url = os.environ.get('JIRA_URL')
    jira_email = os.environ.get('JIRA_EMAIL')
    jira_token = os.environ.get('JIRA_API_TOKEN')
    project_key = os.environ.get('JIRA_PROJECT_KEY', 'TRID')
    epic_key = os.environ.get('JIRA_EPIC_KEY')  # Optional
    github_token = os.environ.get('GITHUB_TOKEN')
    
    issue_number = os.environ.get('ISSUE_NUMBER')
    issue_title = os.environ.get('ISSUE_TITLE')
    issue_url = os.environ.get('ISSUE_URL')
    issue_author = os.environ.get('ISSUE_AUTHOR')
    issue_labels = json.loads(os.environ.get('ISSUE_LABELS', '[]'))
    repo_name = os.environ.get('GITHUB_REPOSITORY')  # e.g., "alloydsa/trident"
    
    # Validate required variables
    if not all([jira_url, jira_email, jira_token, issue_number, issue_title, repo_name]):
        print("ERROR: Missing required environment variables")
        sys.exit(1)
    
    # Prepare headers for Jira authentication using Personal Access Token (PAT)
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/json'
    }
    
    # Check if ticket already exists for this GitHub issue
    search_jql = f'project = {project_key} AND summary ~ "trident#{issue_number}:"'
    search_url = f"{jira_url}/rest/api/2/search"
    search_params = {'jql': search_jql, 'maxResults': 1}
    
    try:
        search_response = requests.get(search_url, headers=headers, params=search_params, timeout=10)
        if search_response.status_code == 200:
            existing_issues = search_response.json().get('issues', [])
            if existing_issues:
                existing_key = existing_issues[0]['key']
                existing_url = f"{jira_url}/browse/{existing_key}"
                print(f"⚠️  Jira ticket already exists: {existing_key}")
                print(f"🔗 URL: {existing_url}")
                return existing_key
    except Exception as e:
        print(f"⚠️  Could not check for existing tickets: {e}")
        # Continue with creation anyway
    
    # Fetch full issue body from GitHub
    issue_body = get_github_issue_body(issue_number, github_token, repo_name)
    
    # Determine issue type based on labels
    if 'bug' in issue_labels:
        issue_type = 'Bug'
    elif 'enhancement' in issue_labels:
        issue_type = 'Story'
    else:
        print("⚠️ Issue does not have 'bug' or 'enhancement' label. Skipping Jira ticket creation.")
        sys.exit(0)
    
    # Format description similar to Tasktop
    description = f"{issue_body}\n\n==== ^^ GitHub initial comment ^^ ====\n\nGitHub Issue: {issue_url}\nAuthor: {issue_author}"
    
    # Prepare Jira issue payload
    jira_payload = {
        "fields": {
            "project": {
                "key": project_key
            },
            "summary": f"trident#{issue_number}: {issue_title}",
            "description": description,
            "issuetype": {
                "name": issue_type
            },
            "labels": ["github-issue"] + [label for label in issue_labels if label != 'tracked']
        }
    }
    
    # Add epic link if provided
    if epic_key:
        # Note: The field name for Epic Link varies by Jira instance
        # Common field names: customfield_10008, customfield_10014, etc.
        # You may need to adjust this based on your Jira configuration
        jira_payload["fields"]["customfield_10008"] = epic_key
    
    # Create the Jira issue
    api_url = f"{jira_url}/rest/api/2/issue"
    response = requests.post(api_url, headers=headers, json=jira_payload)
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"Creating Jira ticket (attempt {attempt + 1}/{max_retries})...")
            response = requests.post(
                api_url, 
                headers=headers, 
                json=jira_payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                jira_issue = response.json()
                jira_key = jira_issue.get('key')
                jira_issue_url = f"{jira_url}/browse/{jira_key}"
                
                print(f"✅ Successfully created Jira ticket: {jira_key}")
                print(f"🔗 URL: {jira_issue_url}")
                
                return jira_key
            else:
                print(f"❌ Failed to create Jira ticket")
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    sys.exit(1)
                    
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            print(f"⚠️  Network error on attempt {attempt + 1}: {type(e).__name__}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"❌ Failed after {max_retries} attempts")
                print(f"Error: {str(e)}")
                sys.exit(1)


def find_jira_ticket(jira_url, headers, project_key, issue_number):
    """Find the Jira ticket for a GitHub issue."""
    search_jql = f'project = {project_key} AND summary ~ "trident#{issue_number}:"'
    search_url = f"{jira_url}/rest/api/2/search"
    search_params = {'jql': search_jql, 'maxResults': 1}
    
    try:
        response = requests.get(search_url, headers=headers, params=search_params, timeout=10)
        if response.status_code == 200:
            issues = response.json().get('issues', [])
            if issues:
                return issues[0]
    except Exception as e:
        print(f"❌ Failed to find Jira ticket: {e}")
    
    return None


def sync_comment_to_jira():
    """Sync a GitHub comment to Jira."""
    jira_url = os.environ.get('JIRA_URL')
    jira_pat = os.environ.get('JIRA_PAT')
    project_key = os.environ.get('JIRA_PROJECT_KEY', 'TRID')
    
    issue_number = os.environ.get('ISSUE_NUMBER')
    comment_body = os.environ.get('COMMENT_BODY')
    comment_author = os.environ.get('COMMENT_AUTHOR')
    comment_url = os.environ.get('COMMENT_URL')
    
    if not all([jira_url, jira_pat, issue_number, comment_body]):
        print("ERROR: Missing required environment variables for comment sync")
        sys.exit(1)
    
    headers = {
        'Authorization': f'Bearer {jira_pat}',
        'Content-Type': 'application/json'
    }
    
    print(f"Looking for Jira ticket for GitHub issue #{issue_number}...")
    jira_issue = find_jira_ticket(jira_url, headers, project_key, issue_number)
    
    if not jira_issue:
        print(f"⚠️ No Jira ticket found for issue #{issue_number}. Skipping comment sync.")
        return
    
    jira_key = jira_issue['key']
    print(f"Found Jira ticket: {jira_key}")
    
    # Format comment
    formatted_comment = f"*Comment from GitHub by {comment_author}:*\n\n{comment_body}\n\n----\n[View on GitHub|{comment_url}]"
    
    # Add comment to Jira
    api_url = f"{jira_url}/rest/api/2/issue/{jira_key}/comment"
    payload = {"body": formatted_comment}
    
    for attempt in range(3):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code in [200, 201]:
                print(f"✅ Comment added to Jira ticket {jira_key}")
                return
            else:
                print(f"⚠️ Failed to add comment (attempt {attempt + 1})")
                if attempt < 2:
                    sleep(2 * (attempt + 1))
        except Exception as e:
            print(f"⚠️ Network error: {e}")
            if attempt < 2:
                sleep(2 * (attempt + 1))
    
    print(f"❌ Failed to sync comment after retries")


def sync_status_to_jira():
    """Sync GitHub issue status to Jira."""
    jira_url = os.environ.get('JIRA_URL')
    jira_pat = os.environ.get('JIRA_PAT')
    project_key = os.environ.get('JIRA_PROJECT_KEY', 'TRID')
    
    issue_number = os.environ.get('ISSUE_NUMBER')
    action = os.environ.get('ACTION')
    
    if not all([jira_url, jira_pat, issue_number, action]):
        print("ERROR: Missing required environment variables for status sync")
        sys.exit(1)
    
    headers = {
        'Authorization': f'Bearer {jira_pat}',
        'Content-Type': 'application/json'
    }
    
    print(f"Looking for Jira ticket for GitHub issue #{issue_number}...")
    jira_issue = find_jira_ticket(jira_url, headers, project_key, issue_number)
    
    if not jira_issue:
        print(f"⚠️ No Jira ticket found for issue #{issue_number}. Skipping status sync.")
        return
    
    jira_key = jira_issue['key']
    current_status = jira_issue['fields']['status']['name']
    print(f"Found Jira ticket: {jira_key} (Current status: {current_status})")
    
    # Get available transitions
    trans_url = f"{jira_url}/rest/api/2/issue/{jira_key}/transitions"
    try:
        response = requests.get(trans_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Failed to get transitions")
            return
        transitions = response.json().get('transitions', [])
    except Exception as e:
        print(f"❌ Error getting transitions: {e}")
        return
    
    if not transitions:
        print(f"⚠️ No transitions available for {jira_key}")
        return
    
    print(f"Available transitions: {', '.join([t['name'] for t in transitions])}")
    
    # Determine target status
    if action == 'closed':
        target_names = ['done', 'closed', 'resolved', 'complete']
        comment = "GitHub issue was closed"
    elif action == 'reopened':
        target_names = ['reopen', 'to do', 'open', 'backlog']
        comment = "GitHub issue was reopened"
    else:
        print(f"⚠️ Unknown action: {action}")
        return
    
    # Find transition
    transition_id = None
    target_status = None
    for transition in transitions:
        to_status = transition.get('to', {}).get('name', '').lower()
        for target in target_names:
            if target.lower() in to_status:
                transition_id = transition['id']
                target_status = transition['to']['name']
                break
        if transition_id:
            break
    
    if not transition_id:
        print(f"⚠️ No suitable transition found for action '{action}'")
        return
    
    print(f"Transitioning {jira_key} to '{target_status}'...")
    
    # Perform transition
    api_url = f"{jira_url}/rest/api/2/issue/{jira_key}/transitions"
    payload = {
        "transition": {"id": transition_id},
        "update": {"comment": [{"add": {"body": comment}}]}
    }
    
    for attempt in range(3):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.status_code in [200, 204]:
                print(f"✅ Successfully updated {jira_key} status to '{target_status}'")
                return
            else:
                print(f"⚠️ Failed to transition (attempt {attempt + 1}): {response.status_code}")
                if attempt < 2:
                    sleep(2 * (attempt + 1))
        except Exception as e:
            print(f"⚠️ Network error: {e}")
            if attempt < 2:
                sleep(2 * (attempt + 1))
    
    print(f"❌ Failed to update status after retries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sync GitHub issues with Jira')
    parser.add_argument('--sync-comment', action='store_true', help='Sync a comment to Jira')
    parser.add_argument('--sync-status', action='store_true', help='Sync issue status to Jira')
    args = parser.parse_args()
    
    if args.sync_comment:
        sync_comment_to_jira()
    elif args.sync_status:
        sync_status_to_jira()
    else:
        # Default: create Jira ticket
        issue_data = {
            'number': os.environ.get('ISSUE_NUMBER'),
            'title': os.environ.get('ISSUE_TITLE'),
            'url': os.environ.get('ISSUE_URL'),
            'author': os.environ.get('ISSUE_AUTHOR'),
            'labels': json.loads(os.environ.get('ISSUE_LABELS', '[]'))
        }
        create_jira_ticket(issue_data)
        create_jira_ticket(issue_data)
