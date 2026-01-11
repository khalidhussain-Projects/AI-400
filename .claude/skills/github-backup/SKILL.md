---
name: github-backup
description: >
  Automated GitHub repository backup system with mirror cloning, multiple storage providers,
  and scheduled workflows. Use when user needs to set up automated backups for GitHub repositories,
  create mirror clones preserving full history, configure backup storage (GitHub, S3, GCS, Azure),
  restore repositories from backups, verify backup integrity, or auto-discover repositories to backup.
  Triggers on backup automation, disaster recovery, repository mirroring, or data preservation tasks.
---

# GitHub Backup

Automated backup system for GitHub repositories using mirror cloning with full history preservation.

## Quick Start

### 1. Create Backup Repository

```bash
# Using GitHub CLI
gh repo create my-github-backups --private
git clone https://github.com/USERNAME/my-github-backups.git
cd my-github-backups
git checkout -b backups
mkdir -p backups .github/workflows
git add . && git commit -m "Initialize backup repo" && git push -u origin backups
```

### 2. Create Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Create token with `repo` scope (or `Contents: Read` for fine-grained)
3. Add as repository secret: `BACKUP_PAT`

### 3. Add Workflow and Config

Copy `assets/workflows/backup.yml` to `.github/workflows/`
Copy `assets/config.example.json` as `config.json` and customize repositories

### 4. Run Backup

Workflow runs automatically on schedule, or trigger manually from Actions tab.

---

## Core Scripts

### Backup (`scripts/backup.sh`)

Creates mirror clone backups with full history.

```bash
# Environment
export GITHUB_TOKEN="your-token"
export BACKUP_DIR="./backups"
export STORAGE_TYPE="github"  # github, s3, gcs, azure, local

# Backup specific repositories
bash scripts/backup.sh owner/repo1 owner/repo2

# Backup from config file
CONFIG_FILE=config.json bash scripts/backup.sh
```

### Restore (`scripts/restore.sh`)

Restore repositories from backup archives.

```bash
# Restore to local directory
bash scripts/restore.sh backups/repo_latest.tar.gz ./restored-repo

# Restore to new GitHub repository
bash scripts/restore.sh -m github backups/repo_latest.tar.gz owner/new-repo

# Mirror push to existing repository (overwrites!)
bash scripts/restore.sh -m mirror -f backups/repo_latest.tar.gz owner/existing-repo
```

### Verify (`scripts/verify.sh`)

Verify backup integrity and completeness.

```bash
# Verify single archive
bash scripts/verify.sh backups/repo_2024-01-15.tar.gz

# Verify all backups in directory
bash scripts/verify.sh ./backups

# Compare with live repository
bash scripts/verify.sh -c owner/repo backups/repo_latest.tar.gz
```

### Discover Repos (`scripts/discover-repos.sh`)

Auto-discover repositories for backup.

```bash
# List all your repositories
bash scripts/discover-repos.sh

# Include organization repos
bash scripts/discover-repos.sh -o my-org

# Generate config file (excluding forks and archived)
bash scripts/discover-repos.sh --no-forks --no-archived -c config.json

# Output as JSON
bash scripts/discover-repos.sh -o my-org --json
```

---

## Storage Options

| Provider | Best For | Setup Complexity |
|----------|----------|------------------|
| GitHub | Small repos, simple setup | Low |
| AWS S3 | Production, large repos | Medium |
| Google Cloud | GCP users | Medium |
| Azure Blob | Enterprise, Azure users | Medium |

See [references/storage-providers.md](references/storage-providers.md) for detailed configuration.

---

## Workflow Configuration

The workflow template (`assets/workflows/backup.yml`) supports:

- **Scheduled backups**: Cron-based (default: daily at 2 AM UTC)
- **Manual triggers**: Run on-demand with optional repo filter
- **Multiple storage**: GitHub, S3, GCS, Azure, or artifacts
- **Notifications**: Slack, email, Discord, Teams
- **Verification**: Automatic integrity checks

### Cron Schedule Examples

| Schedule | Cron Expression |
|----------|-----------------|
| Daily 2 AM | `0 2 * * *` |
| Every 6 hours | `0 */6 * * *` |
| Weekly Sunday | `0 2 * * 0` |
| Monthly 1st | `0 2 1 * *` |

---

## References

- [Storage Providers](references/storage-providers.md) - S3, GCS, Azure, GitHub configuration
- [Notifications](references/notifications.md) - Slack, email, Discord, Teams setup
- [Troubleshooting](references/troubleshooting.md) - Common issues and solutions

---

## Assets

- `assets/workflows/backup.yml` - GitHub Actions workflow template
- `assets/config.example.json` - Configuration file template
