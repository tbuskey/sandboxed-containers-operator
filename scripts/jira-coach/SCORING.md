# Jira Coach Scoring System

## Overview

Each Jira ticket is evaluated across **five pillars**, each scored **0-3**, for a maximum of **15 points** (100%).

## Pillar Scores (0-3 each)

Each pillar receives an individual score:

| Score | Rating | Indicator | Meaning |
|-------|--------|-----------|---------|
| **3** | Strong | ✅ | Comprehensive, well-documented |
| **2** | Adequate | ✓  | Present with reasonable detail |
| **1** | Weak | ⚠️  | Brief mention, lacks detail |
| **0** | Missing | ❌ | Not present at all |

### The Five Pillars

1. **Why** - Business justification and purpose
2. **Results** - What the final product looks like
3. **Prove** - How end users deploy/use the feature
4. **Design** - Implementation details (what users don't see)
5. **Evidence** - Code location AND testing proof

## Overall Score Calculation

**Formula:** `(sum of pillar scores / 15) × 100`

**Example:**
- Why: 3/3
- Results: 2/3
- Prove: 1/3
- Design: 2/3
- Evidence: 3/3
- **Total:** 11/15 = 73%

## Completeness Criteria

A ticket is considered **COMPLETE** when:

✅ Overall score ≥ **75%** (11+ points out of 15)  
✅ **No pillar has a score of 0** (nothing completely missing)

## Example Output

### Console Output

```
================================================================================
JIRA TICKET VALIDATION: OSC-1234
================================================================================
Summary: Implement peer pods authentication
Type: Feature
Status: In Progress
URL: https://issues.redhat.com/browse/OSC-1234

⚠️  INCOMPLETE - Score: 73% (target: 75%+)
   Missing: Prove

PILLAR SCORES:
----------------------------------------
  Why          3/3  ✅
  Results      2/3  ✓ 
  Prove        0/3  ❌
  Design       2/3  ✓ 
  Evidence     3/3  ✅
----------------------------------------
  Overall      73%  (11/15 points)
```

### JSON Output

```json
{
  "ticket_key": "OSC-1234",
  "scores": {
    "why": 3,
    "results": 2,
    "prove": 0,
    "design": 2,
    "evidence": 3,
    "total_points": 11,
    "max_points": 15,
    "overall_percentage": 73.33
  },
  "overall_score": 73.33,
  "is_complete": false,
  "missing_aspects": ["Prove"],
  "aspects": {
    "why": {
      "aspect": "Why (Purpose & Justification)",
      "present": true,
      "score": 3,
      "evidence": [...],
      "suggestions": []
    },
    "results": {
      "aspect": "Results (What Final Product Looks Like)",
      "present": true,
      "score": 2,
      "evidence": [...],
      "suggestions": [...]
    },
    ...
  }
}
```

## Score Interpretation by Status

### New Tickets
- **40-60%**: Normal - Focus on Why and Results first
- **60-75%**: Good start - Add Prove and Design next
- **75%+**: Excellent - Ready to start implementation

### In Progress Tickets
- **<60%**: Needs attention - Missing critical information
- **60-75%**: On track - Keep adding Evidence as work progresses
- **75%+**: Well documented - Continue to update

### Done Tickets
- **<75%**: ⚠️  **INCOMPLETE** - Should not be closed yet
- **<60% with Evidence=0**: 🚨 **CRITICAL** - No PR links or testing proof!
- **75%+**: ✅ Complete - Can be closed

## Critical Scoring Rules

### Evidence is Critical for Done Tickets

If a ticket is marked **Done** but Evidence score is **0**:
- **Automatic INCOMPLETE status** regardless of other scores
- **Critical warning** displayed
- Should NOT be closed until Evidence is added

### No Zeros Policy

Tickets should have **no pillar with score 0** to be complete:
- Even if overall score ≥ 75%, missing pillars block completion
- Example: 12/15 (80%) but Prove=0 → **INCOMPLETE**

## Using Scores for Different Purposes

### Individual Development
- Track your own ticket quality over time
- Aim for 75%+ before marking Done
- Use suggestions to improve weak pillars

### Team Standards
```bash
# Weekly team report
for ticket in OSC-1234 OSC-1235 OSC-1236; do
    result=$(python3 scripts/jira-coach/validate.py "$ticket" --json)
    score=$(echo "$result" | jq '.scores.overall_percentage')
    summary=$(echo "$result" | jq -r '.summary')
    echo "$ticket ($score%): $summary"
done
```

### CI/CD Gates
```bash
# Block closure if incomplete
result=$(python3 scripts/jira-coach/validate.py "$TICKET" --json)
score=$(echo "$result" | jq '.scores.total_points')

if [ "$score" -lt 11 ]; then  # 11/15 = 73%, below 75% threshold
    echo "ERROR: Ticket incomplete (${score}/15 points)"
    exit 1
fi
```

### Sprint Planning
```bash
# Identify tickets ready for work (good Why + Results)
result=$(python3 scripts/jira-coach/validate.py "$TICKET" --json)
why=$(echo "$result" | jq '.scores.why')
results=$(echo "$result" | jq '.scores.results')

if [ "$why" -ge 2 ] && [ "$results" -ge 2 ]; then
    echo "Ready to start"
else
    echo "Needs more planning"
fi
```

## Querying Scores with jq

### Get All Scores
```bash
python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.scores'
```

### Get Overall Percentage
```bash
python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.scores.overall_percentage'
```

### Get Specific Pillar Score
```bash
python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.scores.evidence'
```

### Find Weak Pillars
```bash
python3 scripts/jira-coach/validate.py OSC-1234 --json | \
  jq '.aspects | to_entries | map(select(.value.score < 2)) | .[].key'
```

### Check if Complete
```bash
python3 scripts/jira-coach/validate.py OSC-1234 --json | jq '.is_complete'
```

## Score Trends Over Time

Track improvement by running validation periodically:

```bash
# Save snapshot
date=$(date +%Y-%m-%d)
python3 scripts/jira-coach/validate.py OSC-1234 --json > "scores-${date}.json"

# Compare
diff <(jq '.scores' scores-2026-05-01.json) <(jq '.scores' scores-2026-05-05.json)
```

## Tips for Improving Scores

### From 0 → 1 (Add minimal content)
- Add at least a brief mention of the pillar
- A single sentence or bullet point

### From 1 → 2 (Add adequate detail)
- Expand brief mentions with concrete details
- Add 2-3 specific examples or points
- Make it actionable

### From 2 → 3 (Make it comprehensive)
- Add multiple detailed examples
- Include edge cases or variations
- Make it complete and unambiguous

### Priority Order
1. **Fix all zeros first** (critical for completion)
2. **Focus on status-appropriate pillars:**
   - New: Why, Results
   - In Progress: Prove, Design
   - Done: Evidence
3. **Improve 1s to 2s** (adequate detail)
4. **Polish 2s to 3s** (if time permits)

## Common Score Patterns

### Pattern: "Good idea, poor execution"
- Why: 3, Results: 3, Prove: 0, Design: 0, Evidence: 0
- **Problem:** No implementation plan or code
- **Fix:** Add Prove (how to use) and Design (how it works)

### Pattern: "Code exists, no context"
- Why: 0, Results: 0, Prove: 0, Design: 2, Evidence: 3
- **Problem:** PRs exist but ticket doesn't explain what or why
- **Fix:** Document Why and Results for future reference

### Pattern: "Almost done"
- Why: 3, Results: 2, Prove: 2, Design: 2, Evidence: 0
- **Problem:** Work is complete but not linked/tested
- **Fix:** Add PR links and testing evidence

### Pattern: "Perfect planning, no evidence"
- Why: 3, Results: 3, Prove: 3, Design: 3, Evidence: 0
- **Problem:** Great documentation but no implementation proof
- **Fix:** Add code and testing evidence as work completes

## Summary

**Every pillar counts.** The scoring system ensures:
- ✅ No critical information is missing (no zeros)
- ✅ Adequate detail in each area (75%+ overall)
- ✅ Balanced documentation across all five aspects
- ✅ Clear, measurable quality standards

Use the scores to **guide improvement**, not as gatekeeping. The goal is better documentation that helps everyone understand what was built, why, and how to use it.
