# Jira Retrieve - Ticket Validation

Validates Jira Feature/Epic tickets for completeness using the Why, What, How, Where framework.

## Overview

This tool helps ensure that Jira tickets contain all necessary information for effective planning, implementation, and tracking. It evaluates four critical aspects:

- **Why**: Business justification and purpose
- **What**: Results and acceptance criteria
- **How**: Implementation approach
- **Where**: Code location (repos, PRs)

## Prerequisites

1. Python 3.x
2. `requests` library:
   ```bash
   pip install requests
   ```

3. Jira API credentials (Personal Access Token)

## Setup

### 1. Get a Jira Personal Access Token

For Red Hat Jira (issues.redhat.com):
- Go to https://issues.redhat.com
- Click your profile → Personal Settings → Personal Access Tokens
- Create a new token and copy it

For Atlassian Cloud:
- Go to https://id.atlassian.com/manage-profile/security/api-tokens
- Create API token
- You'll need both your email and the token

### 2. Set Environment Variables

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

## Usage

### As a Claude Code Skill

Just ask Claude to validate a ticket:

```
Check if OSC-1234 has all required information
```

or

```
Validate https://issues.redhat.com/browse/OSC-1234
```

Claude will:
1. Run the validation
2. Analyze the results
3. Provide coaching on what's missing
4. Cross-reference PR links with actual code

### Direct Command Line Usage

```bash
# Using ticket ID
python3 scripts/jira-retrieve/validate.py OSC-1234

# Using full URL
python3 scripts/jira-retrieve/validate.py https://issues.redhat.com/browse/OSC-1234

# Output as JSON
python3 scripts/jira-retrieve/validate.py OSC-1234 --json
```

## Understanding the Output

### Completeness Score

The tool calculates an overall completeness score (0-100%):
- Target: **75%+** for a complete ticket
- Based on individual scores for Why, What, How, Where

### Individual Aspect Scores

Each aspect is scored 0-3:
- **3** ✅ = Strong (comprehensive, well-documented)
- **2** ✓  = Adequate (present with reasonable detail)
- **1** ⚠️  = Weak (brief mention, lacks detail)
- **0** ❌ = Missing entirely

### Example Output

```
================================================================================
JIRA TICKET VALIDATION: OSC-1234
================================================================================
Summary: Implement peer pods authentication
Type: Feature
Status: In Progress
URL: https://issues.redhat.com/browse/OSC-1234

⚠️  INCOMPLETE - Score: 67% (target: 75%+)
   Missing: How

================================================================================
VALIDATION DETAILS
================================================================================

✅ Why (Purpose & Justification)
   Score: 3/3
   Evidence found:
     1. Customer requests for better authentication in confidential containers
     2. Security team requires mutual TLS for peer-to-peer communication

✓  What (Results & Acceptance Criteria)
   Score: 2/3
   Evidence found:
     1. Must support certificate-based authentication
   Suggestions:
     • Consider adding more specific acceptance criteria or test cases

⚠️  How (Implementation Approach)
   Score: 1/3
   Suggestions:
     • Consider adding a high-level implementation approach or strategy
     • Details can be in child stories, but an overview is helpful here

✅ Where (Code Location)
   Score: 3/3
   Evidence found:
     1. https://github.com/openshift/sandboxed-containers-operator/pull/2090
     2. https://github.com/openshift/kata-containers/pull/1234

================================================================================
RECOMMENDATIONS
================================================================================
1. Overall completeness: 67% (target: 75%+)
2. Consider adding a high-level implementation approach or strategy
3. Details can be in child stories, but an overview is helpful here
4. Consider adding more specific acceptance criteria or test cases

================================================================================
NEXT STEPS
================================================================================
To improve this ticket:

3. Document 'How' (Implementation Approach):
   - Outline the technical approach
   - Identify affected components
   - Note any design decisions
```

## What the Tool Looks For

### Why (Purpose & Justification)

Keywords and patterns indicating business justification:
- "why", "purpose", "goal", "objective"
- "business value", "business need", "business case"
- "reason", "motivation"
- "problem statement", "problem description"
- "user story", "user need", "user pain"
- "customer request", "customer need"

### What (Results & Acceptance Criteria)

Keywords and patterns indicating results:
- "acceptance criteria", "definition of done", "success criteria"
- "expected result", "expected outcome", "expected behavior"
- "deliverable", "result", "outcome"
- "verification", "test plan", "test criteria"
- "must be able to", "should support", "will provide"

### How (Implementation Approach)

Keywords and patterns indicating approach:
- "approach", "implementation plan", "implementation details"
- "technical design", "technical solution"
- "architecture", "design document"
- "strategy", "method", "solution"
- "will use", "will implement", "will create"

### Where (Code Location)

URL patterns for code:
- GitHub pull requests: `github.com/*/pull/*`
- GitLab merge requests: `gitlab.com/*/-/merge_requests/*`
- Repository links and commit URLs
- Other git hosting platforms

## Validation Philosophy

### Not Everything Needs to Be Complete Immediately

The tool recognizes that tickets evolve:

- **New tickets**: Focus on Why and What first
- **In Progress**: How should be documented, Where is being added
- **Done/Closed**: Where (PR links) is CRITICAL

### Context-Aware Scoring

The tool adjusts expectations based on:
- **Ticket type**: Epics/Features need less implementation detail than Stories
- **Status**: Done tickets must have PR links
- **Content quality**: Multiple pieces of evidence score higher

## Iterative Improvement

Use this tool throughout the ticket lifecycle:

1. **At creation**: Validate Why and What are clear
2. **Before starting work**: Ensure How is outlined
3. **During implementation**: Add PR links as they're created
4. **Before closing**: Verify all four aspects are complete

## Integration with CI/CD

Use JSON output for automated checks:

```bash
#!/bin/bash
# Validate ticket completeness in CI
result=$(python3 scripts/jira-retrieve/validate.py "$TICKET_ID" --json)
score=$(echo "$result" | jq '.overall_score')

if (( $(echo "$score < 75" | bc -l) )); then
    echo "Error: Ticket $TICKET_ID is only ${score}% complete (need 75%+)"
    echo "$result" | jq -r '.recommendations[]'
    exit 1
fi
```

## Troubleshooting

### Authentication Error (401/403)

If you get authentication errors:
- Check that `JIRA_TOKEN` is set correctly
- Verify your token is valid (they can expire)
- Ensure you have permission to access the Jira project
- For Atlassian Cloud, verify `JIRA_EMAIL` is set

### Low Scores Despite Having Content

The tool looks for specific keywords and patterns:
- Generic descriptions may not match the patterns
- Use explicit headers like "Why:", "Acceptance Criteria:", "Approach:"
- Structured content scores higher than narrative

### Missing Evidence

If the tool doesn't find evidence:
- Check that information is in the description or comments (not attachments)
- Information in custom fields may not be detected
- Use the JSON output to see what text was analyzed

## Advanced Usage

### Batch Validation

Validate multiple tickets:

```bash
#!/bin/bash
for ticket in OSC-1234 OSC-1235 OSC-1236; do
    echo "Validating $ticket..."
    python3 scripts/jira-retrieve/validate.py "$ticket"
    echo ""
done
```

### JSON Processing

Extract specific information:

```bash
# Get all incomplete tickets
python3 scripts/jira-retrieve/validate.py OSC-1234 --json | \
  jq 'select(.is_complete == false) | .missing_aspects'

# Get recommendations only
python3 scripts/jira-retrieve/validate.py OSC-1234 --json | \
  jq -r '.recommendations[]'

# Get PR links
python3 scripts/jira-retrieve/validate.py OSC-1234 --json | \
  jq -r '.aspects.where.evidence[]'
```

### Weekly Report

Generate a report of ticket completeness:

```bash
#!/bin/bash
# Report on all tickets in sprint
echo "Sprint Ticket Completeness Report"
echo "=================================="

for ticket in $(jira list --sprint current --format=ids); do
    result=$(python3 scripts/jira-retrieve/validate.py "$ticket" --json 2>/dev/null)
    score=$(echo "$result" | jq -r '.overall_score')
    status=$(echo "$result" | jq -r '.status')
    summary=$(echo "$result" | jq -r '.summary')

    printf "%-12s %-15s %3.0f%%  %s\n" "$ticket" "$status" "$score" "$summary"
done
```

## Best Practices

1. **Validate early**: Check tickets when they're created
2. **Validate often**: Re-check as information is added
3. **Use as a checklist**: The four aspects (Why, What, How, Where) guide ticket creation
4. **Coach, don't police**: Use suggestions to improve, not gatekeep
5. **Adapt to your team**: Different teams may prioritize aspects differently

## Related Tools

- **assemble.py**: Retrieves a feature and all linked stories with PRs
  - Use `assemble` to see the full feature scope
  - Use `validate` to check individual ticket quality

## Example Workflow

```bash
# 1. Create a new feature ticket (manual in Jira)

# 2. Validate it has good Why and What
python3 scripts/jira-retrieve/validate.py OSC-1234

# 3. Add missing information based on feedback

# 4. Start implementation, document How

# 5. Create PRs and link them to the ticket

# 6. Validate before closing
python3 scripts/jira-retrieve/validate.py OSC-1234

# 7. Should see 75%+ score and all PRs linked
```

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
- Check the existing Jira tickets for examples
- Review the patterns in the code
- Ask Claude for help using the jira-retrieve skill
