# Jira Coach - Complete Ticket Validation & Feature Assembly

A comprehensive toolkit for ensuring Jira Feature/Epic tickets are complete, well-documented, and properly linked to code changes.

## Overview

Jira Coach provides two main capabilities:

1. **Validate** (`validate.py`) - Evaluate individual tickets for completeness
2. **Assemble** (`assemble.py`) - Gather a feature and all its associated stories with PR links

Both tools help ensure tickets have the critical information needed for effective planning, implementation, and tracking.

## The Five Pillars Framework

Complete tickets should have:

- **Why** - Business justification and purpose
- **Results** - What the final product looks like (objects created, UI elements, log entries)
- **Prove** - How end users deploy/use the feature to produce the Results
- **Design** - Implementation details (what end users don't see)
- **Evidence** - Code location (PR/MR links) AND testing proof

## Quick Start

### 1. Prerequisites

- Python 3.x
- `requests` library:
  ```bash
  pip install requests
  ```
- Jira API credentials (Personal Access Token)

### 2. Setup Environment Variables

**For Red Hat Jira (on-premise):**
```bash
export JIRA_URL="https://issues.redhat.com"
export JIRA_TOKEN="your-personal-access-token"
```

**For Atlassian Cloud:**
```bash
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@company.com"
export JIRA_TOKEN="your-api-token"
```

Add these to your `~/.bashrc` or `~/.zshrc` to persist across sessions.

### 3. Get a Jira Personal Access Token

**For Red Hat Jira:**
- Go to https://issues.redhat.com
- Click your profile → Personal Settings → Personal Access Tokens
- Create a new token and copy it

**For Atlassian Cloud:**
- Go to https://id.atlassian.com/manage-profile/security/api-tokens
- Create API token
- You'll need both your email and the token

## Tools

### Validate - Check Ticket Completeness

Evaluates a single ticket for the Why, Results, Prove, Design, Evidence framework.

**Usage:**
```bash
# As a Claude Code skill
"Check if OSC-1234 has all required information"

# Direct command line - text output (default)
python3 scripts/jira-coach/validate.py OSC-1234

# JSON output (complete data)
python3 scripts/jira-coach/validate.py OSC-1234 --format json

# CSV output (for spreadsheets)
python3 scripts/jira-coach/validate.py OSC-1234 --format csv

# CSV without header (for batch processing)
python3 scripts/jira-coach/validate.py OSC-1234 --format csv --no-header

# Save to file
python3 scripts/jira-coach/validate.py OSC-1234 --format json --output validation.json
python3 scripts/jira-coach/validate.py OSC-1234 --format csv --output validation.csv
```

**Output:**
- Overall completeness score (0-100%, target: 75%+)
- Individual scores for Why, Results, Prove, Design, Evidence (0-3 each)
- Evidence found for each aspect
- Specific suggestions for improvement
- Coaching on next steps

**When to use:**
- Before starting work on a ticket
- To check if a ticket is ready to be closed
- When reviewing ticket quality
- As part of ticket creation process

See [`README-validate.md`](./README-validate.md) for detailed validation documentation.

### Assemble - Gather Feature with Stories & PRs

Retrieves a feature and all associated stories with their PR/MR links.

**Usage:**
```bash
# As a Claude Code skill
"Assemble feature OSC-1234"

# Direct command line
python3 scripts/jira-coach/assemble.py OSC-1234
python3 scripts/jira-coach/assemble.py https://issues.redhat.com/browse/OSC-1234

# JSON output
python3 scripts/jira-coach/assemble.py OSC-1234 --json
```

**Output:**
- Feature overview (summary, status, assignee)
- Feature-level PR/MR links
- All associated stories grouped by status
- PR/MR links for each story
- Summary statistics
- Identification of stories missing PR links

**When to use:**
- To see the complete scope of a feature
- Before closing a feature (verify all stories have PRs)
- For code review preparation
- When creating release notes

### Verify PRs - Check PR/MR Link Status

Verifies that PR/MR URLs actually exist and checks their status.

**Usage:**
```bash
python3 scripts/jira-coach/verify_prs.py <pr-url> [<pr-url2> ...]

# With authentication for private repos
python3 scripts/jira-coach/verify_prs.py --github-token <token> <pr-url>
python3 scripts/jira-coach/verify_prs.py --gitlab-token <token> <pr-url>

# JSON output
python3 scripts/jira-coach/verify_prs.py <pr-url> --json
```

**Output:**
- Verification status (exists, not found, error)
- PR/MR state (open, closed, merged)
- Title, author, timestamps
- Summary statistics

**When to use:**
- After assembling a feature to verify all PRs
- When cross-referencing ticket claims with actual code
- To check if PRs are merged before closing tickets

## Common Workflows

### 1. Create a New Feature Ticket

```bash
# After creating the ticket in Jira, validate it
python3 scripts/jira-coach/validate.py OSC-1234

# Claude will coach you to add missing Why, What, How information
```

### 2. Before Closing a Feature

```bash
# Validate the feature ticket itself
python3 scripts/jira-coach/validate.py OSC-1234

# Assemble all stories to verify PR links
python3 scripts/jira-coach/assemble.py OSC-1234

# Check all PRs are merged
python3 scripts/jira-coach/assemble.py OSC-1234 --json | \
  jq -r '.. | .pr_mr_urls? // [] | .[]' | \
  xargs python3 scripts/jira-coach/verify_prs.py
```

### 3. Sprint Review Preparation

```bash
# For each feature in the sprint, get complete picture
for feature in OSC-1234 OSC-1235 OSC-1236; do
    echo "=== $feature ==="
    
    # Validate completeness
    python3 scripts/jira-coach/validate.py "$feature" --json | \
      jq '{score: .overall_score, complete: .is_complete}'
    
    # Get story count and PR count
    python3 scripts/jira-coach/assemble.py "$feature" --json | \
      jq '{stories: (.stories | length), prs: (.stories | map(.pr_mr_urls | length) | add)}'
done
```

### 4. Continuous Improvement

Ask Claude via the jira-coach skill to:
- Validate tickets when they're created
- Re-check as information is added
- Review before transitioning status
- Verify before closing

## Using with Claude Code

The easiest way to use these tools is through Claude Code's skills system:

```
# Validate a ticket
Check if OSC-1234 has all required information

# Assemble a feature
Assemble feature OSC-1234

# Comprehensive review
Review feature OSC-1234 and all its stories
```

Claude will:
1. Run the appropriate tool(s)
2. Analyze the results
3. Provide coaching on what's missing
4. Cross-reference PR links with actual code
5. Guide you through improvements iteratively

## Understanding the Validation Scoring

### Individual Aspect Scores (0-3)

- **3** ✅ = Strong (comprehensive, well-documented)
- **2** ✓  = Adequate (present with reasonable detail)
- **1** ⚠️  = Weak (brief mention, lacks detail)
- **0** ❌ = Missing entirely

### Overall Score (0-100%)

Calculated as: `(sum of aspect scores / 15) × 100`

**Target:** 75%+ for a complete ticket

### Completeness Criteria

A ticket is considered complete when:
- Overall score ≥ 75%
- No aspect has a score of 0

### Context-Aware Scoring

The tools adjust expectations based on:
- **Ticket type**: Epics/Features need less implementation detail than Stories
- **Status**: Done tickets must have PR links
- **Content quality**: Multiple pieces of evidence score higher

## Philosophy: Iterative Improvement

**Not everything needs to be complete immediately.**

The tools recognize that tickets evolve:

- **New tickets**: Focus on Why and What first
- **In Progress**: How should be documented, Where is being added
- **Done/Closed**: Where (PR links) is CRITICAL

Use these tools throughout the ticket lifecycle:
1. **At creation**: Validate Why and What are clear
2. **Before starting work**: Ensure How is outlined
3. **During implementation**: Add PR links as they're created
4. **Before closing**: Verify all five aspects are complete

## Example Output

### Validation Output

```
================================================================================
JIRA TICKET VALIDATION: OSC-1234
================================================================================
Summary: Implement peer pods authentication
Type: Feature
Status: In Progress
URL: https://issues.redhat.com/browse/OSC-1234

⚠️  INCOMPLETE - Score: 67% (target: 75%+)
   Missing: Prove, Design

PILLAR SCORES:
----------------------------------------
  Why          3/3  ✅
  Results      2/3  ✓ 
  Prove        1/3  ⚠️ 
  Design       1/3  ⚠️ 
  Evidence     3/3  ✅
----------------------------------------
  Overall      67%  (10/15 points)

================================================================================
VALIDATION DETAILS
================================================================================

✅ Why (Purpose & Justification)
   Score: 3/3
   Evidence found:
     1. Customer requests for better authentication in confidential containers
     2. Security team requires mutual TLS for peer-to-peer communication

✓  Results (What Final Product Looks Like)
   Score: 2/3
   Evidence found:
     1. Creates peer-pod-controller Deployment
     2. Logs show authentication status
   Suggestions:
     • Add more concrete details about the Results
     • List specific objects created, UI elements, or log entries

⚠️  Prove (How Users Deploy/Use)
   Score: 1/3
   Suggestions:
     • Add 'Prove' section showing how end users deploy/use this feature
     • Include deployment steps or command examples
     • Show how a user produces the Results described

⚠️  Design (Implementation Details)
   Score: 1/3
   Suggestions:
     • Add 'Design' section with implementation details
     • Describe internal architecture, components, or data structures

✅ Evidence (Code & Testing)
   Score: 3/3
   Evidence found:
     1. https://github.com/openshift/sandboxed-containers-operator/pull/2090
     2. https://github.com/openshift/kata-containers/pull/1234
     3. [TEST] CI pipeline passed

================================================================================
NEXT STEPS
================================================================================
To improve this ticket:

3. Document 'How' (Implementation Approach):
   - Outline the technical approach
   - Identify affected components
   - Note any design decisions
```

### Assembly Output

```
================================================================================
FEATURE: OSC-1234 - Implement new peer pods feature
================================================================================
Status: In Progress
Type: Epic
Assignee: John Doe
URL: https://issues.redhat.com/browse/OSC-1234

ASSOCIATED STORIES (5):
================================================================================

In Progress (2):
--------------------------------------------------------------------------------

  OSC-1235: Add peer pods controller
  Type: Story | Link: relates to | Assignee: Jane Smith
  URL: https://issues.redhat.com/browse/OSC-1235
  PR/MR URLs (1):
    - https://github.com/openshift/sandboxed-containers-operator/pull/2090

  OSC-1236: Update documentation
  Type: Story | Link: relates to | Assignee: Bob Jones
  URL: https://issues.redhat.com/browse/OSC-1236
  ⚠️  No PR/MR URLs found

Done (3):
...

================================================================================
SUMMARY
================================================================================
Total Stories: 5
Stories with PR/MR: 3
Stories without PR/MR: 2

Total unique PR/MR URLs: 4
```

## Output Formats

### Text Format (Default)
Human-readable output with scoring summary, detailed validation, and coaching. See example above.

### JSON Format
Complete data structure with all validation results and timestamps. Primary format for programmatic access.

```bash
python3 scripts/jira-coach/validate.py OSC-1234 --format json
```

Includes:
- All pillar scores and evidence
- Timestamps (created, updated, validated in UTC)
- Complete recommendations
- Full ticket metadata

### CSV Format
Spreadsheet-compatible format for tracking multiple tickets over time.

```bash
python3 scripts/jira-coach/validate.py OSC-1234 --format csv
```

**CSV Columns:**
- `ticket_key` - Jira ticket ID
- `ticket_type` - Epic, Feature, Story, etc.
- `summary` - Ticket title
- `status` - Current Jira status
- `url` - Direct link to ticket
- `created_at_utc` - When ticket was created (ISO 8601)
- `updated_at_utc` - Last update timestamp (ISO 8601)
- `validated_at_utc` - When validation ran (ISO 8601)
- `why_score` - Why pillar score (0-3)
- `results_score` - Results pillar score (0-3)
- `prove_score` - Prove pillar score (0-3)
- `design_score` - Design pillar score (0-3)
- `evidence_score` - Evidence pillar score (0-3)
- `total_points` - Sum of all pillar scores
- `max_points` - Maximum possible (15)
- `overall_percentage` - Overall score percentage
- `is_complete` - True if ≥75% and no zeros
- `missing_aspects` - Comma-separated list of missing pillars

**Use Cases:**
- Track ticket quality over time
- Sprint/release quality reports
- Identify patterns in incomplete tickets
- Compare ticket completeness across teams

**Example: Build Quality Dashboard**
```bash
# METHOD 1: Using --no-header (recommended)
tickets=($(jira list --sprint current --format=ids))
python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > sprint-quality.csv
for ticket in "${tickets[@]:1}"; do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header >> sprint-quality.csv
done

# METHOD 2: Using helper script (easiest)
./scripts/jira-coach/batch-validate.sh sprint-quality.csv $(jira list --sprint current --format=ids)

# METHOD 3: Save individual files then combine (slower)
for ticket in $(jira list --sprint current --format=ids); do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv --output "validation-${ticket}.csv"
done
head -1 validation-*.csv | head -1 > sprint-quality.csv  # Header
tail -n +2 -q validation-*.csv >> sprint-quality.csv     # All data rows
rm validation-*.csv  # Cleanup

# Import sprint-quality.csv into spreadsheet for analysis
```

## Advanced Usage

### Quick Batch Validation (Using Helper Script)

For convenience, use the `batch-validate.sh` script:

```bash
# Validate multiple tickets
./scripts/jira-coach/batch-validate.sh sprint-report.csv OSC-1234 OSC-1235 OSC-1236

# Validate from Jira query
./scripts/jira-coach/batch-validate.sh release-report.csv $(jira list --fixVersion 1.13 --format=ids)

# Validate from file
./scripts/jira-coach/batch-validate.sh batch-report.csv $(cat tickets.txt)
```

The script provides:
- Progress indicator for each ticket
- Error handling (continues on failures)
- Summary statistics (success/fail counts, average score)
- Single CSV output with proper header

### Batch Validation

```bash
# Validate multiple tickets (text output)
for ticket in OSC-1234 OSC-1235 OSC-1236; do
    python3 scripts/jira-coach/validate.py "$ticket"
done

# Generate CSV report for multiple tickets (METHOD 1: using --no-header)
# First ticket includes header, rest omit it
tickets=(OSC-1234 OSC-1235 OSC-1236)
python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > batch-report.csv
for ticket in "${tickets[@]:1}"; do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header >> batch-report.csv
done

# Generate CSV report (METHOD 2: simpler one-liner)
{
    python3 scripts/jira-coach/validate.py OSC-1234 --format csv
    for ticket in OSC-1235 OSC-1236; do
        python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header
    done
} > batch-report.csv

# Generate CSV report (METHOD 3: with ticket list from file)
tickets=($(cat ticket-list.txt))
python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > batch-report.csv
for ticket in "${tickets[@]:1}"; do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header >> batch-report.csv
done
```

### CI/CD Integration

```bash
#!/bin/bash
# Enforce minimum completeness before closing
TICKET_ID="$1"
result=$(python3 scripts/jira-coach/validate.py "$TICKET_ID" --json)
score=$(echo "$result" | jq '.overall_score')

if (( $(echo "$score < 75" | bc -l) )); then
    echo "Error: Ticket $TICKET_ID is only ${score}% complete (need 75%+)"
    echo "$result" | jq -r '.recommendations[]'
    exit 1
fi
```

### Extract Specific Information

```bash
# Get overall score
python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.overall_score'

# Get all pillar scores
python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.scores'
# Output:
# {
#   "why": 3,
#   "results": 2,
#   "prove": 1,
#   "design": 1,
#   "evidence": 3,
#   "total_points": 10,
#   "max_points": 15,
#   "overall_percentage": 66.67
# }

# Get individual pillar score
python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.scores.why'

# Get missing aspects
python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.missing_aspects'

# Get all PRs from a feature
python3 scripts/jira-coach/assemble.py OSC-1234 --json | \
  jq -r '.. | .pr_mr_urls? // [] | .[]' | sort -u

# Find stories without PRs
python3 scripts/jira-coach/assemble.py OSC-1234 --json | \
  jq -r '.stories[] | select(.has_pr_mr == false) | .key'

# Get timestamps from JSON
python3 scripts/jira-coach/validate.py OSC-1234 --format json | \
  jq '.timestamps'

# CSV querying (using awk/cut)
# Get just the scores
python3 scripts/jira-coach/validate.py OSC-1234 --format csv | \
  awk -F',' 'NR==1 {for(i=1;i<=NF;i++) if($i~/score/) printf "%s%s", (p?" ":""), $i; p=1; print ""} NR>1 {print $9,$10,$11,$12,$13}'

# Get overall percentage from CSV
python3 scripts/jira-coach/validate.py OSC-1234 --format csv | \
  tail -1 | cut -d',' -f16

# Find tickets below threshold (from batch CSV)
awk -F',' 'NR>1 && $16<75 {print $1, $16"%"}' batch-report.csv
```

## Troubleshooting

### Authentication Error (401/403)

- Check that `JIRA_TOKEN` is set correctly
- Verify your token is valid (they can expire)
- Ensure you have permission to access the Jira project
- For Atlassian Cloud, verify `JIRA_EMAIL` is set

### Low Validation Scores Despite Having Content

The tool looks for specific keywords and patterns:
- Generic descriptions may not match the patterns
- Use explicit headers like "Why:", "Acceptance Criteria:", "Approach:"
- Structured content scores higher than narrative

### Missing PRs in Assembly

If URLs aren't being extracted:
- Verify URLs are in the description or comments (not just attachments)
- URLs must be in standard format (full GitHub/GitLab URLs)
- Custom git hosting might need additional URL patterns added to the script

### Rate Limiting

GitHub/GitLab APIs have rate limits for unauthenticated requests:
- Use `--github-token` or `--gitlab-token` with verify_prs.py
- For private repos, tokens are required

## Files in This Directory

**Scripts:**
- **validate.py** - Ticket validation tool (Why, Results, Prove, Design, Evidence)
- **assemble.py** - Feature assembly tool (gather stories and PRs)
- **verify_prs.py** - PR/MR verification helper
- **batch-validate.sh** - Helper script for batch validation with progress tracking
- **example.sh** - Interactive examples and demos

**Documentation:**
- **README.md** - This file (main documentation)
- **README-validate.md** - Detailed validation documentation
- **FRAMEWORK.md** - Complete framework guide (Why, Results, Prove, Design, Evidence)
- **SCORING.md** - Scoring system explanation and usage
- **CSV-FORMAT.md** - CSV format specification and usage examples

## Best Practices

1. **Validate early**: Check tickets when they're created
2. **Validate often**: Re-check as information is added
3. **Use as a checklist**: The five aspects (Why, Results, Prove, Design, Evidence) guide ticket creation
4. **Coach, don't police**: Use suggestions to improve, not gatekeep
5. **Adapt to your team**: Different teams may prioritize aspects differently
6. **Link code early**: Add PR links as soon as PRs are created
7. **Review before closing**: Always validate before marking Done

## Contributing

To improve the validation patterns:

1. Edit `validate.py`
2. Modify the keyword patterns:
   - `WHY_INDICATORS`
   - `WHAT_INDICATORS`
   - `HOW_INDICATORS`
   - `CODE_URL_PATTERNS`
3. Adjust scoring thresholds in the `validate_*` methods
4. Test on real tickets in your project

## Support

For issues or questions:
- Run the example script: `./scripts/jira-coach/example.sh`
- Check the detailed documentation: `README-validate.md`
- Ask Claude for help using the jira-coach skill
