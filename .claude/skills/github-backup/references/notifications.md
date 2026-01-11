# Notification Configuration

## Table of Contents
- [Slack](#slack)
- [Email](#email)
- [Discord](#discord)
- [Microsoft Teams](#microsoft-teams)
- [Custom Webhooks](#custom-webhooks)

---

## Slack

### Setup

1. Create Slack App or use Incoming Webhooks
2. Add webhook URL to repository variables

### Variables/Secrets

| Name | Type | Description |
|------|------|-------------|
| `SLACK_WEBHOOK_URL` | Variable | Incoming webhook URL |

### Workflow Step

```yaml
- name: Notify Slack
  if: always()
  env:
    SLACK_WEBHOOK_URL: ${{ vars.SLACK_WEBHOOK_URL }}
  run: |
    STATUS="${{ job.status }}"
    COLOR="good"
    [[ "$STATUS" != "success" ]] && COLOR="danger"

    curl -X POST "$SLACK_WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "{
        \"attachments\": [{
          \"color\": \"$COLOR\",
          \"title\": \"GitHub Backup $STATUS\",
          \"text\": \"Backup completed at $(date -u)\",
          \"fields\": [
            {\"title\": \"Repository\", \"value\": \"${{ github.repository }}\", \"short\": true},
            {\"title\": \"Status\", \"value\": \"$STATUS\", \"short\": true}
          ],
          \"footer\": \"GitHub Actions\",
          \"ts\": $(date +%s)
        }]
      }"
```

### Message Template

```json
{
  "attachments": [{
    "color": "good",
    "title": "Backup Successful",
    "fields": [
      {"title": "Repositories", "value": "5 backed up"},
      {"title": "Size", "value": "1.2 GB"},
      {"title": "Duration", "value": "3m 42s"}
    ]
  }]
}
```

---

## Email

### Using SMTP

#### Secrets Required

| Secret | Description |
|--------|-------------|
| `SMTP_SERVER` | SMTP server address |
| `SMTP_PORT` | SMTP port (587 for TLS) |
| `SMTP_USERNAME` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |

#### Variables

| Variable | Description |
|----------|-------------|
| `NOTIFICATION_EMAIL` | Recipient email(s) |

#### Workflow Step

```yaml
- name: Send email notification
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: ${{ secrets.SMTP_SERVER }}
    server_port: ${{ secrets.SMTP_PORT }}
    username: ${{ secrets.SMTP_USERNAME }}
    password: ${{ secrets.SMTP_PASSWORD }}
    subject: "GitHub Backup ${{ job.status }} - ${{ github.repository }}"
    to: ${{ vars.NOTIFICATION_EMAIL }}
    from: GitHub Actions <noreply@github.com>
    body: |
      Backup Status: ${{ job.status }}

      Repository: ${{ github.repository }}
      Workflow: ${{ github.workflow }}
      Run URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}

      Triggered by: ${{ github.event_name }}
      Time: ${{ github.event.head_commit.timestamp }}
```

### Using SendGrid

```yaml
- name: Send via SendGrid
  if: failure()
  env:
    SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
  run: |
    curl -X POST "https://api.sendgrid.com/v3/mail/send" \
      -H "Authorization: Bearer $SENDGRID_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "personalizations": [{"to": [{"email": "${{ vars.NOTIFICATION_EMAIL }}"}]}],
        "from": {"email": "backups@example.com"},
        "subject": "GitHub Backup Failed",
        "content": [{"type": "text/plain", "value": "Backup failed. Check workflow logs."}]
      }'
```

---

## Discord

### Setup

1. Create Discord webhook in channel settings
2. Add webhook URL to secrets

### Workflow Step

```yaml
- name: Notify Discord
  if: always()
  env:
    DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
  run: |
    STATUS="${{ job.status }}"
    COLOR=3066993  # Green
    [[ "$STATUS" != "success" ]] && COLOR=15158332  # Red

    curl -X POST "$DISCORD_WEBHOOK" \
      -H "Content-Type: application/json" \
      -d "{
        \"embeds\": [{
          \"title\": \"GitHub Backup $STATUS\",
          \"color\": $COLOR,
          \"fields\": [
            {\"name\": \"Repository\", \"value\": \"${{ github.repository }}\", \"inline\": true},
            {\"name\": \"Status\", \"value\": \"$STATUS\", \"inline\": true}
          ],
          \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
        }]
      }"
```

---

## Microsoft Teams

### Setup

1. Add Incoming Webhook connector to Teams channel
2. Add webhook URL to secrets

### Workflow Step

```yaml
- name: Notify Teams
  if: always()
  env:
    TEAMS_WEBHOOK: ${{ secrets.TEAMS_WEBHOOK }}
  run: |
    STATUS="${{ job.status }}"
    COLOR="00FF00"
    [[ "$STATUS" != "success" ]] && COLOR="FF0000"

    curl -X POST "$TEAMS_WEBHOOK" \
      -H "Content-Type: application/json" \
      -d "{
        \"@type\": \"MessageCard\",
        \"themeColor\": \"$COLOR\",
        \"title\": \"GitHub Backup $STATUS\",
        \"sections\": [{
          \"facts\": [
            {\"name\": \"Repository\", \"value\": \"${{ github.repository }}\"},
            {\"name\": \"Status\", \"value\": \"$STATUS\"},
            {\"name\": \"Time\", \"value\": \"$(date -u)\"}
          ]
        }],
        \"potentialAction\": [{
          \"@type\": \"OpenUri\",
          \"name\": \"View Run\",
          \"targets\": [{\"os\": \"default\", \"uri\": \"${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}\"}]
        }]
      }"
```

---

## Custom Webhooks

### Generic Webhook

```yaml
- name: Custom webhook
  if: always()
  run: |
    curl -X POST "${{ secrets.WEBHOOK_URL }}" \
      -H "Content-Type: application/json" \
      -H "X-GitHub-Event: backup" \
      -d "{
        \"status\": \"${{ job.status }}\",
        \"repository\": \"${{ github.repository }}\",
        \"run_id\": \"${{ github.run_id }}\",
        \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
        \"event\": \"${{ github.event_name }}\"
      }"
```

### PagerDuty (On Failure)

```yaml
- name: Alert PagerDuty
  if: failure()
  run: |
    curl -X POST "https://events.pagerduty.com/v2/enqueue" \
      -H "Content-Type: application/json" \
      -d "{
        \"routing_key\": \"${{ secrets.PAGERDUTY_KEY }}\",
        \"event_action\": \"trigger\",
        \"payload\": {
          \"summary\": \"GitHub backup failed for ${{ github.repository }}\",
          \"severity\": \"warning\",
          \"source\": \"github-actions\"
        }
      }"
```

---

## Notification Best Practices

1. **On Failure Only**: For routine backups, only notify on failures
2. **Summary Reports**: For multiple repos, send single summary instead of per-repo
3. **Deduplication**: Avoid duplicate notifications with proper `if` conditions
4. **Severity Levels**: Use different channels for warnings vs critical failures
5. **Include Links**: Always include link to workflow run for debugging
