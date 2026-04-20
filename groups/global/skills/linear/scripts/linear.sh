#!/usr/bin/env bash
set -euo pipefail

# Linear CLI wrapper
# Requires: LINEAR_API_KEY, curl, jq

API="https://api.linear.app/graphql"

if [[ -z "${LINEAR_API_KEY:-}" ]]; then
  echo "Error: LINEAR_API_KEY not set" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

# gql: simple inline query (no variables, manual escaping)
gql() {
  local query="$1"
  curl -s -X POST "$API" \
    -H "Content-Type: application/json" \
    -H "Authorization: $LINEAR_API_KEY" \
    -d "{\"query\": \"$query\"}"
}

# gql_json: accepts a full JSON payload built with jq — safe for arbitrary strings
gql_json() {
  local payload="$1"
  curl -s -X POST "$API" \
    -H "Content-Type: application/json" \
    -H "Authorization: $LINEAR_API_KEY" \
    --data-binary "$payload"
}

# ---------------------------------------------------------------------------
# Team cache
# ---------------------------------------------------------------------------

cache_key="$(printf '%s' "$LINEAR_API_KEY" | cksum | awk '{print $1}')"
TEAMS_CACHE="${LINEAR_TEAMS_CACHE:-/tmp/linear-teams-${cache_key}.json}"

refresh_teams_cache() {
  gql "{ teams { nodes { id key name } } }" > "$TEAMS_CACHE"
}

load_teams() {
  if [[ ! -f "$TEAMS_CACHE" ]]; then
    refresh_teams_cache
  fi
  cat "$TEAMS_CACHE"
}

resolve_team_id() {
  local team_key="${1:-}"
  local team_id=""
  if [[ -z "$team_key" ]]; then
    team_key="${LINEAR_DEFAULT_TEAM:-}"
  fi
  if [[ -z "$team_key" ]]; then
    echo "Error: team key required. Run 'linear.sh teams' to list teams." >&2
    return 1
  fi
  team_id=$(load_teams | jq -r --arg key "$team_key" '.data.teams.nodes[] | select(.key == $key) | .id' | head -n1)
  if [[ -z "$team_id" || "$team_id" == "null" ]]; then
    refresh_teams_cache
    team_id=$(load_teams | jq -r --arg key "$team_key" '.data.teams.nodes[] | select(.key == $key) | .id' | head -n1)
  fi
  if [[ -z "$team_id" || "$team_id" == "null" ]]; then
    local team_keys
    team_keys=$(load_teams | jq -r '.data.teams.nodes[].key' | tr '\n' ' ')
    echo "Unknown team: $team_key (available: $team_keys)" >&2
    return 1
  fi
  echo "$team_id"
}

# ---------------------------------------------------------------------------
# Issue / cycle UUID resolvers
# ---------------------------------------------------------------------------

# resolve_issue_uuid: TEAM-123 → internal UUID
resolve_issue_uuid() {
  local issue_id="$1"
  local team_key="${issue_id%%-*}"
  local issue_num="${issue_id##*-}"
  local uuid
  uuid=$(gql "{ issues(filter: { number: { eq: $issue_num }, team: { key: { eq: \\\"$team_key\\\" } } }) { nodes { id } } }" \
    | jq -r '.data.issues.nodes[0].id')
  if [[ -z "$uuid" || "$uuid" == "null" ]]; then
    echo "Could not find issue: $issue_id" >&2
    return 1
  fi
  echo "$uuid"
}

# resolve_cycle_id: team_key + (number | "current") → cycle UUID
resolve_cycle_id() {
  local team_key="$1"
  local cycle_ref="${2:-current}"
  local team_id
  team_id=$(resolve_team_id "$team_key") || return 1

  local cycles_json
  cycles_json=$(gql "{ team(id: \\\"$team_id\\\") { cycles { nodes { id number name startsAt endsAt } } } }" \
    | jq '.data.team.cycles.nodes')

  local cycle_id
  if [[ "$cycle_ref" == "current" || "$cycle_ref" == "active" ]]; then
    local today
    today=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    cycle_id=$(echo "$cycles_json" \
      | jq -r --arg today "$today" \
        '.[] | select(.startsAt <= $today and .endsAt >= $today) | .id' \
      | head -n1)
  else
    cycle_id=$(echo "$cycles_json" \
      | jq -r --argjson num "$cycle_ref" '.[] | select(.number == $num) | .id' \
      | head -n1)
  fi

  if [[ -z "$cycle_id" || "$cycle_id" == "null" ]]; then
    echo "Could not find cycle: $cycle_ref for team $team_key" >&2
    return 1
  fi
  echo "$cycle_id"
}

# ---------------------------------------------------------------------------
# Status / workflow helpers
# ---------------------------------------------------------------------------

get_state_id() {
  local team_key="$1"
  local state_name="$2"
  local team_id
  team_id=$(resolve_team_id "$team_key") || return 1
  case "$state_name" in
    todo)     state_name="Todo" ;;
    progress) state_name="In Progress" ;;
    review)   state_name="In Review" ;;
    done)     state_name="Done" ;;
    blocked)  state_name="Blocked" ;;
    backlog)  state_name="Backlog" ;;
  esac
  gql "{ workflowStates(filter: { team: { id: { eq: \\\"$team_id\\\" } }, name: { eq: \\\"$state_name\\\" } }) { nodes { id } } }" \
    | jq -r '.data.workflowStates.nodes[0].id'
}

# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

format_issues() {
  jq -r '.data | .. | .nodes? // empty | .[] | select(.identifier) |
    "[\(.priorityLabel // "—")] \(.identifier): \(.title) (\(.state.name)) \(if .assignee then "→ " + .assignee.name else "" end)"' 2>/dev/null \
    || echo "No issues found"
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd="${1:-help}"
shift || true

case "$cmd" in

  # ── Browse ────────────────────────────────────────────────────────────────

  my-issues)
    gql "{ viewer { assignedIssues(first: 20, filter: { state: { type: { nin: [\\\"completed\\\", \\\"canceled\\\"] } } }) { nodes { identifier title state { name } priority priorityLabel } } } }" \
      | format_issues
    ;;

  my-todos)
    gql "{ viewer { assignedIssues(first: 20, filter: { state: { type: { eq: \\\"unstarted\\\" } } }) { nodes { identifier title state { name } priority priorityLabel } } } }" \
      | format_issues
    ;;

  urgent)
    gql "{ issues(filter: { priority: { lte: 2 }, state: { type: { nin: [\\\"completed\\\", \\\"canceled\\\"] } } }, first: 20) { nodes { identifier title state { name } priority priorityLabel assignee { name } } } }" \
      | format_issues
    ;;

  team)
    team_key="${1:-}"
    team_id=$(resolve_team_id "$team_key") || exit 1
    gql "{ team(id: \\\"$team_id\\\") { issues(first: 30, filter: { state: { type: { nin: [\\\"completed\\\", \\\"canceled\\\"] } } }) { nodes { identifier title state { name } priority priorityLabel assignee { name } } } } }" \
      | format_issues
    ;;

  project)
    project_name="${1:-}"
    if [[ -z "$project_name" ]]; then
      echo "Usage: linear.sh project <name>" >&2; exit 1
    fi
    gql "{ projects(filter: { name: { containsIgnoreCase: \\\"$project_name\\\" } }, first: 1) { nodes { issues(first: 30, filter: { state: { type: { nin: [\\\"completed\\\", \\\"canceled\\\"] } } }) { nodes { identifier title state { name } priority priorityLabel assignee { name } } } } } }" \
      | format_issues
    ;;

  issue)
    issue_id="${1:-}"
    if [[ -z "$issue_id" ]]; then
      echo "Usage: linear.sh issue <TEAM-123>" >&2; exit 1
    fi
    team_key="${issue_id%%-*}"
    issue_num="${issue_id##*-}"
    gql "{ issues(filter: { number: { eq: $issue_num }, team: { key: { eq: \\\"$team_key\\\" } } }) { nodes { identifier title description state { name } priority priorityLabel assignee { name } project { name } team { name } cycle { number name } createdAt dueDate } } }" \
      | jq -r '.data.issues.nodes[0] | "
\(.identifier): \(.title)
State: \(.state.name) | Priority: \(.priorityLabel // "None") | Assignee: \(.assignee.name // "Unassigned")
Project: \(.project.name // "None") | Team: \(.team.name) | Cycle: \(if .cycle then "#" + (.cycle.number | tostring) + " " + .cycle.name else "None" end)
Created: \(.createdAt | split("T")[0])
\(if .dueDate then "Due: " + .dueDate else "" end)

\(.description // "No description")
"'
    ;;

  branch)
    issue_id="${1:-}"
    if [[ -z "$issue_id" ]]; then
      echo "Usage: linear.sh branch <TEAM-123>" >&2; exit 1
    fi
    team_key="${issue_id%%-*}"
    issue_num="${issue_id##*-}"
    gql "{ issues(filter: { number: { eq: $issue_num }, team: { key: { eq: \\\"$team_key\\\" } } }) { nodes { branchName } } }" \
      | jq -r '.data.issues.nodes[0].branchName'
    ;;

  teams)
    refresh_teams_cache
    jq -r '.data.teams.nodes[] | "\(.key)\t\(.name)"' "$TEAMS_CACHE"
    ;;

  projects)
    gql "{ projects(first: 20) { nodes { name state progress startDate targetDate teams { nodes { name } } } } }" \
      | jq -r '.data.projects.nodes[] | "\(.name) [\(.state)] - \((.progress * 100) | floor)% complete \(if .targetDate then "(due " + .targetDate + ")" else "" end)"'
    ;;

  # ── Actions ───────────────────────────────────────────────────────────────

  create)
    # Usage: create <TEAM_KEY> "Title" ["Description"] [--priority <level>] [--cycle <number|current>]
    team_key="${1:-}"
    title="${2:-}"
    description="${3:-}"

    # Handle LINEAR_DEFAULT_TEAM shorthand (no team key given)
    if [[ -z "$title" && -n "${LINEAR_DEFAULT_TEAM:-}" ]]; then
      team_key="$LINEAR_DEFAULT_TEAM"
      title="${1:-}"
      description="${2:-}"
      shift 2 || true
    else
      shift 3 || true
    fi

    if [[ -z "$team_key" || -z "$title" ]]; then
      echo "Usage: linear.sh create <TEAM_KEY> \"Title\" [\"Description\"] [--priority urgent|high|medium|low|none] [--cycle <number|current>]" >&2
      exit 1
    fi

    # Parse optional flags
    priority_val=""
    cycle_ref=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --priority)
          shift
          case "${1:-}" in
            urgent) priority_val=1 ;;
            high)   priority_val=2 ;;
            medium) priority_val=3 ;;
            low)    priority_val=4 ;;
            none)   priority_val=0 ;;
            *) echo "Unknown priority: ${1:-}" >&2; exit 1 ;;
          esac
          shift
          ;;
        --cycle)
          shift
          cycle_ref="${1:-}"
          shift
          ;;
        *) shift ;;
      esac
    done

    team_id=$(resolve_team_id "$team_key") || exit 1

    # Build input object safely with jq
    input=$(jq -n \
      --arg teamId "$team_id" \
      --arg title "$title" \
      --arg desc "$description" \
      '{teamId: $teamId, title: $title, description: $desc}')

    if [[ -n "$priority_val" ]]; then
      input=$(echo "$input" | jq --argjson p "$priority_val" '. + {priority: $p}')
    fi

    payload=$(jq -n \
      --argjson input "$input" \
      '{query: "mutation($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id identifier title url } } }", variables: {input: $input}}')

    result=$(gql_json "$payload")
    issue_uuid=$(echo "$result" | jq -r '.data.issueCreate.issue.id')
    issue_key=$(echo "$result"  | jq -r '.data.issueCreate.issue.identifier')
    issue_url=$(echo "$result"  | jq -r '.data.issueCreate.issue.url')

    echo "$result" | jq -r 'if .data.issueCreate.success then "Created: \(.data.issueCreate.issue.identifier) - \(.data.issueCreate.issue.title)\n\(.data.issueCreate.issue.url)" else "Error: " + (.errors[0].message // "Unknown error") end'

    # Link to cycle if requested
    if [[ -n "$cycle_ref" ]]; then
      cycle_id=$(resolve_cycle_id "$team_key" "$cycle_ref") || exit 1
      link_result=$(gql_json "$(jq -n \
        --arg id "$issue_uuid" \
        --arg cycleId "$cycle_id" \
        '{query: "mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success } }", variables: {id: $id, input: {cycleId: $cycleId}}}')")
      echo "$link_result" | jq -r 'if .data.issueUpdate.success then "→ Added to cycle" else "Cycle link failed: " + (.errors[0].message // "unknown") end'
    fi
    ;;

  comment)
    issue_id="${1:-}"
    body="${2:-}"
    if [[ -z "$issue_id" || -z "$body" ]]; then
      echo "Usage: linear.sh comment <TEAM-123> \"Comment text\"" >&2; exit 1
    fi
    issue_uuid=$(resolve_issue_uuid "$issue_id") || exit 1
    result=$(gql_json "$(jq -n \
      --arg issueId "$issue_uuid" \
      --arg body "$body" \
      '{query: "mutation($input: CommentCreateInput!) { commentCreate(input: $input) { success } }", variables: {input: {issueId: $issueId, body: $body}}}')")
    echo "$result" | jq -r 'if .data.commentCreate.success then "Comment added" else "Error: " + (.errors[0].message // "Unknown error") end'
    ;;

  status)
    issue_id="${1:-}"
    new_status="${2:-}"
    if [[ -z "$issue_id" || -z "$new_status" ]]; then
      echo "Usage: linear.sh status <TEAM-123> <todo|progress|review|done|blocked>" >&2; exit 1
    fi
    team_key="${issue_id%%-*}"
    state_id=$(get_state_id "$team_key" "$new_status")
    if [[ -z "$state_id" || "$state_id" == "null" ]]; then
      echo "Could not find state: $new_status for team $team_key" >&2; exit 1
    fi
    issue_uuid=$(resolve_issue_uuid "$issue_id") || exit 1
    result=$(gql_json "$(jq -n \
      --arg id "$issue_uuid" \
      --arg stateId "$state_id" \
      '{query: "mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success issue { identifier state { name } } } }", variables: {id: $id, input: {stateId: $stateId}}}')")
    echo "$result" | jq -r 'if .data.issueUpdate.success then "Updated \(.data.issueUpdate.issue.identifier) → \(.data.issueUpdate.issue.state.name)" else "Error: " + (.errors[0].message // "Unknown error") end'
    ;;

  priority)
    issue_id="${1:-}"
    priority="${2:-}"
    if [[ -z "$issue_id" || -z "$priority" ]]; then
      echo "Usage: linear.sh priority <TEAM-123> <urgent|high|medium|low|none>" >&2; exit 1
    fi
    case "$priority" in
      urgent) pval=1 ;;
      high)   pval=2 ;;
      medium) pval=3 ;;
      low)    pval=4 ;;
      none)   pval=0 ;;
      *) echo "Unknown priority: $priority" >&2; exit 1 ;;
    esac
    issue_uuid=$(resolve_issue_uuid "$issue_id") || exit 1
    result=$(gql_json "$(jq -n \
      --arg id "$issue_uuid" \
      --argjson pval "$pval" \
      '{query: "mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success issue { identifier priorityLabel } } }", variables: {id: $id, input: {priority: $pval}}}')")
    echo "$result" | jq -r 'if .data.issueUpdate.success then "Updated \(.data.issueUpdate.issue.identifier) → \(.data.issueUpdate.issue.priorityLabel)" else "Error: " + (.errors[0].message // "Unknown error") end'
    ;;

  assign)
    issue_id="${1:-}"
    user_name="${2:-}"
    if [[ -z "$issue_id" || -z "$user_name" ]]; then
      echo "Usage: linear.sh assign <TEAM-123> <userName>" >&2; exit 1
    fi
    user_id=$(gql_json "$(jq -n --arg name "$user_name" \
      '{query: "{ users(filter: { name: { containsIgnoreCase: $name } }) { nodes { id name } } }", variables: {name: $name}}')" \
      | jq -r '.data.users.nodes[0].id')
    if [[ -z "$user_id" || "$user_id" == "null" ]]; then
      echo "Could not find user: $user_name" >&2; exit 1
    fi
    issue_uuid=$(resolve_issue_uuid "$issue_id") || exit 1
    result=$(gql_json "$(jq -n \
      --arg id "$issue_uuid" \
      --arg assigneeId "$user_id" \
      '{query: "mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success issue { identifier assignee { name } } } }", variables: {id: $id, input: {assigneeId: $assigneeId}}}')")
    echo "$result" | jq -r 'if .data.issueUpdate.success then "Assigned \(.data.issueUpdate.issue.identifier) → \(.data.issueUpdate.issue.assignee.name)" else "Error: " + (.errors[0].message // "Unknown error") end'
    ;;

  # ── Cycles ────────────────────────────────────────────────────────────────

  cycles)
    # Usage: cycles [TEAM_KEY]
    team_key="${1:-${LINEAR_DEFAULT_TEAM:-}}"
    if [[ -z "$team_key" ]]; then
      echo "Usage: linear.sh cycles <TEAM_KEY>" >&2; exit 1
    fi
    team_id=$(resolve_team_id "$team_key") || exit 1
    gql "{ team(id: \\\"$team_id\\\") { cycles(first: 20) { nodes { number name startsAt endsAt issues { nodes { identifier } } } } } }" \
      | jq -r '.data.team.cycles.nodes[] | "#\(.number) \(.name) [\(.startsAt | split("T")[0]) → \(.endsAt | split("T")[0])] — \(.issues.nodes | length) issue(s)"'
    ;;

  cycle)
    # Usage: cycle <TEAM_KEY> [number|current]  — list issues in a cycle
    team_key="${1:-}"
    cycle_ref="${2:-current}"
    if [[ -z "$team_key" ]]; then
      echo "Usage: linear.sh cycle <TEAM_KEY> [number|current]" >&2; exit 1
    fi
    team_id=$(resolve_team_id "$team_key") || exit 1
    cycles_json=$(gql "{ team(id: \\\"$team_id\\\") { cycles { nodes { id number name startsAt endsAt issues { nodes { identifier title state { name } priority priorityLabel assignee { name } } } } } } }" \
      | jq '.data.team.cycles.nodes')

    if [[ "$cycle_ref" == "current" || "$cycle_ref" == "active" ]]; then
      today=$(date -u +%Y-%m-%dT%H:%M:%SZ)
      cycle_data=$(echo "$cycles_json" \
        | jq --arg today "$today" '.[] | select(.startsAt <= $today and .endsAt >= $today)' \
        | head -c 999999)
    else
      cycle_data=$(echo "$cycles_json" \
        | jq --argjson num "$cycle_ref" '.[] | select(.number == $num)')
    fi

    if [[ -z "$cycle_data" || "$cycle_data" == "null" ]]; then
      echo "No cycle found for: $cycle_ref" >&2; exit 1
    fi

    echo "$cycle_data" | jq -r '"=== Cycle #\(.number): \(.name) [\(.startsAt | split("T")[0]) → \(.endsAt | split("T")[0])] ==="'
    echo "$cycle_data" | jq -r '.issues.nodes[] | "[\(.priorityLabel // "—")] \(.identifier): \(.title) (\(.state.name)) \(if .assignee then "→ " + .assignee.name else "" end)"'
    ;;

  cycle-create)
    # Usage: cycle-create <TEAM_KEY> "Name" <YYYY-MM-DD> <YYYY-MM-DD>
    team_key="${1:-}"
    name="${2:-}"
    start_date="${3:-}"
    end_date="${4:-}"
    if [[ -z "$team_key" || -z "$name" || -z "$start_date" || -z "$end_date" ]]; then
      echo "Usage: linear.sh cycle-create <TEAM_KEY> \"Name\" <start YYYY-MM-DD> <end YYYY-MM-DD>" >&2; exit 1
    fi
    team_id=$(resolve_team_id "$team_key") || exit 1
    result=$(gql_json "$(jq -n \
      --arg teamId "$team_id" \
      --arg name "$name" \
      --arg startsAt "${start_date}T00:00:00.000Z" \
      --arg endsAt "${end_date}T00:00:00.000Z" \
      '{query: "mutation($input: CycleCreateInput!) { cycleCreate(input: $input) { success cycle { id number name startsAt endsAt } } }", variables: {input: {teamId: $teamId, name: $name, startsAt: $startsAt, endsAt: $endsAt}}}')")
    echo "$result" | jq -r 'if .data.cycleCreate.success then "Created: Cycle #\(.data.cycleCreate.cycle.number) \(.data.cycleCreate.cycle.name) [\(.data.cycleCreate.cycle.startsAt | split("T")[0]) → \(.data.cycleCreate.cycle.endsAt | split("T")[0])]" else "Error: " + (.errors[0].message // "Unknown error") end'
    ;;

  cycle-add)
    # Usage: cycle-add <ISSUE_ID> [TEAM_KEY] [cycle_number|current]
    issue_id="${1:-}"
    team_key="${2:-${issue_id%%-*}}"
    cycle_ref="${3:-current}"
    if [[ -z "$issue_id" ]]; then
      echo "Usage: linear.sh cycle-add <TEAM-123> [TEAM_KEY] [cycle_number|current]" >&2; exit 1
    fi
    issue_uuid=$(resolve_issue_uuid "$issue_id") || exit 1
    cycle_id=$(resolve_cycle_id "$team_key" "$cycle_ref") || exit 1
    result=$(gql_json "$(jq -n \
      --arg id "$issue_uuid" \
      --arg cycleId "$cycle_id" \
      '{query: "mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success issue { identifier } } }", variables: {id: $id, input: {cycleId: $cycleId}}}')")
    echo "$result" | jq -r 'if .data.issueUpdate.success then "\(.data.issueUpdate.issue.identifier) → added to cycle" else "Error: " + (.errors[0].message // "Unknown error") end'
    ;;

  cycle-remove)
    # Usage: cycle-remove <ISSUE_ID>
    issue_id="${1:-}"
    if [[ -z "$issue_id" ]]; then
      echo "Usage: linear.sh cycle-remove <TEAM-123>" >&2; exit 1
    fi
    issue_uuid=$(resolve_issue_uuid "$issue_id") || exit 1
    result=$(gql_json "$(jq -n \
      --arg id "$issue_uuid" \
      '{query: "mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success issue { identifier } } }", variables: {id: $id, input: {cycleId: null}}}')")
    echo "$result" | jq -r 'if .data.issueUpdate.success then "\(.data.issueUpdate.issue.identifier) → removed from cycle" else "Error: " + (.errors[0].message // "Unknown error") end'
    ;;

  # ── Overviews ─────────────────────────────────────────────────────────────

  standup)
    echo "=== 📊 Daily Standup ==="
    echo ""
    echo "🎯 YOUR TODOS:"
    gql "{ viewer { assignedIssues(first: 10, filter: { state: { type: { eq: \\\"unstarted\\\" } } }) { nodes { identifier title priorityLabel } } } }" \
      | jq -r '.data.viewer.assignedIssues.nodes // [] | sort_by(.priorityLabel) | .[] | "  [\(.priorityLabel // "—")] \(.identifier): \(.title)"'
    echo ""
    echo "🚧 IN PROGRESS (yours):"
    gql "{ viewer { assignedIssues(first: 10, filter: { state: { type: { eq: \\\"started\\\" } } }) { nodes { identifier title state { name } } } } }" \
      | jq -r '.data.viewer.assignedIssues.nodes // [] | .[] | "  \(.identifier): \(.title) (\(.state.name))"'
    echo ""
    echo "🔴 BLOCKED (team-wide):"
    gql "{ issues(filter: { state: { name: { in: [\\\"Blocked\\\", \\\"Paused\\\"] } } }, first: 10) { nodes { identifier title assignee { name } } } }" \
      | jq -r '.data.issues.nodes // [] | .[] | "  \(.identifier): \(.title) → \(.assignee.name // "unassigned")"'
    echo ""
    echo "✅ RECENTLY DONE (last 7 days):"
    week_ago=$(date -d '7 days ago' +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d)
    gql "{ issues(filter: { state: { type: { eq: \\\"completed\\\" } }, completedAt: { gte: \\\"$week_ago\\\" } }, first: 10) { nodes { identifier title completedAt assignee { name } } } }" \
      | jq -r '.data.issues.nodes // [] | .[] | "  \(.identifier): \(.title) → \(.assignee.name // "unassigned")"'
    ;;

  # ── Help ──────────────────────────────────────────────────────────────────

  help|*)
    echo "Linear CLI - Manage issues, cycles, and projects"
    echo ""
    echo "Browse:"
    echo "  my-issues                          Your assigned open issues"
    echo "  my-todos                           Your Todo items"
    echo "  urgent                             Urgent/High priority issues (all)"
    echo "  teams                              List available teams"
    echo "  team [TEAM_KEY]                    Team issues (uses LINEAR_DEFAULT_TEAM if set)"
    echo "  project <name>                     Project issues"
    echo "  issue <ID>                         Issue details (incl. cycle)"
    echo "  branch <ID>                        Get Linear branch name for GitHub"
    echo "  projects                           All projects with progress"
    echo "  standup                            Daily standup summary"
    echo ""
    echo "Actions:"
    echo "  create <TEAM_KEY> \"title\" [\"desc\"] [--priority urgent|high|medium|low|none] [--cycle <number|current>]"
    echo "  comment <ID> \"text\"               Add comment"
    echo "  status  <ID> <todo|progress|review|done|blocked>   Update status"
    echo "  priority <ID> <urgent|high|medium|low|none>        Set priority"
    echo "  assign  <ID> <userName>            Assign to user"
    echo ""
    echo "Cycles:"
    echo "  cycles [TEAM_KEY]                  List all cycles"
    echo "  cycle  <TEAM_KEY> [number|current] Issues in a cycle (default: current)"
    echo "  cycle-create <TEAM_KEY> \"name\" <start YYYY-MM-DD> <end YYYY-MM-DD>"
    echo "  cycle-add    <ID> [TEAM_KEY] [number|current]   Add issue to cycle"
    echo "  cycle-remove <ID>                  Remove issue from its cycle"
    ;;
esac
