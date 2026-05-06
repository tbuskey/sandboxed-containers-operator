#!/bin/bash
#
# Example usage of jira-coach validation tool
#
# This script demonstrates how to use the Jira ticket validation tool
# to check if tickets have Why, Results, Prove, Design, Evidence information.
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Jira Ticket Validation Example"
echo "==============================="
echo ""

# Check environment variables
if [ -z "${JIRA_URL:-}" ]; then
    echo -e "${RED}Error: JIRA_URL not set${NC}"
    echo "Please set: export JIRA_URL='https://issues.redhat.com'"
    exit 1
fi

if [ -z "${JIRA_TOKEN:-}" ]; then
    echo -e "${RED}Error: JIRA_TOKEN not set${NC}"
    echo "Please set your Jira personal access token:"
    echo "  export JIRA_TOKEN='your-token'"
    exit 1
fi

echo -e "${GREEN}Environment configured:${NC}"
echo "  JIRA_URL: $JIRA_URL"
echo "  JIRA_TOKEN: [set]"
echo ""

# Example 1: Validate a single ticket
echo -e "${YELLOW}Example 1: Validate a single ticket${NC}"
echo "--------------------------------------"
echo "Command: python3 scripts/jira-coach/validate.py OSC-1234"
echo ""

if [ "${1:-}" != "" ]; then
    TICKET="$1"
else
    read -p "Enter a Jira ticket ID to validate (or press Enter to skip): " TICKET
fi

if [ -n "$TICKET" ]; then
    echo ""
    python3 scripts/jira-coach/validate.py "$TICKET"
    echo ""
else
    echo "Skipped."
    echo ""
fi

# Example 2: Get JSON output
echo -e "${YELLOW}Example 2: Get JSON output${NC}"
echo "--------------------------------------"
echo "Command: python3 scripts/jira-coach/validate.py OSC-1234 --json"
echo ""

if [ -n "$TICKET" ]; then
    echo "JSON output for $TICKET:"
    python3 scripts/jira-coach/validate.py "$TICKET" --json | jq '.overall_score, .is_complete, .missing_aspects'
    echo ""
else
    echo "Skipped (no ticket provided)."
    echo ""
fi

# Example 3: Extract specific information
echo -e "${YELLOW}Example 3: Extract specific information with jq${NC}"
echo "--------------------------------------"
echo "Get just the score:"
echo "  python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.overall_score'"
echo ""
echo "Get missing aspects:"
echo "  python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.missing_aspects'"
echo ""
echo "Get recommendations:"
echo "  python3 scripts/jira-coach/validate.py OSC-1234 --json | jq -r '.recommendations[]'"
echo ""
echo "Get PR links:"
echo "  python3 scripts/jira-coach/validate.py OSC-1234 --json | jq -r '.aspects.where.evidence[]'"
echo ""

# Example 4: Verify PRs
echo -e "${YELLOW}Example 4: Verify PR links${NC}"
echo "--------------------------------------"
echo "After getting PR links from a ticket, verify them:"
echo "  python3 scripts/jira-coach/verify_prs.py <pr-url> [<pr-url2> ...]"
echo ""

if [ -n "$TICKET" ]; then
    PR_URLS=$(python3 scripts/jira-coach/validate.py "$TICKET" --json 2>/dev/null | jq -r '.aspects.where.evidence[]' 2>/dev/null || true)

    if [ -n "$PR_URLS" ]; then
        echo "PR links found in $TICKET:"
        echo "$PR_URLS"
        echo ""
        echo "Verifying PRs..."
        python3 scripts/jira-coach/verify_prs.py $PR_URLS 2>/dev/null || echo "Note: Some PRs could not be verified (this is normal for private repos without tokens)"
    else
        echo "No PR links found in $TICKET"
    fi
    echo ""
fi

# Example 5: Batch validation
echo -e "${YELLOW}Example 5: Batch validation${NC}"
echo "--------------------------------------"
echo "Validate multiple tickets:"
cat <<'EOF'
#!/bin/bash
for ticket in OSC-1234 OSC-1235 OSC-1236; do
    echo "Validating $ticket..."
    score=$(python3 scripts/jira-coach/validate.py "$ticket" --json | jq '.overall_score')
    echo "$ticket: ${score}%"
    echo ""
done
EOF
echo ""

# Example 6: CI/CD integration
echo -e "${YELLOW}Example 6: CI/CD integration${NC}"
echo "--------------------------------------"
echo "Enforce minimum completeness score:"
cat <<'EOF'
#!/bin/bash
TICKET_ID="OSC-1234"
MIN_SCORE=75

result=$(python3 scripts/jira-coach/validate.py "$TICKET_ID" --json)
score=$(echo "$result" | jq '.overall_score')

if (( $(echo "$score < $MIN_SCORE" | bc -l) )); then
    echo "Error: Ticket $TICKET_ID is only ${score}% complete (need ${MIN_SCORE}%+)"
    echo "$result" | jq -r '.recommendations[]'
    exit 1
fi

echo "✅ Ticket $TICKET_ID is ${score}% complete"
EOF
echo ""

echo -e "${GREEN}Examples complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Try validating some of your team's tickets"
echo "2. Identify patterns in what's commonly missing"
echo "3. Create templates or checklists based on findings"
echo "4. Integrate into your workflow (git hooks, CI, etc.)"
echo ""
echo "For more information, see scripts/jira-coach/README.md"
