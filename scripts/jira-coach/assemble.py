#!/usr/bin/env python3
"""
Assemble - Jira Feature Aggregator

Retrieves a Jira feature and all associated stories with PR/MR URLs.
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


class JiraAssembler:
    """Assembles Jira feature information with stories and PR/MR links."""

    def __init__(self, jira_url: str, token: str, email: Optional[str] = None):
        """Initialize Jira client."""
        self.jira_url = jira_url.rstrip('/')
        self.session = requests.Session()

        # Atlassian Jira Cloud requires basic auth (email + API token)
        # On-premise Jira can use Bearer token
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
        # If it's already just an ID like OSC-1234
        if re.match(r'^[A-Z]+-\d+$', url_or_id):
            return url_or_id

        # Extract from URL
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

    def get_issue_links(self, issue_key: str) -> List[Dict]:
        """Get all linked issues."""
        issue = self.get_issue(issue_key)
        links = []

        # Get issue links (e.g., "relates to", "is child of", etc.)
        for link in issue.get('fields', {}).get('issuelinks', []):
            if 'inwardIssue' in link:
                links.append({
                    'key': link['inwardIssue']['key'],
                    'summary': link['inwardIssue']['fields']['summary'],
                    'type': link['type']['inward'],
                    'direction': 'inward'
                })
            elif 'outwardIssue' in link:
                links.append({
                    'key': link['outwardIssue']['key'],
                    'summary': link['outwardIssue']['fields']['summary'],
                    'type': link['type']['outward'],
                    'direction': 'outward'
                })

        # Get subtasks
        for subtask in issue.get('fields', {}).get('subtasks', []):
            links.append({
                'key': subtask['key'],
                'summary': subtask['fields']['summary'],
                'type': 'subtask',
                'direction': 'child'
            })

        return links

    def extract_urls(self, text: str) -> Set[str]:
        """Extract PR/MR URLs from text."""
        if not text:
            return set()

        url_patterns = [
            r'https?://github\.com/[^\s)]+/pull/\d+',
            r'https?://gitlab\.com/[^\s)]+/-/merge_requests/\d+',
            r'https?://[^\s]+/pull/\d+',
            r'https?://[^\s]+/-/merge_requests/\d+',
        ]

        urls = set()
        for pattern in url_patterns:
            matches = re.findall(pattern, text)
            urls.update(matches)

        return urls

    def get_pr_mr_urls(self, issue_key: str) -> Set[str]:
        """Extract all PR/MR URLs from an issue."""
        issue = self.get_issue(issue_key)
        fields = issue.get('fields', {})
        urls = set()

        # Extract from description
        description = fields.get('description', '')
        if description:
            urls.update(self.extract_urls(description))

        # Extract from comments
        try:
            comments_url = f"{self.jira_url}/rest/api/2/issue/{issue_key}/comment"
            response = self.session.get(comments_url)
            response.raise_for_status()
            comments = response.json().get('comments', [])

            for comment in comments:
                body = comment.get('body', '')
                urls.update(self.extract_urls(body))
        except Exception as e:
            print(f"Warning: Could not fetch comments for {issue_key}: {e}", file=sys.stderr)

        # Extract from remote links (external links)
        for link in fields.get('issuelinks', []):
            if 'object' in link and 'url' in link['object']:
                url = link['object']['url']
                if 'pull' in url or 'merge_request' in url:
                    urls.add(url)

        return urls

    def analyze_feature(self, feature_id: str) -> Dict:
        """Analyze a feature and all its associated stories."""
        feature_key = self.extract_ticket_id(feature_id)

        print(f"Fetching feature {feature_key}...", file=sys.stderr)
        feature = self.get_issue(feature_key)
        feature_fields = feature.get('fields', {})

        result = {
            'feature': {
                'key': feature_key,
                'summary': feature_fields.get('summary', ''),
                'status': feature_fields.get('status', {}).get('name', ''),
                'type': feature_fields.get('issuetype', {}).get('name', ''),
                'assignee': feature_fields.get('assignee', {}).get('displayName', 'Unassigned') if feature_fields.get('assignee') else 'Unassigned',
                'description': feature_fields.get('description', ''),
                'url': f"{self.jira_url}/browse/{feature_key}",
                'pr_mr_urls': list(self.get_pr_mr_urls(feature_key))
            },
            'stories': []
        }

        # Get linked issues
        print(f"Fetching linked issues for {feature_key}...", file=sys.stderr)
        links = self.get_issue_links(feature_key)

        for link in links:
            story_key = link['key']
            print(f"  Processing {story_key}...", file=sys.stderr)

            try:
                story = self.get_issue(story_key)
                story_fields = story.get('fields', {})
                pr_mr_urls = self.get_pr_mr_urls(story_key)

                story_info = {
                    'key': story_key,
                    'summary': story_fields.get('summary', ''),
                    'status': story_fields.get('status', {}).get('name', ''),
                    'type': story_fields.get('issuetype', {}).get('name', ''),
                    'assignee': story_fields.get('assignee', {}).get('displayName', 'Unassigned') if story_fields.get('assignee') else 'Unassigned',
                    'link_type': link['type'],
                    'url': f"{self.jira_url}/browse/{story_key}",
                    'pr_mr_urls': list(pr_mr_urls),
                    'has_pr_mr': len(pr_mr_urls) > 0
                }

                result['stories'].append(story_info)
            except Exception as e:
                print(f"  Warning: Could not process {story_key}: {e}", file=sys.stderr)

        return result

    def format_output(self, data: Dict) -> str:
        """Format the analysis results."""
        feature = data['feature']
        stories = data['stories']

        output = []
        output.append("=" * 80)
        output.append(f"FEATURE: {feature['key']} - {feature['summary']}")
        output.append("=" * 80)
        output.append(f"Status: {feature['status']}")
        output.append(f"Type: {feature['type']}")
        output.append(f"Assignee: {feature['assignee']}")
        output.append(f"URL: {feature['url']}")

        if feature['pr_mr_urls']:
            output.append(f"\nFeature PR/MR URLs ({len(feature['pr_mr_urls'])}):")
            for url in feature['pr_mr_urls']:
                output.append(f"  - {url}")

        if feature['description']:
            output.append("\nDescription:")
            output.append("-" * 80)
            # Truncate long descriptions
            desc_lines = feature['description'].split('\n')[:10]
            output.extend(desc_lines)
            if len(feature['description'].split('\n')) > 10:
                output.append("  ... (truncated)")
            output.append("-" * 80)

        output.append(f"\nASSOCIATED STORIES ({len(stories)}):")
        output.append("=" * 80)

        # Group by status
        by_status = {}
        for story in stories:
            status = story['status']
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(story)

        # Count stories with/without PR/MR
        with_pr = sum(1 for s in stories if s['has_pr_mr'])
        without_pr = len(stories) - with_pr

        for status, status_stories in sorted(by_status.items()):
            output.append(f"\n{status} ({len(status_stories)}):")
            output.append("-" * 80)

            for story in status_stories:
                output.append(f"\n  {story['key']}: {story['summary']}")
                output.append(f"  Type: {story['type']} | Link: {story['link_type']} | Assignee: {story['assignee']}")
                output.append(f"  URL: {story['url']}")

                if story['pr_mr_urls']:
                    output.append(f"  PR/MR URLs ({len(story['pr_mr_urls'])}):")
                    for url in story['pr_mr_urls']:
                        output.append(f"    - {url}")
                else:
                    output.append("  ⚠️  No PR/MR URLs found")

        output.append("\n" + "=" * 80)
        output.append("SUMMARY")
        output.append("=" * 80)
        output.append(f"Total Stories: {len(stories)}")
        output.append(f"Stories with PR/MR: {with_pr}")
        output.append(f"Stories without PR/MR: {without_pr}")

        all_urls = set(feature['pr_mr_urls'])
        for story in stories:
            all_urls.update(story['pr_mr_urls'])

        output.append(f"\nTotal unique PR/MR URLs: {len(all_urls)}")
        if all_urls:
            output.append("\nAll PR/MR URLs:")
            for url in sorted(all_urls):
                output.append(f"  - {url}")

        return "\n".join(output)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Assemble Jira feature with stories and PR/MR URLs'
    )
    parser.add_argument(
        'feature',
        help='Jira feature URL or ID (e.g., OSC-1234 or https://issues.redhat.com/browse/OSC-1234)'
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

    # Atlassian Cloud requires email for basic auth
    if 'atlassian.net' in jira_url and not jira_email:
        print("Error: JIRA_EMAIL required for Atlassian Cloud authentication", file=sys.stderr)
        print("Set your Atlassian email: export JIRA_EMAIL='your-email@redhat.com'", file=sys.stderr)
        sys.exit(1)

    try:
        assembler = JiraAssembler(jira_url, jira_token, jira_email)
        data = assembler.analyze_feature(args.feature)

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(assembler.format_output(data))

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
