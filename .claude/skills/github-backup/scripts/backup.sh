#!/usr/bin/env bash
#
# GitHub Repository Backup Script
# Creates mirror clones with full history, compresses, and uploads to storage
#
set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
CONFIG_FILE="${CONFIG_FILE:-config.json}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="${LOG_FILE:-backup_${DATE}.log}"
RETENTION_COUNT="${RETENTION_COUNT:-7}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging Functions
# ============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

# ============================================================================
# Helper Functions
# ============================================================================
check_dependencies() {
    local deps=("git" "jq" "curl")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Required dependency not found: $dep"
            exit 1
        fi
    done
    log_info "All dependencies satisfied"
}

validate_token() {
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        log_error "GITHUB_TOKEN environment variable is not set"
        exit 1
    fi

    # Validate token by making API call
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/user")

    if [[ "$response" != "200" ]]; then
        log_error "Invalid GITHUB_TOKEN (HTTP $response)"
        exit 1
    fi
    log_info "GitHub token validated"
}

# ============================================================================
# Backup Functions
# ============================================================================
backup_repo() {
    local repo="$1"
    local repo_name="${repo//\//_}"
    local backup_path="${BACKUP_DIR}/${repo_name}"
    local archive_name="${repo_name}_${DATE}.tar.gz"

    log_info "Backing up: $repo"
    mkdir -p "$backup_path"

    # Mirror clone
    log_info "  Creating mirror clone..."
    if ! git clone --mirror "https://${GITHUB_TOKEN}@github.com/${repo}.git" "${repo_name}.git" 2>> "$LOG_FILE"; then
        log_error "  Failed to clone $repo"
        return 1
    fi

    # Handle Git LFS
    if [[ -d "${repo_name}.git/lfs" ]] || git -C "${repo_name}.git" lfs ls-files &>/dev/null; then
        log_info "  Fetching Git LFS objects..."
        (cd "${repo_name}.git" && git lfs fetch --all 2>> "$LOG_FILE") || log_warn "  LFS fetch had issues"
    fi

    # Create compressed archive
    log_info "  Creating archive: $archive_name"
    tar -czf "${backup_path}/${archive_name}" "${repo_name}.git"

    # Create latest symlink
    cp "${backup_path}/${archive_name}" "${backup_path}/${repo_name}_latest.tar.gz"

    # Get archive size
    local size
    size=$(du -h "${backup_path}/${archive_name}" | cut -f1)
    log_success "  Backup complete: $archive_name ($size)"

    # Cleanup temp directory
    rm -rf "${repo_name}.git"

    # Apply retention policy
    cleanup_old_backups "$backup_path" "$repo_name"

    return 0
}

cleanup_old_backups() {
    local backup_path="$1"
    local repo_name="$2"

    # Keep only the last N backups (excluding _latest)
    local count
    count=$(ls -1 "${backup_path}/${repo_name}_2"*.tar.gz 2>/dev/null | wc -l)

    if [[ "$count" -gt "$RETENTION_COUNT" ]]; then
        local to_delete=$((count - RETENTION_COUNT))
        log_info "  Removing $to_delete old backup(s)..."
        ls -1t "${backup_path}/${repo_name}_2"*.tar.gz | tail -n "$to_delete" | xargs rm -f
    fi
}

# ============================================================================
# Storage Upload Functions
# ============================================================================
upload_to_s3() {
    local file="$1"
    local bucket="$2"
    local prefix="${3:-backups}"

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not installed"
        return 1
    fi

    log_info "Uploading to S3: s3://${bucket}/${prefix}/$(basename "$file")"
    aws s3 cp "$file" "s3://${bucket}/${prefix}/$(basename "$file")" --quiet
    log_success "S3 upload complete"
}

upload_to_gcs() {
    local file="$1"
    local bucket="$2"
    local prefix="${3:-backups}"

    if ! command -v gsutil &> /dev/null; then
        log_error "gsutil not installed"
        return 1
    fi

    log_info "Uploading to GCS: gs://${bucket}/${prefix}/$(basename "$file")"
    gsutil cp "$file" "gs://${bucket}/${prefix}/$(basename "$file")"
    log_success "GCS upload complete"
}

upload_to_azure() {
    local file="$1"
    local container="$2"
    local account="$3"
    local prefix="${4:-backups}"

    if ! command -v az &> /dev/null; then
        log_error "Azure CLI not installed"
        return 1
    fi

    log_info "Uploading to Azure Blob: ${container}/${prefix}/$(basename "$file")"
    az storage blob upload \
        --account-name "$account" \
        --container-name "$container" \
        --name "${prefix}/$(basename "$file")" \
        --file "$file" \
        --only-show-errors
    log_success "Azure upload complete"
}

push_to_github() {
    local branch="${1:-backups}"

    log_info "Pushing backups to GitHub branch: $branch"

    git add "${BACKUP_DIR}/"
    if git diff --staged --quiet; then
        log_info "No changes to commit"
        return 0
    fi

    git commit -m "Backup $(date +%Y-%m-%d)"
    git push origin "$branch"
    log_success "Pushed to GitHub"
}

# ============================================================================
# Main Execution
# ============================================================================
main() {
    local repos=()
    local storage_type="${STORAGE_TYPE:-local}"
    local failed=0
    local success=0

    echo "=========================================="
    echo "  GitHub Repository Backup"
    echo "  Started: $(date)"
    echo "=========================================="

    check_dependencies
    validate_token
    mkdir -p "$BACKUP_DIR"

    # Parse repositories from arguments or config
    if [[ $# -gt 0 ]]; then
        repos=("$@")
    elif [[ -f "$CONFIG_FILE" ]]; then
        mapfile -t repos < <(jq -r '.repositories[]' "$CONFIG_FILE" 2>/dev/null)
    else
        log_error "No repositories specified. Provide as arguments or in $CONFIG_FILE"
        exit 1
    fi

    log_info "Backing up ${#repos[@]} repository(ies)"

    # Backup each repository
    for repo in "${repos[@]}"; do
        if backup_repo "$repo"; then
            ((success++))
        else
            ((failed++))
        fi
    done

    # Upload to external storage if configured
    if [[ "$storage_type" != "local" ]]; then
        log_info "Uploading to $storage_type..."
        case "$storage_type" in
            s3)
                for archive in "${BACKUP_DIR}"/*/*.tar.gz; do
                    upload_to_s3 "$archive" "${S3_BUCKET:-}" "${S3_PREFIX:-backups}"
                done
                ;;
            gcs)
                for archive in "${BACKUP_DIR}"/*/*.tar.gz; do
                    upload_to_gcs "$archive" "${GCS_BUCKET:-}" "${GCS_PREFIX:-backups}"
                done
                ;;
            azure)
                for archive in "${BACKUP_DIR}"/*/*.tar.gz; do
                    upload_to_azure "$archive" "${AZURE_CONTAINER:-}" "${AZURE_ACCOUNT:-}" "${AZURE_PREFIX:-backups}"
                done
                ;;
            github)
                push_to_github "${GITHUB_BACKUP_BRANCH:-backups}"
                ;;
        esac
    fi

    # Summary
    echo ""
    echo "=========================================="
    echo "  Backup Summary"
    echo "=========================================="
    log_info "Completed: $(date)"
    log_success "Successful: $success"
    [[ $failed -gt 0 ]] && log_error "Failed: $failed"

    # Exit with error if any failed
    [[ $failed -gt 0 ]] && exit 1
    exit 0
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
