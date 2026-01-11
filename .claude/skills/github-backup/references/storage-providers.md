# Storage Provider Configuration

## Table of Contents
- [GitHub Repository](#github-repository)
- [AWS S3](#aws-s3)
- [Google Cloud Storage](#google-cloud-storage)
- [Azure Blob Storage](#azure-blob-storage)
- [Local Storage](#local-storage)

---

## GitHub Repository

Store backups in a dedicated branch of a GitHub repository.

### Setup

1. Create a backup repository (or use existing)
2. Create a `backups` branch
3. Add `BACKUP_PAT` secret with `repo` scope

### Secrets Required

| Secret | Description |
|--------|-------------|
| `BACKUP_PAT` | Personal Access Token with `repo` scope |

### Environment Variables

```bash
STORAGE_TYPE=github
GITHUB_BACKUP_BRANCH=backups
```

### Workflow Configuration

```yaml
env:
  BACKUP_BRANCH: backups

# In job steps:
- name: Push to GitHub
  run: |
    git add backups/
    git commit -m "Backup $(date +%Y-%m-%d)"
    git push origin $BACKUP_BRANCH
```

---

## AWS S3

Store backups in an Amazon S3 bucket.

### Setup

1. Create S3 bucket with versioning enabled (recommended)
2. Create IAM user with S3 write permissions
3. Add secrets to GitHub repository

### Secrets Required

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `AWS_REGION` | AWS region (default: us-east-1) |
| `S3_BUCKET` | S3 bucket name |

### IAM Policy (Minimum)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

### Environment Variables

```bash
STORAGE_TYPE=s3
S3_BUCKET=my-backup-bucket
S3_PREFIX=github-backups
AWS_REGION=us-east-1
```

### Lifecycle Policy (Optional)

Configure S3 lifecycle rules to automatically delete old backups:

```json
{
  "Rules": [
    {
      "ID": "DeleteOldBackups",
      "Status": "Enabled",
      "Filter": {"Prefix": "github-backups/"},
      "Expiration": {"Days": 90}
    }
  ]
}
```

---

## Google Cloud Storage

Store backups in a GCS bucket.

### Setup

1. Create GCS bucket
2. Create service account with Storage Object Admin role
3. Generate JSON key and add to secrets

### Secrets Required

| Secret | Description |
|--------|-------------|
| `GCP_SA_KEY` | Service account JSON key (base64 encoded) |
| `GCS_BUCKET` | GCS bucket name |

### Service Account Permissions

- `roles/storage.objectAdmin` on the bucket

### Environment Variables

```bash
STORAGE_TYPE=gcs
GCS_BUCKET=my-backup-bucket
GCS_PREFIX=github-backups
```

### Workflow Configuration

```yaml
- uses: google-github-actions/setup-gcloud@v1
  with:
    service_account_key: ${{ secrets.GCP_SA_KEY }}

- run: gsutil cp backup.tar.gz gs://$GCS_BUCKET/backups/
```

---

## Azure Blob Storage

Store backups in Azure Blob Storage.

### Setup

1. Create storage account and container
2. Generate SAS token or use managed identity
3. Add credentials to secrets

### Secrets Required

| Secret | Description |
|--------|-------------|
| `AZURE_STORAGE_ACCOUNT` | Storage account name |
| `AZURE_STORAGE_KEY` | Storage account key |
| `AZURE_CONTAINER` | Container name |

### Environment Variables

```bash
STORAGE_TYPE=azure
AZURE_ACCOUNT=mystorageaccount
AZURE_CONTAINER=backups
AZURE_PREFIX=github-backups
```

### Workflow Configuration

```yaml
- name: Azure Login
  uses: azure/login@v1
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}

- name: Upload to Azure
  run: |
    az storage blob upload \
      --account-name $AZURE_ACCOUNT \
      --container-name $AZURE_CONTAINER \
      --name "backups/$(basename $ARCHIVE)" \
      --file "$ARCHIVE"
```

---

## Local Storage

Store backups as GitHub Actions artifacts (temporary) or download locally.

### Use Cases
- Testing backup workflow
- One-time backups
- Download for local storage

### Workflow Configuration

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: backup-${{ matrix.repo }}
    path: backups/**/*.tar.gz
    retention-days: 30
```

### Download Artifacts

```bash
# Using GitHub CLI
gh run download <run-id> -n backup-owner_repo
```

---

## Storage Comparison

| Feature | GitHub | S3 | GCS | Azure | Local |
|---------|--------|-----|-----|-------|-------|
| Cost | Free* | Pay per GB | Pay per GB | Pay per GB | Free |
| Durability | 99.9% | 99.999999999% | 99.999999999% | 99.9999999999% | N/A |
| Max Size | Repo limits | Unlimited | Unlimited | Unlimited | 500MB |
| Versioning | Git history | Optional | Optional | Optional | No |
| Best For | Small repos | Production | Production | Enterprise | Testing |

*Within repository limits
