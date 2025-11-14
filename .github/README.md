# GitHub to Jira Sync Automation

This directory contains the GitHub Actions workflow and scripts to automatically sync GitHub issues to Jira when the "tracked" label is added.

## Overview

When a user adds the `tracked` label to a GitHub issue, the workflow automatically:
1. Creates a corresponding Jira ticket in the specified project
2. Formats the ticket similar to Tasktop (with GitHub issue content and metadata)
3. Optionally links the ticket to an Epic
4. Adds a comment back to the GitHub issue with the Jira ticket link

## Setup Instructions

### 1. Configure GitHub Secrets

In your GitHub repository settings (Settings → Secrets and variables → Actions), add the following secrets:

#### Required Secrets:
- **`JIRA_URL`**: Your Jira instance URL (e.g., `https://jira.ngage.netapp.com`)
- **`JIRA_EMAIL`**: Email address for Jira authentication
- **`JIRA_API_TOKEN`**: Jira API token (create at: https://id.atlassian.com/manage-profile/security/api-tokens)
- **`JIRA_PROJECT_KEY`**: Jira project key (e.g., `TRID`)

#### Optional Secrets:
- **`JIRA_EPIC_KEY`**: Epic key to automatically link new tickets to (e.g., `TRID-10984`)

**Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### 2. Find Your Epic Link Custom Field

The Epic Link field ID varies by Jira instance. To find yours:

1. Go to your Jira instance
2. Open any issue in your project
3. Open browser DevTools (F12) → Network tab
4. Click "Edit" on the issue
5. Look for API calls to find the Epic Link field name (usually `customfield_10008` or similar)
6. Update line 103 in `.github/scripts/create_jira_ticket.py` with your field name

Alternatively, use the Jira API:
```bash
curl -u email@example.com:YOUR_API_TOKEN \
  https://jira.ngage.netapp.com/rest/api/2/field | grep -i epic
```

### 3. Test the Workflow

1. Push these files to your repository:
   ```bash
   git add .github/
   git commit -m "Add GitHub to Jira sync automation"
   git push
   ```

2. Create a test issue or use an existing one
3. Add the `tracked` label
4. Check the "Actions" tab in GitHub to see the workflow run
5. Verify the Jira ticket was created

## Files

- **`workflows/sync-issue-to-jira.yml`**: GitHub Actions workflow definition
- **`scripts/create_jira_ticket.py`**: Python script that creates the Jira ticket

## Features

### Automatic Detection
- Triggers only when the `tracked` label is added
- Fetches full issue content from GitHub API

### Jira Ticket Creation
- **Summary**: Formatted as `trident#{issue_number}: {issue_title}`
- **Description**: Full issue body + GitHub metadata (similar to Tasktop format)
- **Type**: Automatically sets to "Bug" if issue has `bug` label, otherwise "Task"
- **Labels**: Copies GitHub labels + adds `github-issue` label
- **Epic Link**: Optional automatic linking to specified Epic

### GitHub Integration
- Posts a comment on the GitHub issue with the Jira ticket link
- Example: "📋 Jira ticket created: [TRID-18758](https://jira.ngage.netapp.com/browse/TRID-18758)"

## Customization

### Change the Trigger Label
Edit `.github/workflows/sync-issue-to-jira.yml` line 10:
```yaml
if: github.event.label.name == 'your-custom-label'
```

### Modify Issue Type Logic
Edit `.github/scripts/create_jira_ticket.py` around line 74 to change how issue types are determined:
```python
# Current logic:
issue_type = 'Bug' if 'bug' in issue_labels else 'Task'

# Example alternatives:
issue_type = 'Story' if 'enhancement' in issue_labels else 'Bug' if 'bug' in issue_labels else 'Task'
```

### Add More Fields
Modify the `jira_payload` in the Python script to include additional Jira fields like priority, components, etc.

## Troubleshooting

### Workflow Doesn't Trigger
- Verify the workflow file is in the default branch (usually `main` or `master`)
- Check that Actions are enabled in repository settings
- Ensure you're adding the exact label name specified in the workflow

### Jira Authentication Fails
- Verify your Jira API token is valid
- Ensure your Jira email is correct
- Test authentication manually:
  ```bash
  curl -u email@example.com:YOUR_API_TOKEN \
    https://jira.ngage.netapp.com/rest/api/2/myself
  ```

### Epic Link Not Working
- Verify the Epic key exists and is accessible
- Check the custom field ID for Epic Link (see step 2 above)
- Some Jira instances require special permissions to link to Epics

### Workflow Runs But Fails
- Check the Actions tab in GitHub for detailed logs
- Look for error messages in the Python script output
- Verify all required secrets are configured

## Comparison with Tasktop

| Feature | Tasktop | This Solution |
|---------|---------|---------------|
| Trigger | Label addition | Label addition ✅ |
| Ticket Creation | Automatic | Automatic ✅ |
| Epic Linking | Yes | Yes ✅ |
| Bi-directional Sync | Yes | No (one-way only) |
| Comment Sync | Yes | Can be added |
| Status Sync | Yes | Can be added |
| Cost | Licensed | Free ✅ |
| Customization | Limited | Full control ✅ |

## Future Enhancements

Potential improvements you could add:

1. **Bidirectional Sync**: Sync Jira updates back to GitHub
2. **Comment Sync**: Mirror comments between platforms
3. **Status Sync**: Update GitHub issue status based on Jira status
4. **Assignee Sync**: Map and sync assignees
5. **Update Handling**: Detect when tracked issues are updated
6. **Bulk Operations**: Handle multiple label additions efficiently
7. **Notification**: Send Slack/email notifications on sync

## Support

For issues or questions:
1. Check the Actions logs in GitHub
2. Review the Jira API documentation: https://developer.atlassian.com/cloud/jira/platform/rest/v2/
3. Verify your configuration follows the setup instructions above
