#!/bin/bash
# Starts the Notion UI with current AWS credentials from the environment.
# Run this any time credentials rotate or the server needs restarting.

pkill -f "python -m uvicorn.*server:app" 2>/dev/null; sleep 1

cd "$(dirname "$0")/notion" && \
  env AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
      AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
      AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
      AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-west-2}" \
  nohup python -m uvicorn server:app --host 0.0.0.0 --port 8502 > /tmp/notion-ui.log 2>&1 &

sleep 2
tail -3 /tmp/notion-ui.log
echo ""
echo "App running at: ${WORKSHOP_URL}/app/8502/"
