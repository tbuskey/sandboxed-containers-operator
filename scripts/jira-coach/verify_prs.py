#!/usr/bin/env python3
"""
PR Verification Helper

Verifies that PR/MR links from Jira actually exist and checks their status.
This is a helper utility for cross-referencing Jira tickets with actual code.
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Optional
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def extract_github_pr_info(url: str) -> Optional[Dict[str, str]]:
    """Extract owner, repo, and PR number from GitHub URL."""
    pattern = r'github\.com/([^/]+)/([^/]+)/pull/(\d+)'
    match = re.search(pattern, url)
    if match:
        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'pr_number': match.group(3),
            'platform': 'github'
        }
    return None


def extract_gitlab_mr_info(url: str) -> Optional[Dict[str, str]]:
    """Extract project path and MR number from GitLab URL."""
    pattern = r'gitlab\.com/([^/]+/[^/]+)/-/merge_requests/(\d+)'
    match = re.search(pattern, url)
    if match:
        return {
            'project': match.group(1),
            'mr_number': match.group(2),
            'platform': 'gitlab'
        }
    return None


def check_github_pr(owner: str, repo: str, pr_number: str, token: Optional[str] = None) -> Dict:
    """Check GitHub PR status via API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'token {token}'

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        pr_data = response.json()

        return {
            'exists': True,
            'state': pr_data['state'],  # open, closed
            'merged': pr_data.get('merged', False),
            'title': pr_data['title'],
            'author': pr_data['user']['login'],
            'created_at': pr_data['created_at'],
            'updated_at': pr_data['updated_at'],
            'merged_at': pr_data.get('merged_at'),
            'url': pr_data['html_url'],
            'status': 'merged' if pr_data.get('merged') else pr_data['state']
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {'exists': False, 'error': 'PR not found'}
        elif e.response.status_code == 403:
            return {'exists': None, 'error': 'API rate limit exceeded or access forbidden'}
        else:
            return {'exists': None, 'error': f'HTTP {e.response.status_code}'}
    except Exception as e:
        return {'exists': None, 'error': str(e)}


def check_gitlab_mr(project: str, mr_number: str, token: Optional[str] = None) -> Dict:
    """Check GitLab MR status via API."""
    # GitLab project path needs to be URL-encoded
    encoded_project = project.replace('/', '%2F')
    url = f"https://gitlab.com/api/v4/projects/{encoded_project}/merge_requests/{mr_number}"

    headers = {}
    if token:
        headers['PRIVATE-TOKEN'] = token

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        mr_data = response.json()

        return {
            'exists': True,
            'state': mr_data['state'],  # opened, closed, merged
            'merged': mr_data['state'] == 'merged',
            'title': mr_data['title'],
            'author': mr_data['author']['username'],
            'created_at': mr_data['created_at'],
            'updated_at': mr_data['updated_at'],
            'merged_at': mr_data.get('merged_at'),
            'url': mr_data['web_url'],
            'status': mr_data['state']
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {'exists': False, 'error': 'MR not found'}
        elif e.response.status_code == 403:
            return {'exists': None, 'error': 'Access forbidden'}
        else:
            return {'exists': None, 'error': f'HTTP {e.response.status_code}'}
    except Exception as e:
        return {'exists': None, 'error': str(e)}


def verify_pr_url(url: str, github_token: Optional[str] = None, gitlab_token: Optional[str] = None) -> Dict:
    """Verify a PR/MR URL and return its status."""
    result = {
        'url': url,
        'platform': None,
        'verified': False,
        'info': {}
    }

    # Try GitHub
    github_info = extract_github_pr_info(url)
    if github_info:
        result['platform'] = 'github'
        pr_status = check_github_pr(
            github_info['owner'],
            github_info['repo'],
            github_info['pr_number'],
            github_token
        )
        result['info'] = pr_status
        result['verified'] = pr_status.get('exists', False)
        return result

    # Try GitLab
    gitlab_info = extract_gitlab_mr_info(url)
    if gitlab_info:
        result['platform'] = 'gitlab'
        mr_status = check_gitlab_mr(
            gitlab_info['project'],
            gitlab_info['mr_number'],
            gitlab_token
        )
        result['info'] = mr_status
        result['verified'] = mr_status.get('exists', False)
        return result

    # Unknown platform
    result['info'] = {'error': 'Unsupported platform or invalid URL'}
    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Verify PR/MR URLs from Jira tickets'
    )
    parser.add_argument(
        'urls',
        nargs='+',
        help='PR/MR URLs to verify'
    )
    parser.add_argument(
        '--github-token',
        help='GitHub personal access token (for private repos or higher rate limits)'
    )
    parser.add_argument(
        '--gitlab-token',
        help='GitLab personal access token (for private repos)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    results = []
    for url in args.urls:
        result = verify_pr_url(url, args.github_token, args.gitlab_token)
        results.append(result)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("=" * 80)
        print("PR/MR VERIFICATION RESULTS")
        print("=" * 80)

        for result in results:
            print(f"\nURL: {result['url']}")
            print(f"Platform: {result['platform'] or 'Unknown'}")

            info = result['info']

            if result['verified']:
                print(f"✅ Verified: PR/MR exists")
                print(f"   Status: {info.get('status', 'unknown')}")
                print(f"   Title: {info.get('title', 'N/A')}")
                print(f"   Author: {info.get('author', 'N/A')}")

                if info.get('merged'):
                    print(f"   ✅ Merged: {info.get('merged_at', 'N/A')}")
                elif info.get('state') == 'closed':
                    print(f"   ⚠️  Closed (not merged)")
                elif info.get('state') == 'open':
                    print(f"   📝 Open")

            elif result['verified'] is False:
                print(f"❌ Not Found: {info.get('error', 'Unknown error')}")
            else:
                print(f"⚠️  Could not verify: {info.get('error', 'Unknown error')}")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        verified = sum(1 for r in results if r['verified'])
        not_found = sum(1 for r in results if r['verified'] is False)
        errors = sum(1 for r in results if r['verified'] is None)

        print(f"Total URLs: {len(results)}")
        print(f"Verified: {verified}")
        print(f"Not Found: {not_found}")
        print(f"Errors: {errors}")

        if verified > 0:
            merged = sum(1 for r in results if r['verified'] and r['info'].get('merged'))
            open_prs = sum(1 for r in results if r['verified'] and r['info'].get('state') == 'open')
            closed = sum(1 for r in results if r['verified'] and r['info'].get('state') == 'closed' and not r['info'].get('merged'))

            print(f"\nStatus breakdown:")
            print(f"  Merged: {merged}")
            print(f"  Open: {open_prs}")
            print(f"  Closed (not merged): {closed}")


if __name__ == '__main__':
    main()
