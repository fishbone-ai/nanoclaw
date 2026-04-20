#!/usr/bin/env bash
# Daily standup: fetches urgent + high-priority Linear tasks for Avishay and
# Ohav and posts a personalized message to each in #daily-tasks-check.
#
# Runs via NanoClaw's scheduled-task system. Wake-agent only on failure:
# healthy runs print `{"wakeAgent":false}` at the end.
#
# Required env (injected by container-runner from NanoClaw .env):
#   LINEAR_API_KEY
#   SLACK_BOT_TOKEN

set -uo pipefail

SLACK_CHANNEL="C0AP1M0J7FF"   # #daily-tasks-check

AVISHAY_LINEAR_ID="8f197062-380b-4fa4-98e0-acd0fc08ed55"
OHAV_LINEAR_ID="68135dc9-ea68-43d3-940d-fa319b99412d"

AVISHAY_SLACK_ID="U0AKCGVSHS8"
OHAV_SLACK_ID="U0AJTFLERPZ"

err() { echo "ERROR: $*" >&2; }

if [[ -z "${LINEAR_API_KEY:-}" ]]; then
  err "LINEAR_API_KEY not set"
  echo '{"wakeAgent":true,"data":{"error":"LINEAR_API_KEY not set in container env"}}'
  exit 0
fi
if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
  err "SLACK_BOT_TOKEN not set"
  echo '{"wakeAgent":true,"data":{"error":"SLACK_BOT_TOKEN not set in container env"}}'
  exit 0
fi

# Fetch open Urgent (1) + High (2) priority issues assigned to a Linear user.
get_issues() {
  local user_id="$1"
  curl -sS -X POST https://api.linear.app/graphql \
    -H "Authorization: $LINEAR_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"{ issues(filter: { assignee: { id: { eq: \\\"$user_id\\\" } }, state: { type: { nin: [\\\"completed\\\", \\\"cancelled\\\"] } }, priority: { in: [1, 2] } }) { nodes { identifier title priority url } } }\" }" \
  | python3 -c "
import json, sys
priority_map = {1: '🔴', 2: '🟠'}
data = json.load(sys.stdin)
issues = data.get('data', {}).get('issues', {}).get('nodes', [])
if not issues:
    print('_No urgent or high priority tasks_')
else:
    issues.sort(key=lambda i: i.get('priority', 99))
    for i in issues:
        p = priority_map.get(i.get('priority', 0), '')
        label = f'{p} ' if p else ''
        print(f'• {label}<{i[\"url\"]}|{i[\"identifier\"]}> {i[\"title\"]}')
"
}

# Post a Slack message. Prints "OK" on success, "ERROR: ..." on failure.
post_message() {
  local text="$1"
  local payload
  payload=$(python3 -c "import json,sys; print(json.dumps({'channel': sys.argv[1], 'text': sys.argv[2], 'mrkdwn': True}))" "$SLACK_CHANNEL" "$text")
  curl -sS -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "$payload" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('OK' if d.get('ok') else f'ERROR: {d}')"
}

errors=()

for person in "Avishay:$AVISHAY_LINEAR_ID:$AVISHAY_SLACK_ID" "Ohav:$OHAV_LINEAR_ID:$OHAV_SLACK_ID"; do
  IFS=: read -r name linear_id slack_id <<<"$person"
  issues=$(get_issues "$linear_id") || { errors+=("$name: linear fetch failed"); continue; }
  msg="Good morning <@${slack_id}>! 👋 Here are your open tasks for today:

${issues}

What's the status? Any blockers I can help with?"
  result=$(post_message "$msg")
  if [[ "$result" != "OK" ]]; then
    errors+=("$name: $result")
  fi
done

if [[ ${#errors[@]} -gt 0 ]]; then
  # Escape the error list into a JSON string
  err_json=$(python3 -c "import json,sys; print(json.dumps('; '.join(sys.argv[1:])))" "${errors[@]}")
  echo "{\"wakeAgent\":true,\"data\":{\"error\":$err_json}}"
else
  echo '{"wakeAgent":false}'
fi
