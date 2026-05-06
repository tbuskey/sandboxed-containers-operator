#!/usr/bin/env python3
"""
Jira Ticket Validator

Validates that Jira Feature/Epic tickets contain the necessary information:
- Why: Business justification and purpose
- Results: What the final product looks like (objects created, UI elements, log entries)
- Prove: How end users deploy/use the feature to produce the Results
- Design: Implementation details (what end users don't see)
- Evidence: Code location (PRs, repos) and testing proof
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


@dataclass
class ValidationResult:
    """Result of validating a single aspect of a ticket."""
    aspect: str
    present: bool
    score: int  # 0-3: 0=missing, 1=weak, 2=adequate, 3=strong
    evidence: List[str]
    suggestions: List[str]


@dataclass
class TicketValidation:
    """Complete validation result for a ticket."""
    ticket_key: str
    ticket_type: str
    summary: str
    status: str
    url: str
    why: ValidationResult
    results: ValidationResult
    prove: ValidationResult
    design: ValidationResult
    evidence: ValidationResult
    overall_score: float
    is_complete: bool
    missing_aspects: List[str]
    recommendations: List[str]


class JiraValidator:
    """Validates Jira tickets for completeness."""

    # Keywords that indicate "Why" information
    WHY_INDICATORS = [
        r'\bwhy\b',
        r'\bpurpose\b',
        r'\bgoal\b',
        r'\bobjective\b',
        r'\bbusiness\s+(?:value|justification|need|case)\b',
        r'\breason\b',
        r'\bmotivation\b',
        r'\bproblem\s+(?:statement|description)\b',
        r'\buser\s+(?:story|need|pain|problem)\b',
        r'\bcustomer\s+(?:request|need|demand)\b',
    ]

    # Keywords that indicate "Results" (what the final product looks like)
    RESULTS_INDICATORS = [
        r'\bresult',
        r'\boutput',
        r'\bcreates?\s+(?:a|an|the)?\s*(?:object|resource|pod|deployment|service|configmap|secret)',
        r'\b(?:UI|user\s+interface|screen|page|button|field|form)\b',
        r'\blog\s+(?:entry|entries|message|output|shows?)',
        r'\bdisplay',
        r'\bshow',
        r'\b(?:generates?|produces?)\s+(?:a|an|the)?\s*(?:file|report|output)',
        r'\b(?:new|updated|modified)\s+(?:object|resource|file|entry)',
        r'\b(?:appears?|visible|displayed)\b',
        r'\b(?:status|state)\s+(?:is|becomes|changes\s+to)',
        r'\bfinal\s+(?:product|result|state)',
        r'\blooks\s+like',
        r'\bexpected\s+(?:output|result|state)',
        # New patterns for specific, testable results
        r'\b(?:within|in|after|takes?)\s+\d+\s*(?:second|minute|hour)',  # Temporal expectations
        r'\bmax(?:imum)?\s+time',
        r'\btimeout',
        r'\b(?:which|in)\s+log',  # Log specificity
        r'\border\s+of\s+events',
        r'\bsequence',
    ]

    # Keywords that indicate "Prove" (how end users deploy/use the feature)
    PROVE_INDICATORS = [
        r'\bprove',
        r'\bdemonstrat',
        r'\bdeploy',
        r'\binstall',
        r'\bsetup',
        r'\bconfigur',
        r'\bapply\s+(?:the|a)?\s*(?:yaml|manifest|config)',
        r'\bcreate\s+(?:a|an|the)?\s*(?:pod|deployment|resource)',
        r'\brun\s+(?:the|a)?\s*command',
        r'\bexecute',
        r'\b(?:user|end-user|operator|admin)\s+(?:can|will|should|must)',
        r'\bhow\s+to\s+(?:use|deploy|enable|configure|setup)',
        r'\bsteps?\s+to',
        r'\bprocedure',
        r'\binstructions?',
        r'\busage',
        r'\bexample\s+(?:usage|deployment)',
        r'\b(?:oc|kubectl)\s+',
        r'\bcommand.*:',
        # New patterns for cluster/platform specifics
        r'\bcluster\s+(?:on|setup|type|configuration)',
        r'\b(?:AWS|Azure|ARO|bare[\s-]?metal|BM)\b',
        r'\b(?:GPU|TDX|SNP|SEV)\b',
        r'\binstance\s+(?:type|size)',
        r'\b(?:kata|coco|peer-?pods?)\b',
        r'\bdifference(?:s)?\s+from\s+(?:GA|docs|documentation)',
        r'\bverify\s+(?:with|by|using)',
        r'\bwait\s+(?:for|until)',
        r'\bcurl\s+',  # API verification commands
    ]

    # Keywords that indicate "Design" (implementation details users don't see)
    DESIGN_INDICATORS = [
        r'\bdesign',
        r'\barchitecture',
        r'\bimplementation\s+(?:plan|approach|details)\b',
        r'\btechnical\s+(?:design|approach|solution)\b',
        r'\binternal',
        r'\bunder\s+the\s+hood',
        r'\bbackend',
        r'\balgorithm',
        r'\bdata\s+(?:structure|model|flow)',
        r'\b(?:class|function|method|component)\s+(?:design|structure)',
        r'\bAPI\s+(?:design|interface)',
        r'\bmodule',
        r'\bpackage',
        r'\blibrary',
        r'\bdependenc(?:y|ies)',
        r'\brefactor',
        r'\b(?:will|shall)\s+(?:use|implement|create|add|modify)\b',
    ]

    # URL patterns for code repositories
    CODE_URL_PATTERNS = [
        r'https?://github\.com/[^\s)]+/(?:pull|tree|blob|commit)/[^\s)]+',
        r'https?://gitlab\.com/[^\s)]+/(?:-/)?(?:merge_requests|tree|blob|commit)/[^\s)]+',
        r'https?://[^\s]+/(?:pull|merge_requests?)/\d+',
    ]

    # Keywords that indicate testing evidence
    TESTING_INDICATORS = [
        r'\btest(?:s|ed|ing)?\b',
        r'\bQE\b',
        r'\bCI\b',
        r'\bpipeline\s+(?:pass|success|green)',
        r'\bverified',
        r'\bvalidated',
        r'\bproven',
        r'\bconfirmed',
        r'\btest\s+(?:result|output|log|report)',
        r'\b(?:unit|integration|e2e|functional)\s+test',
        r'\bcoverage',
        r'\btest\s+case',
        r'\bpassed\s+(?:test|verification)',
        r'\bscreenshot',
        r'\btest\s+evidence',
    ]

    def __init__(self, jira_url: str, token: str, email: Optional[str] = None):
        """Initialize Jira client."""
        self.jira_url = jira_url.rstrip('/')
        self.session = requests.Session()

        if email and token:
            # Basic auth for Atlassian Cloud (email + API token)
            self.session.auth = (email, token)
            self.session.headers.update({'Content-Type': 'application/json'})
        elif token:
            # Bearer token for on-premise or PAT
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            })
        else:
            raise ValueError("JIRA_TOKEN must be provided")

    def extract_ticket_id(self, url_or_id: str) -> str:
        """Extract ticket ID from URL or plain ID."""
        if re.match(r'^[A-Z]+-\d+$', url_or_id):
            return url_or_id

        match = re.search(r'([A-Z]+-\d+)', url_or_id)
        if match:
            return match.group(1)

        raise ValueError(f"Could not extract ticket ID from: {url_or_id}")

    def get_issue(self, issue_key: str) -> Dict:
        """Get issue details from Jira."""
        url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_comments(self, issue_key: str) -> List[Dict]:
        """Get all comments for an issue."""
        try:
            url = f"{self.jira_url}/rest/api/2/issue/{issue_key}/comment"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json().get('comments', [])
        except Exception as e:
            print(f"Warning: Could not fetch comments for {issue_key}: {e}", file=sys.stderr)
            return []

    def extract_urls(self, text: str, patterns: List[str]) -> Set[str]:
        """Extract URLs matching given patterns from text."""
        if not text:
            return set()

        urls = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.update(matches)

        return urls

    def check_patterns(self, text: str, patterns: List[str]) -> Tuple[bool, List[str]]:
        """Check if text contains any of the given patterns."""
        if not text:
            return False, []

        text_lower = text.lower()
        matches = []

        for pattern in patterns:
            if re.search(pattern, text_lower):
                # Extract the matching section (with context)
                match = re.search(pattern, text_lower)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                matches.append(context[:100])  # Limit to 100 chars

        return len(matches) > 0, matches

    def validate_why(self, issue: Dict, comments: List[Dict]) -> ValidationResult:
        """Validate the 'Why' aspect of a ticket."""
        description = issue.get('fields', {}).get('description', '') or ''

        # Combine all text sources
        all_text = description
        for comment in comments:
            all_text += '\n' + (comment.get('body', '') or '')

        has_why, evidence = self.check_patterns(all_text, self.WHY_INDICATORS)

        # Score based on quality
        score = 0
        suggestions = []

        if not has_why:
            score = 0
            suggestions.append("Add a 'Why' section explaining the business justification and purpose")
            suggestions.append("Describe the problem this solves or the value it provides")
            suggestions.append("Consider: Why is this work important? What problem does it solve?")
        elif len(evidence) == 1 and len(description) < 200:
            score = 1
            suggestions.append("The 'Why' explanation is brief. Consider adding more context about the business value")
        elif len(evidence) >= 2 or len(description) > 300:
            score = 3
            evidence = evidence[:2]  # Keep top 2 pieces of evidence
        else:
            score = 2

        return ValidationResult(
            aspect="Why (Purpose & Justification)",
            present=has_why,
            score=score,
            evidence=evidence,
            suggestions=suggestions
        )

    def validate_results(self, issue: Dict, comments: List[Dict]) -> ValidationResult:
        """Validate the 'Results' aspect (what the final product looks like)."""
        description = issue.get('fields', {}).get('description', '') or ''

        # Combine all text sources
        all_text = description
        for comment in comments:
            all_text += '\n' + (comment.get('body', '') or '')

        has_results, evidence = self.check_patterns(all_text, self.RESULTS_INDICATORS)

        score = 0
        suggestions = []

        if not has_results:
            score = 0
            suggestions.append("Add 'Results' section describing what the final product looks like")
            suggestions.append("Specify what objects/resources get created (Pods, Deployments, ConfigMaps, etc.)")
            suggestions.append("Describe any UI elements, screen changes, or visual output")
            suggestions.append("Note what appears in logs (specify WHICH log) or system output")
            suggestions.append("Include timing expectations (e.g., 'pod starts within 2 minutes')")
            suggestions.append("Make results testable/scriptable where possible")
            suggestions.append("Consider: What does the user see when this is deployed? Where? When?")
        elif len(evidence) == 1:
            score = 1
            suggestions.append("Add more concrete details about the Results")
            suggestions.append("List specific objects created, UI elements, or log entries")
        elif len(evidence) >= 3:
            score = 3
            evidence = evidence[:3]
        else:
            score = 2
            suggestions.append("Consider adding more specific examples of the final product")

        return ValidationResult(
            aspect="Results (What Final Product Looks Like)",
            present=has_results,
            score=score,
            evidence=evidence,
            suggestions=suggestions
        )

    def validate_prove(self, issue: Dict, comments: List[Dict]) -> ValidationResult:
        """Validate the 'Prove' aspect (how end users deploy/use the feature)."""
        description = issue.get('fields', {}).get('description', '') or ''

        # Combine all text sources
        all_text = description
        for comment in comments:
            all_text += '\n' + (comment.get('body', '') or '')

        has_prove, evidence = self.check_patterns(all_text, self.PROVE_INDICATORS)

        score = 0
        suggestions = []

        if not has_prove:
            score = 0
            suggestions.append("Add 'Prove' section showing how end users deploy/use this feature")
            suggestions.append("Specify cluster setup (platform: AWS/Azure/BM, instance type, GPU/TDX/SNP?)")
            suggestions.append("Note which mode: kata/coco/peer-pods and any platform-specific differences")
            suggestions.append("Include deployment steps or command examples")
            suggestions.append("Show verification commands (e.g., oc get, curl, logs)")
            suggestions.append("Link to internal docs if behavior differs from GA docs")
            suggestions.append("Consider: What commands does a user run? What YAML do they apply? What cluster setup?")
        elif len(evidence) == 1:
            score = 1
            suggestions.append("Add more detailed usage instructions or deployment steps")
            suggestions.append("Include specific commands or configuration examples")
        elif len(evidence) >= 3:
            score = 3
            evidence = evidence[:3]
        else:
            score = 2
            suggestions.append("Consider adding more complete usage examples")

        return ValidationResult(
            aspect="Prove (How Users Deploy/Use)",
            present=has_prove,
            score=score,
            evidence=evidence,
            suggestions=suggestions
        )

    def validate_design(self, issue: Dict, comments: List[Dict]) -> ValidationResult:
        """Validate the 'Design' aspect (implementation details users don't see)."""
        description = issue.get('fields', {}).get('description', '') or ''

        # Combine all text sources
        all_text = description
        for comment in comments:
            all_text += '\n' + (comment.get('body', '') or '')

        has_design, evidence = self.check_patterns(all_text, self.DESIGN_INDICATORS)

        score = 0
        suggestions = []

        # For Epics/Features, implementation details might be in child stories
        issue_type = issue.get('fields', {}).get('issuetype', {}).get('name', '').lower()
        is_epic_or_feature = 'epic' in issue_type or 'feature' in issue_type

        if not has_design:
            if is_epic_or_feature:
                score = 1  # Less critical for high-level tickets
                suggestions.append("Consider adding high-level design/architecture notes")
                suggestions.append("Internal implementation details can be in child stories")
            else:
                score = 0
                suggestions.append("Add 'Design' section with implementation details")
                suggestions.append("Describe internal architecture, components, or data structures")
                suggestions.append("Note what happens under the hood (what users don't see)")
                suggestions.append("Consider: What internal changes are needed? What components are affected?")
        elif len(evidence) >= 2:
            score = 3
            evidence = evidence[:2]
        else:
            score = 2

        return ValidationResult(
            aspect="Design (Implementation Details)",
            present=has_design,
            score=score,
            evidence=evidence,
            suggestions=suggestions
        )

    def validate_evidence(self, issue: Dict, comments: List[Dict]) -> ValidationResult:
        """Validate the 'Evidence' aspect (code location and testing proof)."""
        description = issue.get('fields', {}).get('description', '') or ''

        # Combine all text sources
        all_text = description
        for comment in comments:
            all_text += '\n' + (comment.get('body', '') or '')

        # Extract code URLs
        code_urls = self.extract_urls(all_text, self.CODE_URL_PATTERNS)

        # Also check for repo mentions
        repo_patterns = [
            r'https?://github\.com/[^\s/]+/[^\s/]+(?:/|$)',
            r'https?://gitlab\.com/[^\s/]+/[^\s/]+(?:/|$)',
        ]
        repo_mentions = self.extract_urls(all_text, repo_patterns)

        # Check for testing evidence
        has_testing, testing_evidence = self.check_patterns(all_text, self.TESTING_INDICATORS)

        score = 0
        suggestions = []
        evidence = list(code_urls)[:5]  # Top 5 URLs

        # Add testing evidence to evidence list
        if testing_evidence:
            evidence.extend([f"[TEST] {t}" for t in testing_evidence[:2]])

        status = issue.get('fields', {}).get('status', {}).get('name', '').lower()
        is_done = 'done' in status or 'closed' in status or 'resolved' in status
        is_in_progress = 'progress' in status or 'review' in status

        # Scoring logic
        has_code = len(code_urls) > 0 or len(repo_mentions) > 0

        if not has_code and not has_testing:
            if is_done:
                score = 0
                suggestions.append("⚠️  CRITICAL: Ticket is marked Done but has no PR/MR links or testing evidence!")
                suggestions.append("Add links to the PRs/MRs that implemented this work")
                suggestions.append("Add evidence of testing (test results, CI pipeline links, verification notes)")
            elif is_in_progress:
                score = 1
                suggestions.append("Add PR/MR links as code changes are created")
                suggestions.append("Link to the relevant repository or branch")
                suggestions.append("Add testing evidence as verification is completed")
            else:
                score = 2  # Acceptable for new tickets
                suggestions.append("Add repository links when work begins")
                suggestions.append("Link PRs/MRs and testing evidence as work progresses")
        elif has_code and has_testing:
            # Both code and testing evidence present
            if len(code_urls) >= 2 and len(testing_evidence) >= 1:
                score = 3
            else:
                score = 2
                if is_done:
                    suggestions.append("Verify all related PRs/MRs are linked")
                    suggestions.append("Add more comprehensive testing evidence if available")
        elif has_code:
            # Has code but missing testing evidence
            if len(code_urls) >= 2:
                score = 2
                if is_done or is_in_progress:
                    suggestions.append("Add evidence of testing (test results, CI output, verification)")
            else:
                score = 1
                suggestions.append("Add more PR/MR links")
                suggestions.append("Add evidence of testing")
        elif has_testing:
            # Has testing but missing code links
            score = 1
            suggestions.append("Add specific PR/MR links to show where code changes are")
        else:
            # Has repo mentions but no specific code links
            score = 1
            suggestions.append("Add specific PR/MR links (not just repository URLs)")
            suggestions.append("Add evidence of testing")

        return ValidationResult(
            aspect="Evidence (Code & Testing)",
            present=has_code or has_testing,
            score=score,
            evidence=evidence,
            suggestions=suggestions
        )

    def validate_ticket(self, ticket_id: str) -> TicketValidation:
        """Validate a complete ticket."""
        ticket_key = self.extract_ticket_id(ticket_id)

        print(f"Fetching ticket {ticket_key}...", file=sys.stderr)
        issue = self.get_issue(ticket_key)
        comments = self.get_comments(ticket_key)

        fields = issue.get('fields', {})

        # Validate each aspect
        why_result = self.validate_why(issue, comments)
        results_result = self.validate_results(issue, comments)
        prove_result = self.validate_prove(issue, comments)
        design_result = self.validate_design(issue, comments)
        evidence_result = self.validate_evidence(issue, comments)

        # Calculate overall score (0-100)
        max_score = 15  # 5 aspects * 3 max score each
        total_score = (why_result.score + results_result.score + prove_result.score +
                      design_result.score + evidence_result.score)
        overall_score = (total_score / max_score) * 100

        # Determine missing aspects
        missing = []
        if why_result.score == 0:
            missing.append("Why")
        if results_result.score == 0:
            missing.append("Results")
        if prove_result.score == 0:
            missing.append("Prove")
        if design_result.score == 0:
            missing.append("Design")
        if evidence_result.score == 0:
            missing.append("Evidence")

        # Is complete?
        is_complete = len(missing) == 0 and overall_score >= 75

        # Generate recommendations
        recommendations = []
        if not is_complete:
            recommendations.append(f"Overall completeness: {overall_score:.0f}% (target: 75%+)")

        # Add suggestions from each aspect
        for result in [why_result, results_result, prove_result, design_result, evidence_result]:
            recommendations.extend(result.suggestions)

        return TicketValidation(
            ticket_key=ticket_key,
            ticket_type=fields.get('issuetype', {}).get('name', 'Unknown'),
            summary=fields.get('summary', ''),
            status=fields.get('status', {}).get('name', 'Unknown'),
            url=f"{self.jira_url}/browse/{ticket_key}",
            why=why_result,
            results=results_result,
            prove=prove_result,
            design=design_result,
            evidence=evidence_result,
            overall_score=overall_score,
            is_complete=is_complete,
            missing_aspects=missing,
            recommendations=recommendations
        )

    def format_validation(self, validation: TicketValidation) -> str:
        """Format validation results as human-readable text."""
        output = []

        # Header
        output.append("=" * 80)
        output.append(f"JIRA TICKET VALIDATION: {validation.ticket_key}")
        output.append("=" * 80)
        output.append(f"Summary: {validation.summary}")
        output.append(f"Type: {validation.ticket_type}")
        output.append(f"Status: {validation.status}")
        output.append(f"URL: {validation.url}")
        output.append("")

        # Overall score
        if validation.is_complete:
            output.append(f"✅ COMPLETE - Score: {validation.overall_score:.0f}%")
        else:
            output.append(f"⚠️  INCOMPLETE - Score: {validation.overall_score:.0f}% (target: 75%+)")
            if validation.missing_aspects:
                output.append(f"   Missing: {', '.join(validation.missing_aspects)}")

        # Pillar scores summary
        output.append("")
        output.append("PILLAR SCORES:")
        output.append("-" * 40)

        total_score = 0
        for aspect_result in [validation.why, validation.results, validation.prove,
                             validation.design, validation.evidence]:
            total_score += aspect_result.score
            # Visual indicator
            if aspect_result.score >= 3:
                indicator = "✅"
            elif aspect_result.score >= 2:
                indicator = "✓ "
            elif aspect_result.score >= 1:
                indicator = "⚠️ "
            else:
                indicator = "❌"

            # Extract pillar name (e.g., "Why (Purpose & Justification)" -> "Why")
            pillar_name = aspect_result.aspect.split('(')[0].strip()
            output.append(f"  {pillar_name:12s} {aspect_result.score}/3  {indicator}")

        output.append("-" * 40)
        output.append(f"  {'Overall':12s} {validation.overall_score:.0f}%  ({total_score}/15 points)")

        output.append("")
        output.append("=" * 80)
        output.append("VALIDATION DETAILS")
        output.append("=" * 80)

        # Format each aspect
        for aspect_result in [validation.why, validation.results, validation.prove,
                             validation.design, validation.evidence]:
            output.append("")

            # Visual indicator
            if aspect_result.score >= 3:
                indicator = "✅"
            elif aspect_result.score >= 2:
                indicator = "✓ "
            elif aspect_result.score >= 1:
                indicator = "⚠️ "
            else:
                indicator = "❌"

            output.append(f"{indicator} {aspect_result.aspect}")
            output.append(f"   Score: {aspect_result.score}/3")

            if aspect_result.evidence:
                output.append("   Evidence found:")
                for i, evidence in enumerate(aspect_result.evidence[:3], 1):
                    # Truncate and clean evidence
                    clean = evidence.replace('\n', ' ').strip()
                    if len(clean) > 80:
                        clean = clean[:77] + "..."
                    output.append(f"     {i}. {clean}")

            if aspect_result.suggestions:
                output.append("   Suggestions:")
                for suggestion in aspect_result.suggestions:
                    output.append(f"     • {suggestion}")

        # Recommendations section
        if validation.recommendations:
            output.append("")
            output.append("=" * 80)
            output.append("RECOMMENDATIONS")
            output.append("=" * 80)

            for i, rec in enumerate(validation.recommendations, 1):
                output.append(f"{i}. {rec}")

        # Next steps coaching
        output.append("")
        output.append("=" * 80)
        output.append("NEXT STEPS")
        output.append("=" * 80)

        if validation.is_complete:
            output.append("✅ This ticket has all required information!")
            output.append("   Continue to monitor and update as work progresses.")
        else:
            output.append("To improve this ticket:")
            output.append("")

            step_num = 1
            if validation.why.score < 2:
                output.append(f"{step_num}. Add 'Why' section to the description:")
                output.append("   - Explain the business justification")
                output.append("   - Describe the problem being solved")
                output.append("   - Include user/customer impact")
                output.append("")
                step_num += 1

            if validation.results.score < 2:
                output.append(f"{step_num}. Define 'Results' (What Final Product Looks Like):")
                output.append("   - Describe what objects/resources get created")
                output.append("   - Specify WHICH log shows output (not just 'in logs')")
                output.append("   - Include timing: when events happen, max acceptable times")
                output.append("   - Note UI elements, screen changes, or visual output")
                output.append("   - Make it testable/scriptable with poll timeouts")
                output.append("   - Example: 'Pod Running status within 2 min, operator log shows X'")
                output.append("")
                step_num += 1

            if validation.prove.score < 2:
                output.append(f"{step_num}. Add 'Prove' (How Users Deploy/Use):")
                output.append("   - Specify cluster setup: platform, instance type, special HW (GPU/TDX/SNP)")
                output.append("   - Note mode: kata/coco/peer-pods and platform specifics")
                output.append("   - Show deployment steps or commands")
                output.append("   - Include verification steps (oc get, curl, etc.)")
                output.append("   - Note differences from GA docs or other platforms")
                output.append("   - Link internal docs if needed")
                output.append("")
                step_num += 1

            if validation.design.score < 2:
                output.append(f"{step_num}. Document 'Design' (Implementation Details):")
                output.append("   - Describe internal architecture/components")
                output.append("   - Note what happens under the hood")
                output.append("   - Identify technical dependencies")
                output.append("   - Keep user-facing details in Prove, not here")
                output.append("")
                step_num += 1

            if validation.evidence.score < 2:
                output.append(f"{step_num}. Add 'Evidence' (Code & Testing):")
                output.append("   - Link PRs/MRs as they're created")
                output.append("   - Add testing evidence (CI output, test results)")
                output.append("   - Include verification notes or screenshots")
                output.append("   - Update throughout development and testing")

        return "\n".join(output)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate Jira ticket for Why, Results, Prove, Design, Evidence completeness'
    )
    parser.add_argument(
        'ticket',
        help='Jira ticket URL or ID (e.g., OSC-1234 or https://issues.redhat.com/browse/OSC-1234)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    # Get credentials from environment
    jira_url = os.environ.get('JIRA_URL')
    jira_token = os.environ.get('JIRA_TOKEN')
    jira_email = os.environ.get('JIRA_EMAIL')

    if not jira_url:
        print("Error: JIRA_URL environment variable not set", file=sys.stderr)
        print("Example: export JIRA_URL='https://issues.redhat.com'", file=sys.stderr)
        sys.exit(1)

    if not jira_token:
        print("Error: JIRA_TOKEN environment variable not set", file=sys.stderr)
        print("Set your Jira personal access token: export JIRA_TOKEN='your-token'", file=sys.stderr)
        sys.exit(1)

    if 'atlassian.net' in jira_url and not jira_email:
        print("Error: JIRA_EMAIL required for Atlassian Cloud authentication", file=sys.stderr)
        print("Set your Atlassian email: export JIRA_EMAIL='your-email@redhat.com'", file=sys.stderr)
        sys.exit(1)

    try:
        validator = JiraValidator(jira_url, jira_token, jira_email)
        validation = validator.validate_ticket(args.ticket)

        if args.json:
            # Convert to dict for JSON serialization
            output = {
                'ticket_key': validation.ticket_key,
                'ticket_type': validation.ticket_type,
                'summary': validation.summary,
                'status': validation.status,
                'url': validation.url,
                'scores': {
                    'why': validation.why.score,
                    'results': validation.results.score,
                    'prove': validation.prove.score,
                    'design': validation.design.score,
                    'evidence': validation.evidence.score,
                    'total_points': (validation.why.score + validation.results.score +
                                   validation.prove.score + validation.design.score +
                                   validation.evidence.score),
                    'max_points': 15,
                    'overall_percentage': validation.overall_score
                },
                'overall_score': validation.overall_score,
                'is_complete': validation.is_complete,
                'missing_aspects': validation.missing_aspects,
                'aspects': {
                    'why': asdict(validation.why),
                    'results': asdict(validation.results),
                    'prove': asdict(validation.prove),
                    'design': asdict(validation.design),
                    'evidence': asdict(validation.evidence),
                },
                'recommendations': validation.recommendations
            }
            print(json.dumps(output, indent=2))
        else:
            print(validator.format_validation(validation))

    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP {e.response.status_code} - {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
