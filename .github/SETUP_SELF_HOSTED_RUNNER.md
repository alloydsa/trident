# Setting Up Self-Hosted GitHub Actions Runner

Since Jira requires VPN access, you need to run the workflow on a machine inside the NetApp network.

## Prerequisites

- A Linux/macOS/Windows machine or VM inside NetApp network
- VPN access to Jira (jira.ngage.netapp.com)
- Python 3.11+ installed
- Sufficient permissions to install software

## Step 1: Prepare the Machine

1. **Connect to your NetApp machine** (via SSH or direct access)

2. **Verify Jira connectivity**:

   ```bash
   curl -I https://jira.ngage.netapp.com
   # Should return HTTP 200 or redirect, not connection refused
   ```

3. **Install Python 3.11+** (if not already installed):

   ```bash
   # macOS
   brew install python@3.11

   # Ubuntu/Debian
   sudo apt update && sudo apt install python3.11 python3-pip

   # RHEL/CentOS
   sudo yum install python3.11 python3-pip
   ```

4. **Install required Python packages**:
   ```bash
   pip3 install requests
   ```

## Step 2: Add Self-Hosted Runner to GitHub

### For Your Fork (alloydsa/trident):

1. Go to: **https://github.com/alloydsa/trident/settings/actions/runners**

2. Click **"New self-hosted runner"**

3. Select your OS (Linux/macOS/Windows)

4. Follow the commands shown (example for Linux):

   ```bash
   # Create a folder
   mkdir actions-runner && cd actions-runner

   # Download the latest runner package
   curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
     https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

   # Extract the installer
   tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

   # Configure the runner
   ./config.sh --url https://github.com/alloydsa/trident --token YOUR_TOKEN_HERE

   # Run the runner
   ./run.sh
   ```

5. **Add labels** during configuration (optional but recommended):

   - When prompted, add label: `netapp-vpn` or `jira-access`

6. **Keep it running**:
   ```bash
   # For long-term use, install as a service:
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

### For Main Repository (NetApp/trident):

If you need this on the main repo, you'll need admin access or request the NetApp team to:

1. Set up the self-hosted runner on a NetApp machine
2. Configure it at: https://github.com/NetApp/trident/settings/actions/runners

## Step 3: Configure GitHub Secrets

Go to: **https://github.com/alloydsa/trident/settings/secrets/actions**

Add these secrets:

- `JIRA_URL` = `https://jira.ngage.netapp.com`
- `JIRA_PAT` = Your Jira Personal Access Token (get from Jira → Profile → Personal Access Tokens)
- `JIRA_PROJECT_KEY` = `TRID`
- `JIRA_EPIC_KEY` = `TRID-10984` (optional)

## Step 4: Test the Setup

1. **Verify runner is online**:

   - Go to: https://github.com/alloydsa/trident/settings/actions/runners
   - Status should show "Idle" (green)

2. **Create a test issue** on your fork

3. **Add the `tracked` label**

4. **Check the Actions tab**: https://github.com/alloydsa/trident/actions
   - The workflow should run on your self-hosted runner
   - Check logs for any errors

## Troubleshooting

### Runner Shows Offline

```bash
# Check if runner service is running
sudo ./svc.sh status

# Restart if needed
sudo ./svc.sh restart

# Check logs
tail -f _diag/Runner_*.log
```

### Python Not Found

```bash
# Add Python to PATH in runner config
export PATH="/usr/local/bin:$PATH"

# Or specify full path in workflow (edit sync-issue-to-jira.yml):
uses: actions/setup-python@v5
with:
  python-version: '3.11'
```

### Jira Connection Fails

```bash
# Test from the runner machine using Personal Access Token:
curl -H "Authorization: Bearer YOUR_PAT_TOKEN" \
  https://jira.ngage.netapp.com/rest/api/2/myself

# Should return your Jira user info
```

### Permission Issues

```bash
# Ensure runner user has access to Python
which python3
python3 --version

# Install packages for runner user
sudo -u runner-user pip3 install requests
```

## Security Considerations

1. **Keep runner updated**: Regularly update the runner software
2. **Restrict access**: Only give runner access to necessary repos
3. **Monitor logs**: Check runner logs regularly for suspicious activity
4. **Use dedicated machine**: Don't run other services on the runner machine
5. **Secure secrets**: Never log or expose the API tokens

## Alternative: Use Existing CI/CD Infrastructure

If NetApp already has Jenkins, GitLab CI, or other CI/CD infrastructure inside the VPN:

1. Trigger it via webhook from GitHub
2. Use that infrastructure to create Jira tickets
3. No need for a dedicated GitHub Actions runner

## Cost Comparison

| Solution           | Setup Time | Maintenance | Cost                          |
| ------------------ | ---------- | ----------- | ----------------------------- |
| Self-hosted runner | 30 min     | Low         | Free (uses existing hardware) |
| Tasktop            | 5 min      | None        | $$$ (licensing)               |
| Webhook service    | 1-2 hours  | Low         | Free                          |

---

Need help with any step? Check the runner logs or GitHub Actions documentation:

- https://docs.github.com/en/actions/hosting-your-own-runners
