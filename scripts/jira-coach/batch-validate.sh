#!/bin/bash
#
# Batch Validate Jira Tickets
#
# This script validates multiple Jira tickets and generates a single CSV report.
# Usage: ./batch-validate.sh <output-file> <ticket1> <ticket2> ...
#        ./batch-validate.sh report.csv OSC-1234 OSC-1235 OSC-1236
#        cat tickets.txt | xargs ./batch-validate.sh report.csv
#
# # Add to cron: validate all In Progress tickets daily
#  0 9 * * * cd /path/to/repo && \
#      ./scripts/jira-coach/batch-validate.sh \
#      "daily-$(date +%Y%m%d).csv" \
#      $(jira list --status "In Progress" --format=ids)

set -euo pipefail

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <output-file> <ticket1> [ticket2] [ticket3] ..." >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 sprint-report.csv OSC-1234 OSC-1235 OSC-1236" >&2
    echo "  $0 release-report.csv \$(jira list --fixVersion 1.13 --format=ids)" >&2
    echo "  cat tickets.txt | xargs $0 batch-report.csv" >&2
    exit 1
fi

OUTPUT_FILE="$1"
shift
TICKETS=("$@")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
SUCCESS_COUNT=0
FAIL_COUNT=0
TOTAL_COUNT=${#TICKETS[@]}

echo "Batch Validation Report" >&2
echo "======================" >&2
echo "Output: $OUTPUT_FILE" >&2
echo "Tickets: $TOTAL_COUNT" >&2
echo "" >&2

# Validate first ticket (with header)
echo -n "Processing ${TICKETS[0]}... " >&2
if python3 scripts/jira-coach/validate.py "${TICKETS[0]}" --format csv > "$OUTPUT_FILE" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}" >&2
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}✗ FAILED${NC}" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
    # Create empty file with just header if first ticket fails
    echo "ticket_key,ticket_type,summary,status,url,created_at_utc,updated_at_utc,validated_at_utc,why_score,results_score,prove_score,design_score,evidence_score,total_points,max_points,overall_percentage,is_complete,missing_aspects" > "$OUTPUT_FILE"
fi

# Validate remaining tickets (without header)
for ticket in "${TICKETS[@]:1}"; do
    echo -n "Processing $ticket... " >&2
    if python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header 2>/dev/null >> "$OUTPUT_FILE"; then
        echo -e "${GREEN}✓${NC}" >&2
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}✗ FAILED${NC}" >&2
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

# Summary
echo "" >&2
echo "Summary" >&2
echo "-------" >&2
echo "Total:   $TOTAL_COUNT" >&2
echo -e "${GREEN}Success: $SUCCESS_COUNT${NC}" >&2
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}Failed:  $FAIL_COUNT${NC}" >&2
fi

# Calculate statistics from CSV
if [ $SUCCESS_COUNT -gt 0 ]; then
    echo "" >&2
    echo "Quality Statistics" >&2
    echo "------------------" >&2

    # Average score
    AVG_SCORE=$(awk -F',' 'NR>1 {sum+=$16; count++} END {if(count>0) printf "%.1f", sum/count; else print "N/A"}' "$OUTPUT_FILE")
    echo "Average Score: ${AVG_SCORE}%" >&2

    # Complete count
    COMPLETE_COUNT=$(awk -F',' 'NR>1 && $17=="True" {count++} END {print count+0}' "$OUTPUT_FILE")
    echo "Complete: $COMPLETE_COUNT / $SUCCESS_COUNT" >&2

    # Incomplete count
    INCOMPLETE_COUNT=$(awk -F',' 'NR>1 && $17=="False" {count++} END {print count+0}' "$OUTPUT_FILE")
    if [ $INCOMPLETE_COUNT -gt 0 ]; then
        echo -e "${YELLOW}Incomplete: $INCOMPLETE_COUNT${NC}" >&2
    fi
fi

echo "" >&2
echo "Report saved to: $OUTPUT_FILE" >&2

# Exit with error if any failed
if [ $FAIL_COUNT -gt 0 ]; then
    exit 1
fi
