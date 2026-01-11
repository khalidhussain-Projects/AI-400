# Troubleshooting Guide

## Table of Contents
- [Authentication Errors](#authentication-errors)
- [Clone Failures](#clone-failures)
- [Storage Issues](#storage-issues)
- [Workflow Problems](#workflow-problems)
- [Restore Issues](#restore-issues)
- [Performance](#performance)

---

## Authentication Errors

### "Bad credentials" or 401 Error

**Cause**: Invalid or expired GitHub token

**Solutions**:
1. Regenerate Personal Access Token
2. Ensure token has `repo` scope (for private repos)
3. Check token hasn't expired
4. Verify secret name matches workflow

```bash
# Test token validity
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

### "Resource not accessible by integration"

**Cause**: Token lacks required permissions

**Solutions**:
1. For fine-grained tokens: Add `Contents: Read` permission
2. For classic tokens: Ensure `repo` scope
3. For org repos: Token owner must be org member

### "Rate limit exceeded"

**Cause**: Too many API requests

**Solutions**:
1. Add delays between repository backups
2. Use authenticated requests (higher limits)
3. Reduce parallel jobs in workflow

```yaml
strategy:
  max-parallel: 2  # Reduce concurrent backups
```

---

## Clone Failures

### "Repository not found"

**Causes**:
- Repository doesn't exist
- No access to private repository
- Typo in repository name

**Solutions**:
1. Verify repository exists and path is correct
2. Check token has access to the repository
3. For org repos, ensure token owner has access

### "fatal: the remote end hung up unexpectedly"

**Cause**: Network timeout or large repository

**Solutions**:
1. Increase Git buffer size:
```bash
git config --global http.postBuffer 524288000
```

2. Use shallow clone for initial test:
```bash
git clone --depth 1 https://github.com/owner/repo.git
```

3. Increase timeout in workflow:
```yaml
- name: Clone with timeout
  timeout-minutes: 30
  run: git clone --mirror ...
```

### "fatal: unable to access... SSL certificate problem"

**Cause**: SSL/TLS issues

**Solutions**:
1. Update CA certificates
2. Temporarily disable SSL verification (not recommended):
```bash
GIT_SSL_NO_VERIFY=1 git clone ...
```

---

## Storage Issues

### GitHub: "Push rejected - repository size limit"

**Cause**: GitHub has repository size limits (~100GB)

**Solutions**:
1. Use external storage (S3, GCS) for large backups
2. Split backups across multiple repositories
3. Exclude large binary files

### S3: "Access Denied"

**Cause**: IAM permissions insufficient

**Solutions**:
1. Verify IAM policy includes required actions
2. Check bucket policy allows access
3. Ensure correct bucket region

```bash
# Test S3 access
aws s3 ls s3://your-bucket/
aws s3 cp test.txt s3://your-bucket/
```

### GCS: "403 Forbidden"

**Cause**: Service account lacks permissions

**Solutions**:
1. Grant `Storage Object Admin` role to service account
2. Check bucket-level IAM permissions
3. Verify JSON key is valid and not expired

---

## Workflow Problems

### "Scheduled workflow not running"

**Causes**:
- Repository inactive for 60+ days (public repos)
- Workflow disabled
- Cron syntax error

**Solutions**:
1. Push a commit to reactivate
2. Check Actions tab for disabled workflows
3. Validate cron syntax at crontab.guru

### "Workflow cancelled"

**Cause**: Timeout or manual cancellation

**Solutions**:
1. Increase job timeout:
```yaml
jobs:
  backup:
    timeout-minutes: 120
```

2. Check for resource constraints
3. Split into smaller jobs

### "No space left on device"

**Cause**: Runner disk full

**Solutions**:
1. Free up space before backup:
```yaml
- name: Free disk space
  run: |
    sudo rm -rf /usr/share/dotnet
    sudo rm -rf /opt/ghc
    df -h
```

2. Use larger runner:
```yaml
runs-on: ubuntu-latest-16-cores
```

---

## Restore Issues

### "fatal: refusing to merge unrelated histories"

**Cause**: Trying to push mirror to non-empty repository

**Solutions**:
1. Use `--force` flag with mirror push
2. Create empty repository for restore
3. Use `--allow-unrelated-histories` if merging

### "LFS objects missing after restore"

**Cause**: LFS objects not included in backup

**Solutions**:
1. Ensure `git lfs fetch --all` ran during backup
2. Re-run LFS fetch from original repo if available
3. Check LFS storage in archive

```bash
# Verify LFS objects in backup
tar -tzf backup.tar.gz | grep lfs
```

### "Corrupt archive"

**Cause**: Incomplete upload or download

**Solutions**:
1. Re-download archive
2. Verify checksum if available
3. Use verification script before restore

```bash
# Verify archive integrity
bash scripts/verify.sh backup.tar.gz
```

---

## Performance

### Backup taking too long

**Causes**:
- Large repository
- Many LFS objects
- Slow network

**Solutions**:
1. Increase parallel jobs (if not rate-limited)
2. Use faster runner
3. Consider incremental backups for frequently updated repos
4. Exclude unnecessary refs:
```bash
git clone --mirror --single-branch ...
```

### High storage costs

**Solutions**:
1. Reduce retention count
2. Use storage lifecycle policies
3. Compress with higher ratio:
```bash
tar -I 'gzip -9' -cf backup.tar.gz repo.git
```

4. Exclude large binary files if not needed

---

## Quick Diagnostics

### Check Token Permissions

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/user | jq '.login, .plan.name'
```

### Check Rate Limits

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit | jq '.rate'
```

### Verify Repository Access

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo | jq '.permissions'
```

### Test Archive Integrity

```bash
gzip -t backup.tar.gz && tar -tzf backup.tar.gz > /dev/null && echo "OK"
```

---

## Getting Help

1. Check workflow logs in GitHub Actions
2. Run scripts with `set -x` for debug output
3. Test individual steps manually
4. Review GitHub Status: https://www.githubstatus.com/
