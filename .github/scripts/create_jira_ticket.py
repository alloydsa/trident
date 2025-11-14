#!/usr/bin/env python3
"""
Script to create a Jira ticket from a GitHub issue.
Triggered by GitHub Actions when 'tracked' label is added.
"""

import os
import sys
import json
import requests
from base64 import b64encode
from time import sleep

def get_github_issue_body(issue_number, token, repo_name):
    """Fetch the full issue body from GitHub API."""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}'
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json().get('body', '')
    except Exception as e:
        print(f"⚠️  Failed to fetch issue body: {e}")
    
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
    
    # Fetch full issue body from GitHub
    issue_body = get_github_issue_body(issue_number, github_token, repo_name)
    
    # Prepare Jira authentication
    auth_string = f"{jira_email}:{jira_token}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/json'
    }
    
    # Determine issue type based on labels
    issue_type = 'Bug' if 'bug' in issue_labels else 'Task'
    
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
    
    # Create the Jira issue with retry logic
    api_url = f"{jira_url}/rest/api/2/issue"
    
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
                
                # Add comment to GitHub issue with Jira link
                repo_name = os.environ.get('GITHUB_REPOSITORY')
                add_github_comment(issue_number, jira_key, jira_issue_url, github_token, repo_name)
                
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

def add_github_comment(issue_number, jira_key, jira_url, github_token, repo_name):
    """Add a comment to the GitHub issue with the Jira ticket link."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    comment_body = f"📋 Jira ticket created: [{jira_key}]({jira_url})"
    
    url = f'https://api.github.com/repos/{repo_name}/issues/{issue_number}/comments'
    payload = {"body": comment_body}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 201:
            print(f"✅ Added comment to GitHub issue #{issue_number}")
        else:
            print(f"⚠️  Failed to add comment to GitHub issue (non-critical)")
    except Exception as e:
        print(f"⚠️  Failed to add comment to GitHub issue: {e} (non-critical)")

if __name__ == "__main__":
    issue_data = {
        'number': os.environ.get('ISSUE_NUMBER'),
        'title': os.environ.get('ISSUE_TITLE'),
        'url': os.environ.get('ISSUE_URL'),
        'author': os.environ.get('ISSUE_AUTHOR'),
        'labels': json.loads(os.environ.get('ISSUE_LABELS', '[]'))
    }
    
    create_jira_ticket(issue_data)
