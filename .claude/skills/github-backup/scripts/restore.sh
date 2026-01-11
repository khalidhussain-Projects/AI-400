#!/usr/bin/env bash
#
# GitHub Repository Restore Script
# Restores repositories from mirror clone backups
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] <backup-archive> <destination>

Restore a GitHub repository from a mirror backup archive.

Arguments:
  backup-archive    Path to the backup .tar.gz archive
  destination       Where to restore (local path or GitHub URL)

Options:
  -m, --mode MODE   Restore mode: local, github, mirror (default: local)
  -n, --name NAME   New repository name (for github mode)
  -p, --private     Create as private repository (github mode)
  -f, --force       Overwrite existing destination
  -l, --lfs         Push LFS objects after restore
  -h, --help        Show this help message

Examples:
  # Restore to local directory
  $(basename "$0") backups/myrepo_2024-01-15.tar.gz ./restored-repo

  # Restore to new GitHub repository
  $(basename "$0") -m github backups/myrepo_2024-01-15.tar.gz owner/new-repo

  # Mirror push to existing repository
  $(basename "$0") -m mirror -f backups/myrepo_2024-01-15.tar.gz owner/existing-repo
EOF
}

# ============================================================================
# Restore Functions
# ============================================================================
extract_archive() {
    local archive="$1"
    local temp_dir="$2"

    log_info "Extracting archive: $archive"
    tar -xzf "$archive" -C "$temp_dir"

    # Find the .git directory
    local git_dir
    git_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "*.git" | head -1)

    if [[ -z "$git_dir" ]]; then
        log_error "No .git directory found in archive"
        return 1
    fi

    echo "$git_dir"
}

restore_local() {
    local git_dir="$1"
    local destination="$2"
    local force="${3:-false}"

    if [[ -d "$destination" ]]; then
        if [[ "$force" == "true" ]]; then
            log_warn "Removing existing directory: $destination"
            rm -rf "$destination"
        else
            log_error "Destination exists: $destination (use -f to overwrite)"
            return 1
        fi
    fi

    log_info "Cloning to: $destination"
    git clone "$git_dir" "$destination"

    log_success "Repository restored to: $destination"
}

restore_github() {
    local git_dir="$1"
    local destination="$2"
    local repo_name="$3"
    local private="${4:-false}"
    local push_lfs="${5:-false}"

    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        log_error "GITHUB_TOKEN environment variable required for GitHub restore"
        return 1
    fi

    # Parse owner and repo from destination
    local owner repo
    owner=$(echo "$destination" | cut -d'/' -f1)
    repo=$(echo "$destination" | cut -d'/' -f2)
    [[ -n "$repo_name" ]] && repo="$repo_name"

    # Check if repo exists
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${owner}/${repo}")

    if [[ "$http_code" == "200" ]]; then
        log_error "Repository already exists: ${owner}/${repo}"
        log_info "Use mirror mode to push to existing repository"
        return 1
    fi

    # Create new repository
    log_info "Creating repository: ${owner}/${repo}"
    local visibility="public"
    [[ "$private" == "true" ]] && visibility="private"

    local create_response
    create_response=$(curl -s -X POST \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/user/repos" \
        -d "{\"name\":\"${repo}\",\"private\":${private}}")

    if echo "$create_response" | jq -e '.id' > /dev/null 2>&1; then
        log_success "Repository created"
    else
        log_error "Failed to create repository: $(echo "$create_response" | jq -r '.message // "Unknown error"')"
        return 1
    fi

    # Push to new repository
    log_info "Pushing backup to GitHub..."
    (
        cd "$git_dir"
        git remote set-url origin "https://${GITHUB_TOKEN}@github.com/${owner}/${repo}.git"
        git push --mirror
    )

    # Handle LFS if requested
    if [[ "$push_lfs" == "true" ]] && [[ -d "${git_dir}/lfs" ]]; then
        log_info "Pushing LFS objects..."
        (cd "$git_dir" && git lfs push --all origin)
    fi

    log_success "Repository restored to: https://github.com/${owner}/${repo}"
}

restore_mirror() {
    local git_dir="$1"
    local destination="$2"
    local force="${3:-false}"
    local push_lfs="${4:-false}"

    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        log_error "GITHUB_TOKEN environment variable required for mirror restore"
        return 1
    fi

    local owner repo
    owner=$(echo "$destination" | cut -d'/' -f1)
    repo=$(echo "$destination" | cut -d'/' -f2)

    if [[ "$force" != "true" ]]; then
        log_warn "Mirror push will overwrite all refs in ${owner}/${repo}"
        read -p "Continue? [y/N] " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && return 1
    fi

    log_info "Mirror pushing to: ${owner}/${repo}"
    (
        cd "$git_dir"
        git remote set-url origin "https://${GITHUB_TOKEN}@github.com/${owner}/${repo}.git"
        git push --mirror --force
    )

    if [[ "$push_lfs" == "true" ]] && [[ -d "${git_dir}/lfs" ]]; then
        log_info "Pushing LFS objects..."
        (cd "$git_dir" && git lfs push --all origin)
    fi

    log_success "Mirror push complete to: https://github.com/${owner}/${repo}"
}

# ============================================================================
# Main
# ============================================================================
main() {
    local mode="local"
    local repo_name=""
    local private="false"
    local force="false"
    local push_lfs="false"

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -m|--mode) mode="$2"; shift 2 ;;
            -n|--name) repo_name="$2"; shift 2 ;;
            -p|--private) private="true"; shift ;;
            -f|--force) force="true"; shift ;;
            -l|--lfs) push_lfs="true"; shift ;;
            -h|--help) usage; exit 0 ;;
            -*) log_error "Unknown option: $1"; usage; exit 1 ;;
            *) break ;;
        esac
    done

    if [[ $# -lt 2 ]]; then
        log_error "Missing required arguments"
        usage
        exit 1
    fi

    local archive="$1"
    local destination="$2"

    if [[ ! -f "$archive" ]]; then
        log_error "Archive not found: $archive"
        exit 1
    fi

    # Create temp directory
    local temp_dir
    temp_dir=$(mktemp -d)
    trap "rm -rf '$temp_dir'" EXIT

    # Extract archive
    local git_dir
    git_dir=$(extract_archive "$archive" "$temp_dir")

    # Restore based on mode
    case "$mode" in
        local)
            restore_local "$git_dir" "$destination" "$force"
            ;;
        github)
            restore_github "$git_dir" "$destination" "$repo_name" "$private" "$push_lfs"
            ;;
        mirror)
            restore_mirror "$git_dir" "$destination" "$force" "$push_lfs"
            ;;
        *)
            log_error "Unknown mode: $mode"
            exit 1
            ;;
    esac
}

main "$@"
