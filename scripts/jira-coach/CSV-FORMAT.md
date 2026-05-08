# CSV Output Format

The CSV format provides spreadsheet-compatible output for tracking ticket quality over time.

## Format

**Command:**
```bash
# With header (default)
python3 scripts/jira-coach/validate.py <ticket-id> --format csv

# Without header (for batch processing)
python3 scripts/jira-coach/validate.py <ticket-id> --format csv --no-header
```

**Output Structure:**
```csv
ticket_key,ticket_type,summary,status,url,created_at_utc,updated_at_utc,validated_at_utc,why_score,results_score,prove_score,design_score,evidence_score,total_points,max_points,overall_percentage,is_complete,missing_aspects
OSC-1234,Epic,"Implement peer pods authentication",In Progress,https://issues.redhat.com/browse/OSC-1234,2026-01-15T10:30:00.000Z,2026-05-01T14:22:00.000Z,2026-05-06T16:45:23.123456Z,3,2,3,2,3,13,15,86.67,True,""
```

**Note:** Use `--no-header` when combining multiple validations into a single CSV file.

## Column Descriptions

| Column | Type | Range/Format | Description |
|--------|------|--------------|-------------|
| `ticket_key` | String | - | Jira ticket ID (e.g., OSC-1234, KATA-5054) |
| `ticket_type` | String | - | Epic, Feature, Story, Task, Bug, etc. |
| `summary` | String | - | Ticket title (quoted if contains commas) |
| `status` | String | - | Current Jira status (New, In Progress, Done, etc.) |
| `url` | String | URL | Direct link to Jira ticket |
| `created_at_utc` | DateTime | ISO 8601 | When ticket was created in UTC |
| `updated_at_utc` | DateTime | ISO 8601 | Last update timestamp in UTC |
| `validated_at_utc` | DateTime | ISO 8601 | When this validation ran in UTC |
| `why_score` | Integer | 0-3 | Why pillar score |
| `results_score` | Integer | 0-3 | Results pillar score |
| `prove_score` | Integer | 0-3 | Prove pillar score |
| `design_score` | Integer | 0-3 | Design pillar score |
| `evidence_score` | Integer | 0-3 | Evidence pillar score |
| `total_points` | Integer | 0-15 | Sum of all pillar scores |
| `max_points` | Integer | 15 | Maximum possible points |
| `overall_percentage` | Float | 0.00-100.00 | (total_points / max_points) × 100 |
| `is_complete` | Boolean | True/False | True if ≥75% and no pillar = 0 |
| `missing_aspects` | String | - | Comma-separated list of missing pillars (quoted) |

## Quick Start: Batch Processing

The simplest way to validate multiple tickets into a single CSV:

```bash
# Simple bash loop with --no-header
tickets=(OSC-1234 OSC-1235 OSC-1236)

# First ticket with header
python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > report.csv

# Rest without header
for ticket in "${tickets[@]:1}"; do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header >> report.csv
done
```

Or use the helper script:
```bash
./scripts/jira-coach/batch-validate.sh report.csv OSC-1234 OSC-1235 OSC-1236
```

## Use Cases

### 1. Sprint Quality Dashboard

Track all tickets in a sprint:

```bash
#!/bin/bash
# Generate sprint quality report

SPRINT_ID="Sprint 42"
OUTPUT="sprint-${SPRINT_ID// /-}-quality.csv"

# Get all tickets
tickets=($(jira list --sprint "$SPRINT_ID" --format=ids))

# First ticket with header
python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > "$OUTPUT"

# Remaining tickets without header
for ticket in "${tickets[@]:1}"; do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header >> "$OUTPUT"
done

echo "Report saved to: $OUTPUT"
echo "Total tickets: ${#tickets[@]}"
```

**Alternative (more robust with error handling):**
```bash
#!/bin/bash
# Generate sprint quality report with error handling

SPRINT_ID="Sprint 42"
OUTPUT="sprint-${SPRINT_ID// /-}-quality.csv"
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Get all tickets
tickets=($(jira list --sprint "$SPRINT_ID" --format=ids))
echo "Processing ${#tickets[@]} tickets..."

# First ticket with header
if python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > "$OUTPUT" 2>/dev/null; then
    echo "✓ ${tickets[0]}"
else
    echo "✗ ${tickets[0]} (failed)" >&2
fi

# Remaining tickets without header
for ticket in "${tickets[@]:1}"; do
    if python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header 2>/dev/null >> "$OUTPUT"; then
        echo "✓ $ticket"
    else
        echo "✗ $ticket (failed)" >&2
    fi
done

echo "Report saved to: $OUTPUT"
```

**Import into spreadsheet**, then create:
- Pivot table by `ticket_type` showing average `overall_percentage`
- Chart showing score distribution
- Filter for `is_complete = False` to find work needed

### 2. Quality Trend Over Time

Track ticket quality as it evolves:

```bash
#!/bin/bash
# Track ticket quality daily

TICKET="OSC-1234"
DATE=$(date +%Y-%m-%d)

# Append to historical CSV
python3 scripts/jira-coach/validate.py "$TICKET" --format csv --output "history-${TICKET}.csv"

# Or append to single timeline file
if [ ! -f "timeline.csv" ]; then
    # Create with header
    python3 scripts/jira-coach/validate.py "$TICKET" --format csv | head -1 > timeline.csv
fi
python3 scripts/jira-coach/validate.py "$TICKET" --format csv | tail -1 >> timeline.csv
```

**Spreadsheet analysis:**
- Line chart: `validated_at_utc` (X) vs `overall_percentage` (Y)
- Shows quality improvement over time
- Identify when pillars were added

### 3. Team Comparison

Compare ticket quality across teams:

```bash
#!/bin/bash
# Compare team quality

for team in team-alpha team-beta team-gamma; do
    echo "Processing $team..."
    
    # Get team's tickets
    tickets=$(jira list --project OSC --component "$team" --format=ids)
    
    for ticket in $tickets; do
        python3 scripts/jira-coach/validate.py "$ticket" --format csv 2>/dev/null | \
            tail -1 | \
            sed "s/^/${team},/" >> team-comparison.csv
    done
done
```

**Spreadsheet:**
- Add `team` column (via sed above)
- Pivot: Average `overall_percentage` by `team`
- Chart: Team performance comparison

### 4. Release Readiness Report

Check all tickets for a release:

```bash
#!/bin/bash
# Validate all tickets in release 1.13

RELEASE="OSC-1.13"

# Get all tickets
tickets=$(jira list --fixVersion "$RELEASE" --format=ids)

# Validate and create report
echo "Validating ${#tickets[@]} tickets for $RELEASE..."

python3 scripts/jira-coach/validate.py DUMMY-0 --format csv 2>/dev/null | head -1 > "release-${RELEASE}-readiness.csv"

for ticket in $tickets; do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv 2>/dev/null | tail -1 >> "release-${RELEASE}-readiness.csv"
done

# Summary
total=$(tail -n +2 "release-${RELEASE}-readiness.csv" | wc -l)
complete=$(awk -F',' '$17=="True"' "release-${RELEASE}-readiness.csv" | wc -l)
incomplete=$((total - complete))

echo "Release $RELEASE Readiness:"
echo "  Total tickets: $total"
echo "  Complete: $complete"
echo "  Incomplete: $incomplete"
echo "  Completeness rate: $(echo "scale=1; $complete*100/$total" | bc)%"
```

### 5. Find Tickets Needing Attention

```bash
#!/bin/bash
# Find tickets with specific issues

CSV_FILE="batch-report.csv"

# Tickets with no Evidence (critical for Done tickets)
echo "=== Tickets Missing Evidence ==="
awk -F',' '$13==0 {print $1, $4, $16"%"}' "$CSV_FILE"

# Incomplete tickets with high scores (close to complete)
echo -e "\n=== Almost Complete (70-74%) ==="
awk -F',' '$16>=70 && $16<75 {print $1, $16"%", $18}' "$CSV_FILE"

# Done tickets that are incomplete
echo -e "\n=== Done but Incomplete ==="
awk -F',' '$4=="Done" && $17=="False" {print $1, $16"%"}' "$CSV_FILE"

# Tickets updated recently but still incomplete
echo -e "\n=== Recently Updated but Incomplete ==="
# (Requires date parsing - example with last 7 days)
week_ago=$(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%S)
awk -F',' -v cutoff="$week_ago" '$8>cutoff && $17=="False" {print $1, $8, $16"%"}' "$CSV_FILE"
```

## Spreadsheet Formulas

Once imported, use these formulas:

**Conditional Formatting:**
```excel
# Highlight incomplete tickets (is_complete = False)
=$Q2=FALSE

# Color-code by score:
# Red: <60%, Yellow: 60-74%, Green: ≥75%
=IF($P2<60, "red", IF($P2<75, "yellow", "green"))
```

**Calculated Columns:**
```excel
# Days since created
=TODAY()-DATEVALUE(LEFT(F2,10))

# Days since updated
=TODAY()-DATEVALUE(LEFT(G2,10))

# Completion rate (for summary)
=COUNTIF(Q:Q,TRUE)/COUNTA(Q:Q)

# Average score by type
=AVERAGEIF(B:B,"Epic",P:P)
```

**Pivot Table Setup:**

1. **Rows:** `ticket_type`
2. **Values:** 
   - Average of `overall_percentage`
   - Count of `ticket_key`
   - Count of `is_complete` (filtered to True)
3. **Filters:** `status`, `is_complete`

**Charts:**
- Pie chart: Distribution of complete vs incomplete
- Bar chart: Average score by ticket type
- Scatter plot: `created_at_utc` vs `overall_percentage` (age vs quality)
- Line chart: `validated_at_utc` vs `overall_percentage` (quality over time)

## Example Analysis Queries

### SQL (if importing to database)

```sql
-- Average score by ticket type
SELECT ticket_type, 
       AVG(overall_percentage) as avg_score,
       COUNT(*) as count,
       SUM(CASE WHEN is_complete = 'True' THEN 1 ELSE 0 END) as complete_count
FROM validations
GROUP BY ticket_type
ORDER BY avg_score DESC;

-- Tickets updated but not validated recently
SELECT ticket_key, summary, 
       updated_at_utc, 
       validated_at_utc,
       DATEDIFF(day, validated_at_utc, CURRENT_TIMESTAMP) as days_since_validation
FROM validations
WHERE DATEDIFF(day, validated_at_utc, CURRENT_TIMESTAMP) > 7
  AND status IN ('In Progress', 'In Review')
ORDER BY days_since_validation DESC;

-- Weakest pillar by ticket type
SELECT ticket_type,
       'Why' as pillar, AVG(why_score) as avg_score FROM validations GROUP BY ticket_type
UNION ALL
SELECT ticket_type, 'Results', AVG(results_score) FROM validations GROUP BY ticket_type
UNION ALL
SELECT ticket_type, 'Prove', AVG(prove_score) FROM validations GROUP BY ticket_type
UNION ALL
SELECT ticket_type, 'Design', AVG(design_score) FROM validations GROUP BY ticket_type
UNION ALL
SELECT ticket_type, 'Evidence', AVG(evidence_score) FROM validations GROUP BY ticket_type
ORDER BY ticket_type, avg_score ASC;
```

### Python/Pandas

```python
import pandas as pd

# Load CSV
df = pd.read_csv('batch-report.csv')

# Convert timestamps to datetime
df['validated_at_utc'] = pd.to_datetime(df['validated_at_utc'])
df['updated_at_utc'] = pd.to_datetime(df['updated_at_utc'])

# Summary statistics
print(df.groupby('ticket_type')['overall_percentage'].describe())

# Find patterns
incomplete = df[df['is_complete'] == False]
print(f"Most common missing aspects:")
print(incomplete['missing_aspects'].value_counts())

# Quality trends
df['validation_date'] = df['validated_at_utc'].dt.date
trend = df.groupby('validation_date')['overall_percentage'].mean()
trend.plot(title='Quality Trend Over Time')

# Correlation analysis
print("\nCorrelation between pillar scores:")
pillars = ['why_score', 'results_score', 'prove_score', 'design_score', 'evidence_score']
print(df[pillars].corr())
```

## Batch Processing Tips

**Parallel execution:**
```bash
# Process tickets in parallel (GNU parallel) - Note: order not guaranteed
tickets=($(jira list --sprint current --format=ids))

# First ticket with header (sequential)
python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > sprint-report.csv

# Rest in parallel without header
printf '%s\n' "${tickets[@]:1}" | \
    parallel -j 4 "python3 scripts/jira-coach/validate.py {} --format csv --no-header 2>/dev/null" \
    >> sprint-report.csv
```

**Error handling:**
```bash
# Skip failed validations
tickets=($(cat tickets.txt))

# First with header
python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > report.csv 2>/dev/null || {
    echo "Failed to validate: ${tickets[0]}" >&2
    # Create header-only file
    echo "ticket_key,ticket_type,summary,status,url,created_at_utc,updated_at_utc,validated_at_utc,why_score,results_score,prove_score,design_score,evidence_score,total_points,max_points,overall_percentage,is_complete,missing_aspects" > report.csv
}

# Rest without header
for ticket in "${tickets[@]:1}"; do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header 2>/dev/null >> report.csv || \
        echo "Failed to validate: $ticket" >&2
done
```

**Rate limiting:**
```bash
# Add delay between requests to avoid API rate limits
tickets=($(cat tickets.txt))

# First with header
python3 scripts/jira-coach/validate.py "${tickets[0]}" --format csv > report.csv
sleep 1

# Rest without header
for ticket in "${tickets[@]:1}"; do
    python3 scripts/jira-coach/validate.py "$ticket" --format csv --no-header >> report.csv
    sleep 1  # 1 second between requests
done
```

## Best Practices

1. **Include timestamps in filename:**
   ```bash
   DATE=$(date +%Y%m%d-%H%M%S)
   python3 scripts/jira-coach/validate.py OSC-1234 --format csv --output "validation-OSC-1234-${DATE}.csv"
   ```

2. **Use --no-header for batch processing:**
   - First ticket includes header (default)
   - Subsequent tickets use `--no-header` flag
   - Cleaner than using `tail -n +2` to strip headers

3. **Quote handling:**
   - Summary and missing_aspects are quoted
   - Handles commas in ticket titles
   - Safe for Excel/Sheets import

4. **Archive historical data:**
   - Keep daily/weekly snapshots
   - Track quality improvements
   - Identify regression

5. **Automate collection:**
   - Cron job for daily validation
   - CI/CD integration for releases
   - Git hooks for commits

## Integration Examples

### Grafana Dashboard

Import CSV to TimescaleDB/PostgreSQL, then query:

```sql
SELECT validated_at_utc as time,
       overall_percentage as score,
       ticket_key
FROM validations
WHERE validated_at_utc > NOW() - INTERVAL '30 days'
ORDER BY validated_at_utc;
```

### Slack Notifications

```bash
#!/bin/bash
# Alert on incomplete Done tickets

REPORT="daily-validation.csv"
incomplete_done=$(awk -F',' '$4=="Done" && $17=="False" {print $1}' "$REPORT")

if [ -n "$incomplete_done" ]; then
    message="⚠️ Incomplete Done tickets: $incomplete_done"
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"$message\"}" \
        "$SLACK_WEBHOOK_URL"
fi
```

### Google Sheets

```python
import gspread
import pandas as pd

# Load CSV
df = pd.read_csv('batch-report.csv')

# Upload to Google Sheets
gc = gspread.service_account()
sh = gc.open('Jira Quality Tracker')
worksheet = sh.sheet1

# Clear and update
worksheet.clear()
worksheet.update([df.columns.values.tolist()] + df.values.tolist())
```
