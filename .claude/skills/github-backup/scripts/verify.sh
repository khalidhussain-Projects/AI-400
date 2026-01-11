#!/usr/bin/env bash
#
# GitHub Backup Verification Script
# Verifies integrity and completeness of backup archives
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] <backup-archive|backup-directory>

Verify the integrity of GitHub repository backup(s).

Arguments:
  backup-archive     Path to a single backup .tar.gz archive
  backup-directory   Path to directory containing multiple backups

Options:
  -c, --compare REPO   Compare backup with live GitHub repository
  -v, --verbose        Show detailed verification output
  -q, --quick          Quick verification (skip full git fsck)
  -h, --help           Show this help message

Checks Performed:
  1. Archive integrity (gzip, tar)
  2. Git repository structure
  3. Git object integrity (git fsck)
  4. Branch and tag verification
  5. LFS objects (if present)
  6. Optional: Compare with live repository

Examples:
  # Verify single archive
  $(basename "$0") backups/myrepo_2024-01-15.tar.gz

  # Verify all backups in directory
  $(basename "$0") ./backups

  # Compare backup with live repository
  $(basename "$0") -c owner/repo backups/myrepo_latest.tar.gz
EOF
}

# ============================================================================
# Verification Functions
# ============================================================================
verify_archive_integrity() {
    local archive="$1"

    log_info "Checking archive integrity..."

    # Check gzip integrity
    if ! gzip -t "$archive" 2>/dev/null; then
        log_error "Archive corrupted (gzip check failed)"
        return 1
    fi

    # Check tar integrity
    if ! tar -tzf "$archive" >/dev/null 2>&1; then
        log_error "Archive corrupted (tar check failed)"
        return 1
    fi

    log_success "Archive integrity verified"
    return 0
}

verify_git_structure() {
    local git_dir="$1"

    log_info "Checking Git repository structure..."

    # Check for essential git files
    local required_files=("HEAD" "config" "objects" "refs")
    for file in "${required_files[@]}"; do
        if [[ ! -e "${git_dir}/${file}" ]]; then
            log_error "Missing required Git component: $file"
            return 1
        fi
    done

    # Verify it's a bare repository
    if [[ ! -f "${git_dir}/HEAD" ]]; then
        log_error "Not a valid Git repository"
        return 1
    fi

    log_success "Git repository structure valid"
    return 0
}

verify_git_objects() {
    local git_dir="$1"
    local quick="${2:-false}"

    log_info "Verifying Git objects..."

    local fsck_args="--no-dangling"
    [[ "$quick" == "true" ]] && fsck_args="--connectivity-only"

    local fsck_output
    if ! fsck_output=$(git --git-dir="$git_dir" fsck $fsck_args 2>&1); then
        log_error "Git fsck found errors:"
        echo "$fsck_output" | head -20
        return 1
    fi

    log_success "Git objects verified"
    return 0
}

verify_refs() {
    local git_dir="$1"
    local verbose="${2:-false}"

    log_info "Verifying branches and tags..."

    # Count branches
    local branch_count
    branch_count=$(git --git-dir="$git_dir" branch -a 2>/dev/null | wc -l)

    # Count tags
    local tag_count
    tag_count=$(git --git-dir="$git_dir" tag 2>/dev/null | wc -l)

    if [[ "$verbose" == "true" ]]; then
        echo "  Branches: $branch_count"
        echo "  Tags: $tag_count"
        echo "  Default branch: $(git --git-dir="$git_dir" symbolic-ref HEAD 2>/dev/null | sed 's|refs/heads/||' || echo 'unknown')"
    fi

    if [[ "$branch_count" -eq 0 ]]; then
        log_warn "No branches found in backup"
    else
        log_success "Refs verified ($branch_count branches, $tag_count tags)"
    fi

    return 0
}

verify_lfs() {
    local git_dir="$1"
    local verbose="${2:-false}"

    if [[ ! -d "${git_dir}/lfs" ]]; then
        [[ "$verbose" == "true" ]] && log_info "No LFS objects present"
        return 0
    fi

    log_info "Verifying LFS objects..."

    local lfs_count
    lfs_count=$(find "${git_dir}/lfs" -type f 2>/dev/null | wc -l)

    if [[ "$lfs_count" -gt 0 ]]; then
        local lfs_size
        lfs_size=$(du -sh "${git_dir}/lfs" 2>/dev/null | cut -f1)
        log_success "LFS objects present ($lfs_count files, $lfs_size)"
    else
        log_warn "LFS directory exists but contains no objects"
    fi

    return 0
}

compare_with_live() {
    local git_dir="$1"
    local repo="$2"

    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        log_warn "GITHUB_TOKEN not set, skipping live comparison"
        return 0
    fi

    log_info "Comparing with live repository: $repo"

    # Get remote refs
    local remote_refs
    remote_refs=$(git ls-remote "https://${GITHUB_TOKEN}@github.com/${repo}.git" 2>/dev/null | head -20)

    if [[ -z "$remote_refs" ]]; then
        log_error "Could not fetch remote refs for $repo"
        return 1
    fi

    # Compare HEAD
    local remote_head
    remote_head=$(echo "$remote_refs" | grep "HEAD" | cut -f1)

    local local_head
    local_head=$(git --git-dir="$git_dir" rev-parse HEAD 2>/dev/null || echo "unknown")

    if [[ "$remote_head" == "$local_head" ]]; then
        log_success "Backup HEAD matches live repository"
    else
        log_warn "Backup HEAD differs from live repository"
        echo "  Backup: $local_head"
        echo "  Live:   $remote_head"
    fi

    # Count ref differences
    local local_ref_count remote_ref_count
    local_ref_count=$(git --git-dir="$git_dir" show-ref 2>/dev/null | wc -l)
    remote_ref_count=$(echo "$remote_refs" | wc -l)

    log_info "Ref count - Backup: $local_ref_count, Live: $remote_ref_count"

    return 0
}

verify_single_backup() {
    local archive="$1"
    local compare_repo="${2:-}"
    local verbose="${3:-false}"
    local quick="${4:-false}"

    local errors=0

    echo ""
    echo "=========================================="
    echo "Verifying: $(basename "$archive")"
    echo "=========================================="

    # Create temp directory
    local temp_dir
    temp_dir=$(mktemp -d)
    trap "rm -rf '$temp_dir'" RETURN

    # Step 1: Archive integrity
    verify_archive_integrity "$archive" || ((errors++))

    # Step 2: Extract
    log_info "Extracting archive..."
    tar -xzf "$archive" -C "$temp_dir"

    local git_dir
    git_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "*.git" | head -1)

    if [[ -z "$git_dir" ]]; then
        log_error "No .git directory found in archive"
        return 1
    fi

    # Step 3: Git structure
    verify_git_structure "$git_dir" || ((errors++))

    # Step 4: Git objects
    verify_git_objects "$git_dir" "$quick" || ((errors++))

    # Step 5: Refs
    verify_refs "$git_dir" "$verbose" || ((errors++))

    # Step 6: LFS
    verify_lfs "$git_dir" "$verbose" || ((errors++))

    # Step 7: Compare with live (optional)
    if [[ -n "$compare_repo" ]]; then
        compare_with_live "$git_dir" "$compare_repo" || ((errors++))
    fi

    # Summary
    echo ""
    if [[ $errors -eq 0 ]]; then
        log_success "All verification checks passed"
        return 0
    else
        log_error "$errors verification check(s) failed"
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================
main() {
    local compare_repo=""
    local verbose="false"
    local quick="false"

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -c|--compare) compare_repo="$2"; shift 2 ;;
            -v|--verbose) verbose="true"; shift ;;
            -q|--quick) quick="true"; shift ;;
            -h|--help) usage; exit 0 ;;
            -*) log_error "Unknown option: $1"; usage; exit 1 ;;
            *) break ;;
        esac
    done

    if [[ $# -lt 1 ]]; then
        log_error "Missing required argument"
        usage
        exit 1
    fi

    local target="$1"
    local total_errors=0
    local verified=0

    if [[ -f "$target" ]]; then
        # Single archive
        verify_single_backup "$target" "$compare_repo" "$verbose" "$quick" || ((total_errors++))
        verified=1
    elif [[ -d "$target" ]]; then
        # Directory of backups
        local archives
        mapfile -t archives < <(find "$target" -name "*_latest.tar.gz" -o -name "*.tar.gz" | sort -u)

        if [[ ${#archives[@]} -eq 0 ]]; then
            log_error "No backup archives found in: $target"
            exit 1
        fi

        log_info "Found ${#archives[@]} backup archive(s)"

        for archive in "${archives[@]}"; do
            verify_single_backup "$archive" "" "$verbose" "$quick" || ((total_errors++))
            ((verified++))
        done
    else
        log_error "Target not found: $target"
        exit 1
    fi

    # Final summary
    echo ""
    echo "=========================================="
    echo "  Verification Summary"
    echo "=========================================="
    echo "  Archives verified: $verified"
    if [[ $total_errors -eq 0 ]]; then
        log_success "All backups verified successfully"
        exit 0
    else
        log_error "Failed verifications: $total_errors"
        exit 1
    fi
}

main "$@"
