"""
GitHub Statistics Service

Fetches live statistics from the GitHub repository to display on the About page.
Includes error handling and caching to ensure the page loads even if GitHub is unavailable.
"""

import requests
import logging
from django.conf import settings
from django.core.cache import cache
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)


class GitHubStatsService:
    """Service for fetching GitHub repository statistics"""
    
    def __init__(self):
        self.repo_owner = "mikerouse"
        self.repo_name = "cfc"
        self.base_url = "https://api.github.com"
        self.token = os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')
        
        # Cache keys
        self.cache_key_stats = "github_repo_stats"
        self.cache_key_issues = "github_repo_issues"
        self.cache_duration = 600  # 10 minutes
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests"""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Council-Finance-Counters/1.0'
        }
        
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        
        return headers
    
    def get_repository_stats(self) -> Dict:
        """
        Get basic repository statistics (stars, forks, open issues, etc.)
        Returns cached data if API is unavailable.
        """
        # Try cache first
        cached_stats = cache.get(self.cache_key_stats)
        if cached_stats:
            logger.info("✅ Using cached GitHub repository stats")
            return cached_stats
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}"
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                stats = {
                    'stars': data.get('stargazers_count', 0),
                    'forks': data.get('forks_count', 0),
                    'open_issues': data.get('open_issues_count', 0),
                    'watchers': data.get('subscribers_count', 0),
                    'size_kb': data.get('size', 0),
                    'language': data.get('language', 'Python'),
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at'),
                    'description': data.get('description', ''),
                    'license': data.get('license', {}).get('name', 'Unknown') if data.get('license') else 'Unknown',
                    'default_branch': data.get('default_branch', 'main'),
                    'topics': data.get('topics', []),
                    'cached_at': None  # Live data
                }
                
                # Cache the successful response
                cache.set(self.cache_key_stats, stats, self.cache_duration)
                logger.info(f"✅ Fetched GitHub repository stats: {stats['stars']} stars, {stats['open_issues']} issues")
                
                return stats
            else:
                logger.warning(f"GitHub API returned status {response.status_code}")
                return self._get_fallback_stats()
                
        except Exception as e:
            logger.error(f"Failed to fetch GitHub repository stats: {e}")
            return self._get_fallback_stats()
    
    def get_recent_issues(self, limit: int = 5) -> list:
        """
        Get recent issues from the repository.
        Returns cached data if API is unavailable.
        """
        # Try cache first
        cache_key = f"{self.cache_key_issues}_{limit}"
        cached_issues = cache.get(cache_key)
        if cached_issues:
            logger.info(f"✅ Using cached GitHub issues (limit: {limit})")
            return cached_issues
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues"
            params = {
                'state': 'all',
                'sort': 'created',
                'direction': 'desc',
                'per_page': limit
            }
            
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                issues = []
                for issue in data:
                    # Skip pull requests (they appear as issues in the API)
                    if 'pull_request' not in issue:
                        issues.append({
                            'number': issue.get('number'),
                            'title': issue.get('title', ''),
                            'state': issue.get('state', 'open'),
                            'created_at': issue.get('created_at'),
                            'updated_at': issue.get('updated_at'),
                            'user': issue.get('user', {}).get('login', 'Unknown'),
                            'labels': [label.get('name', '') for label in issue.get('labels', [])],
                            'html_url': issue.get('html_url', ''),
                            'cached_at': None  # Live data
                        })
                
                # Cache the successful response
                cache.set(cache_key, issues, self.cache_duration)
                logger.info(f"✅ Fetched {len(issues)} recent GitHub issues")
                
                return issues
            else:
                logger.warning(f"GitHub Issues API returned status {response.status_code}")
                return self._get_fallback_issues()
                
        except Exception as e:
            logger.error(f"Failed to fetch GitHub issues: {e}")
            return self._get_fallback_issues()
    
    def get_contributors(self, limit: int = 10) -> list:
        """
        Get repository contributors.
        Returns cached data if API is unavailable.
        """
        cache_key = f"github_contributors_{limit}"
        cached_contributors = cache.get(cache_key)
        if cached_contributors:
            logger.info(f"✅ Using cached GitHub contributors (limit: {limit})")
            return cached_contributors
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contributors"
            params = {'per_page': limit}
            
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                contributors = []
                for contributor in data:
                    contributors.append({
                        'login': contributor.get('login', ''),
                        'contributions': contributor.get('contributions', 0),
                        'avatar_url': contributor.get('avatar_url', ''),
                        'html_url': contributor.get('html_url', ''),
                        'type': contributor.get('type', 'User'),
                        'cached_at': None  # Live data
                    })
                
                # Cache the successful response
                cache.set(cache_key, contributors, self.cache_duration)
                logger.info(f"✅ Fetched {len(contributors)} GitHub contributors")
                
                return contributors
            else:
                logger.warning(f"GitHub Contributors API returned status {response.status_code}")
                return self._get_fallback_contributors()
                
        except Exception as e:
            logger.error(f"Failed to fetch GitHub contributors: {e}")
            return self._get_fallback_contributors()
    
    def _get_fallback_stats(self) -> Dict:
        """Fallback repository stats when API is unavailable"""
        from datetime import datetime
        
        return {
            'stars': '?',
            'forks': '?',
            'open_issues': '?',
            'watchers': '?',
            'size_kb': '?',
            'language': 'Python',
            'created_at': None,
            'updated_at': None,
            'description': 'UK Council Finance Data Platform',
            'license': 'Unknown',
            'default_branch': 'main',
            'topics': ['django', 'python', 'uk-councils', 'finance', 'open-data'],
            'cached_at': datetime.now().isoformat()
        }
    
    def _get_fallback_issues(self) -> list:
        """Fallback issues when API is unavailable"""
        from datetime import datetime
        
        return [{
            'number': '?',
            'title': 'GitHub API temporarily unavailable',
            'state': 'open',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'user': 'System',
            'labels': ['api-unavailable'],
            'html_url': f'https://github.com/{self.repo_owner}/{self.repo_name}/issues',
            'cached_at': datetime.now().isoformat()
        }]
    
    def _get_fallback_contributors(self) -> list:
        """Fallback contributors when API is unavailable"""
        from datetime import datetime
        
        return [{
            'login': 'mikerouse',
            'contributions': '?',
            'avatar_url': '',
            'html_url': f'https://github.com/mikerouse',
            'type': 'User',
            'cached_at': datetime.now().isoformat()
        }]