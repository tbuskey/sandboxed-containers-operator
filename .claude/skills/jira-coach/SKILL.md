---
name: jira-coach
description: Validate Jira tickets for completeness (Why, Results, Prove, Design, Evidence) and assemble features with their stories and PR links. Coaches users to improve ticket quality iteratively.
allowed-tools:
  - Bash(python3 scripts/jira-coach/*.py*)
  - Read
  - Bash(git*)
  - Bash(gh*)
---

# Jira Coach - Ticket Validation & Feature Assembly

This skill helps ensure Jira Feature/Epic tickets are complete and well-documented. It provides two main capabilities:

1. **Validate** - Check if a ticket has Why, Results, Prove, Design, Evidence information
2. **Assemble** - Gather a feature and all its associated stories with PR/MR links

Both capabilities coach users to improve ticket quality iteratively as information becomes available.

## The Five Pillars of Complete Tickets

1. **Why** - Business justification and purpose
   - Why does this ticket exist?
   - What problem does it solve?
   - What business value does it provide?

2. **Results** - What the final product looks like
   - What objects/resources get created? (Pods, Deployments, ConfigMaps, etc.)
   - What UI elements or screen changes appear?
   - What shows up in logs or system output?
   - Be concrete and specific about observable outcomes

3. **Prove** - How end users deploy/use the feature
   - What commands do users run?
   - What YAML or configuration do they apply?
   - How do they produce the Results described above?
   - Step-by-step user-facing instructions
   - No confusion about how to set up and use the feature

4. **Design** - Implementation details (what users don't see)
   - Internal architecture and components
   - What happens under the hood
   - Technical approach and dependencies
   - ONLY things users don't see (user-facing details go in Prove)

5. **Evidence** - Code location and testing proof
   - PR/MR links to code changes
   - Repository references
   - Testing evidence (CI output, test results, verification notes)
   - Proof that it works

## Instructions for Claude

### When to Use Each Tool

**Use `validate.py`** when the user asks about a single ticket's quality:
- "Check if OSC-1234 has all required information"
- "Validate this ticket"
- "What's missing from OSC-1234?"
- "Does OSC-1234 have Why, Results, Prove, Design, Evidence?"

**Use `assemble.py`** when the user wants to see all related work:
- "Assemble feature OSC-1234"
- "Get all stories and PRs for OSC-1234"
- "What's the status of feature OSC-1234 and its related work?"
- "Show me all code changes for this feature"

**Use both** for comprehensive feature review:
1. First validate the feature ticket itself for completeness
2. Then assemble all stories to see related work and PRs

### Validation Workflow

When validating a ticket (`validate.py`):

1. **Run the validation script**:
   ```bash
   python3 scripts/jira-coach/validate.py <ticket-id-or-url>
   ```

2. **Analyze the results**:
   - Overall completeness score (0-100%, target: 75%+)
   - Individual scores for Why, Results, Prove, Design, Evidence (0-3 each)
   - Evidence found for each aspect
   - Missing aspects and suggestions

3. **Coach the user** based on findings:
   - If incomplete, explain what's missing
   - Provide specific, actionable suggestions
   - Adapt guidance based on ticket status:
     - **New tickets**: Focus on Why and Results first
     - **In Progress**: Ensure Prove and Design are documented, start adding Evidence
     - **Done**: Critical that Evidence (PRs and testing) are present

4. **Cross-reference with code** when Evidence is present:
   - Use Read tool to verify PR links point to real code
   - Check if PRs are merged, open, or closed
   - Use `gh pr view <number>` to get PR details if GitHub
   - Validate that linked code relates to the ticket's purpose

5. **Provide coaching iterations**:
   - Not everything will be complete at the start - this is expected
   - Guide users to add information as it becomes available
   - Focus on the most critical missing pieces first
   - Celebrate progress when aspects are added

### Key Distinctions to Explain

When coaching users, emphasize these distinctions:

**Results vs Prove:**
- **Results** = WHAT the user sees (objects created, UI changes, log output)
- **Prove** = HOW to get to those Results (commands, YAML, steps)
- Example: Results: "Creates a kata-runtime RuntimeClass and peer-pod Pods". Prove: "Run `oc apply -f kataconfig.yaml` then `oc create -f peerpod.yaml`"

**Prove vs Design:**
- **Prove** = User-facing deployment/usage (what users DO)
- **Design** = Internal implementation (what users DON'T see)
- If a user needs to know it to use the feature → Prove
- If it's internal architecture/code details → Design

**Evidence = Code + Testing:**
- Not just PR links (that's the old "Where")
- Must also include testing evidence
- CI output, test results, verification notes, screenshots all count

### Assembly Workflow

When assembling a feature (`assemble.py`):

1. **Run the assembly script**:
   ```bash
   python3 scripts/jira-coach/assemble.py <feature-id-or-url>
   ```

2. **Present the results** to the user:
   - Feature overview (summary, status, assignee)
   - Feature-level PR/MR links
   - List of associated stories grouped by status
   - PR/MR links for each story
   - Summary statistics (stories with/without PRs)

3. **Identify gaps**:
   - Highlight stories without PR/MR links
   - Flag completed stories missing code references
   - Note which stories need attention

4. **Provide actionable guidance**:
   - Coach users to add missing PR links
   - Suggest which stories to focus on first
   - Explain the importance of linking code changes

### Comprehensive Feature Review

For a complete feature review, combine both tools:

1. **Validate the feature ticket**:
   ```bash
   python3 scripts/jira-coach/validate.py OSC-1234
   ```
   - Check if the feature has good Why, Results, Prove, Design documentation

2. **Assemble all related work**:
   ```bash
   python3 scripts/jira-coach/assemble.py OSC-1234
   ```
   - See all stories and their PR links
   - Verify the Evidence aspect is covered across stories

3. **Synthesize findings**:
   - The feature ticket should have clear Why, Results, Prove, Design
   - Individual stories should have PR links (Evidence)
   - Coach on any gaps at feature or story level

## Validation Scoring

Each aspect (Why, Results, Prove, Design, Evidence) is scored 0-3:
- **0** = Missing entirely
- **1** = Weak/minimal (brief mention, lacks detail)
- **2** = Adequate (present with reasonable detail)
- **3** = Strong (comprehensive, well-documented)

Overall score = (sum of aspect scores / 15) × 100

A ticket is considered **complete** when:
- Overall score ≥ 75%
- No aspect has a score of 0

## Environment Variables

The scripts use these environment variables for Jira authentication:
- `JIRA_URL` - Base URL for Jira instance (e.g., `https://issues.redhat.com`)
- `JIRA_TOKEN` - Personal Access Token for Jira API
- `JIRA_EMAIL` - Email address for Jira authentication (for Atlassian Cloud)

## Example Questions That Trigger This Skill

**Validation:**
- "Check if OSC-1234 has all required information"
- "Validate https://issues.redhat.com/browse/OSC-1234"
- "Does OSC-1234 have Why, Results, Prove, Design, Evidence?"
- "Review the completeness of feature OSC-1234"
- "What's missing from ticket OSC-1234?"

**Assembly:**
- "Assemble feature OSC-1234"
- "Get all stories and PRs for https://issues.redhat.com/browse/OSC-1234"
- "What's the status of feature OSC-1234 and its related work?"
- "Show me all the code changes for feature OSC-1234"

**Comprehensive Review:**
- "Review feature OSC-1234 and all its stories"
- "Is OSC-1234 ready to close?"
- "Give me a complete picture of OSC-1234"

## Coaching Approach

When providing feedback to users:

1. **Start positive**: Acknowledge what IS present
2. **Prioritize**: Focus on the most critical gaps first
3. **Be specific**: Provide concrete examples of what to add
4. **Distinguish the aspects**: Help users understand Results vs Prove vs Design
5. **Context-aware**: Adjust expectations based on ticket status
6. **Iterative**: Encourage adding information as it becomes available

### Example Coaching for a New Ticket

```
OSC-1234 is at 40% completeness. Here's what to focus on:

✅ Good start: The ticket has a clear Why

⚠️  Priority 1 - Add 'Results':
   Describe what the final product looks like. For example:
   - Creates a peer-pod-controller Deployment
   - Adds a peer-pods RuntimeClass
   - Shows "Peer pod started successfully" in logs

⚠️  Priority 2 - Add 'Prove':
   Show how users deploy this. For example:
   - Run: oc apply -f kataconfig-peerpods.yaml
   - Create pod: oc create -f example-peerpod.yaml
   - Verify: oc get pods -l runtime-class=kata-remote

The 'Design' and 'Evidence' can be added as you start implementation.
```

### Example Coaching for Completed Ticket

```
⚠️  CRITICAL: OSC-1234 is marked Done but missing Evidence!

The ticket has excellent Why, Results, Prove, and Design (great!), but:
- No PR/MR links found
- No testing evidence

This makes it hard to:
- Review the actual implementation
- Verify it was tested
- Reference this work in the future

Please add:
1. Links to the PRs that implemented this
2. Evidence of testing (CI output, QE verification, test results)
```

## Helper Tools

Additional scripts available:

- **verify_prs.py**: Verify PR/MR links actually exist and check their status
  ```bash
  python3 scripts/jira-coach/verify_prs.py <pr-url> [<pr-url2> ...]
  ```

## Output Formats

### Validation Output

Shows:
1. **Header**: Ticket info and overall score
2. **Validation Details**: Score and evidence for each aspect (Why, Results, Prove, Design, Evidence)
3. **Recommendations**: Specific suggestions for improvement
4. **Next Steps**: Actionable coaching on what to do next

### Assembly Output

Shows:
1. **Feature Overview**: Summary, status, type, assignee, URL
2. **Feature PR/MR URLs**: Links from the feature ticket itself
3. **Associated Stories**: Grouped by status with:
   - Story summary, type, assignee
   - Link relationship to feature
   - Story URL
   - PR/MR URLs found
   - Warning if no PRs found
4. **Summary Statistics**:
   - Total stories
   - Stories with/without PR/MR links
   - All unique PR/MR URLs across the feature

## Requirements

- Python 3.x
- `requests` library (`pip install requests`)
- Jira API access credentials
- Read access to linked code repositories (for cross-referencing)

## Setup

See `scripts/jira-coach/README.md` for detailed setup instructions.

## Related Information

- Main documentation: `scripts/jira-coach/README.md`
- Validation details: `scripts/jira-coach/README-validate.md`
- Example usage: `scripts/jira-coach/example.sh`
