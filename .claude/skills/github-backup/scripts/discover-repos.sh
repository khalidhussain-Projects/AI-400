#!/usr/bin/env bash
#
# GitHub Repository Discovery Script
# Auto-discovers repositories for backup based on user/org membership
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Discover GitHub repositories for backup.

Options:
  -t, --type TYPE      Repository type: all, owner, member (default: all)
  -o, --org ORG        Include repositories from organization
  -u, --user USER      Discover repos for specific user (default: authenticated user)
  -p, --private        Include private repositories
  -P, --public         Include only public repositories
  -f, --forks          Include forked repositories
  -F, --no-forks       Exclude forked repositories
  -a, --archived       Include archived repositories
  -A, --no-archived    Exclude archived repositories
  -l, --limit N        Maximum repositories to return (default: unlimited)
  -j, --json           Output as JSON array
  -c, --config FILE    Output to config file
  -h, --help           Show this help message

Examples:
  # List all your repositories
  $(basename "$0")

  # List repositories from an organization
  $(basename "$0") -o my-org

  # Generate config file with public repos only
  $(basename "$0") --public --no-forks -c config.json

  # Get repos as JSON
  $(basename "$0") -o my-org --json
EOF
}

# ============================================================================
# API Functions
# ============================================================================
github_api() {
    local endpoint="$1"
    local page="${2:-1}"
    local per_page="${3:-100}"

    curl -s \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com${endpoint}?per_page=${per_page}&page=${page}"
}

get_all_pages() {
    local endpoint="$1"
    local page=1
    local all_repos="[]"

    while true; do
        local response
        response=$(github_api "$endpoint" "$page")

        # Check for empty response or error
        if [[ -z "$response" ]] || echo "$response" | jq -e '.message' >/dev/null 2>&1; then
            if [[ $page -eq 1 ]]; then
                log_error "API error: $(echo "$response" | jq -r '.message // "Unknown error"')"
                return 1
            fi
            break
        fi

        # Check if we got any results
        local count
        count=$(echo "$response" | jq 'length')
        [[ "$count" -eq 0 ]] && break

        # Merge results
        all_repos=$(echo "$all_repos $response" | jq -s 'add')

        # Check if there are more pages
        [[ "$count" -lt 100 ]] && break
        ((page++))
    done

    echo "$all_repos"
}

# ============================================================================
# Discovery Functions
# ============================================================================
discover_user_repos() {
    local user="${1:-}"
    local type="${2:-all}"

    if [[ -z "$user" ]]; then
        log_info "Discovering repositories for authenticated user..."
        get_all_pages "/user/repos&type=${type}"
    else
        log_info "Discovering repositories for user: $user"
        get_all_pages "/users/${user}/repos&type=${type}"
    fi
}

discover_org_repos() {
    local org="$1"
    local type="${2:-all}"

    log_info "Discovering repositories for organization: $org"
    get_all_pages "/orgs/${org}/repos&type=${type}"
}

filter_repos() {
    local repos="$1"
    local include_private="${2:-true}"
    local include_forks="${3:-true}"
    local include_archived="${4:-true}"
    local public_only="${5:-false}"

    local filter="."

    # Privacy filter
    if [[ "$public_only" == "true" ]]; then
        filter="$filter | select(.private == false)"
    elif [[ "$include_private" == "false" ]]; then
        filter="$filter | select(.private == false)"
    fi

    # Fork filter
    if [[ "$include_forks" == "false" ]]; then
        filter="$filter | select(.fork == false)"
    fi

    # Archive filter
    if [[ "$include_archived" == "false" ]]; then
        filter="$filter | select(.archived == false)"
    fi

    echo "$repos" | jq "[ .[] | $filter ]"
}

# ============================================================================
# Output Functions
# ============================================================================
output_list() {
    local repos="$1"
    echo "$repos" | jq -r '.[].full_name'
}

output_json() {
    local repos="$1"
    echo "$repos" | jq '[.[].full_name]'
}

output_config() {
    local repos="$1"
    local config_file="$2"

    local repo_list
    repo_list=$(echo "$repos" | jq '[.[].full_name]')

    jq -n \
        --argjson repos "$repo_list" \
        '{
            "repositories": $repos,
            "schedule": "0 2 * * *",
            "storage": {
                "type": "github",
                "branch": "backups"
            },
            "retention": {
                "count": 7
            },
            "notifications": {
                "enabled": false
            }
        }' > "$config_file"

    log_success "Config written to: $config_file"
}

# ============================================================================
# Main
# ============================================================================
main() {
    local type="all"
    local org=""
    local user=""
    local include_private="true"
    local public_only="false"
    local include_forks="true"
    local include_archived="true"
    local limit=0
    local output_format="list"
    local config_file=""

    # Check for token
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
        log_error "GITHUB_TOKEN environment variable is required"
        exit 1
    fi

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -t|--type) type="$2"; shift 2 ;;
            -o|--org) org="$2"; shift 2 ;;
            -u|--user) user="$2"; shift 2 ;;
            -p|--private) include_private="true"; shift ;;
            -P|--public) public_only="true"; shift ;;
            -f|--forks) include_forks="true"; shift ;;
            -F|--no-forks) include_forks="false"; shift ;;
            -a|--archived) include_archived="true"; shift ;;
            -A|--no-archived) include_archived="false"; shift ;;
            -l|--limit) limit="$2"; shift 2 ;;
            -j|--json) output_format="json"; shift ;;
            -c|--config) output_format="config"; config_file="$2"; shift 2 ;;
            -h|--help) usage; exit 0 ;;
            -*) log_error "Unknown option: $1"; usage; exit 1 ;;
            *) break ;;
        esac
    done

    # Discover repositories
    local all_repos="[]"

    if [[ -n "$org" ]]; then
        local org_repos
        org_repos=$(discover_org_repos "$org" "$type")
        all_repos=$(echo "$all_repos $org_repos" | jq -s 'add')
    fi

    if [[ -z "$org" ]] || [[ -n "$user" ]]; then
        local user_repos
        user_repos=$(discover_user_repos "$user" "$type")
        all_repos=$(echo "$all_repos $user_repos" | jq -s 'add')
    fi

    # Remove duplicates
    all_repos=$(echo "$all_repos" | jq 'unique_by(.full_name)')

    # Apply filters
    all_repos=$(filter_repos "$all_repos" "$include_private" "$include_forks" "$include_archived" "$public_only")

    # Apply limit
    if [[ "$limit" -gt 0 ]]; then
        all_repos=$(echo "$all_repos" | jq ".[:$limit]")
    fi

    # Count results
    local count
    count=$(echo "$all_repos" | jq 'length')
    log_info "Found $count repository(ies)"

    # Output
    case "$output_format" in
        list)
            output_list "$all_repos"
            ;;
        json)
            output_json "$all_repos"
            ;;
        config)
            if [[ -z "$config_file" ]]; then
                log_error "Config file path required with -c option"
                exit 1
            fi
            output_config "$all_repos" "$config_file"
            ;;
    esac
}

main "$@"
