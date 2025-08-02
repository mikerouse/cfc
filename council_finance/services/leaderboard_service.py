"""
Leaderboard Service
Provides API-friendly leaderboard data structure and calculations
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass, asdict
from datetime import datetime

from django.db.models import Q, F, Subquery, OuterRef
from django.core.cache import cache

from council_finance.models import (
    Council,
    DataField,
    FinancialFigure,
    FinancialYear,
    CouncilCharacteristic,
    UserProfile,
)

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardEntry:
    """Represents a single entry in a leaderboard"""
    rank: int
    council_name: str
    council_slug: str
    council_type: Optional[str]
    council_nation: Optional[str]
    value: Decimal
    display_value: Decimal  # Could be per capita
    population: Optional[int] = None
    per_capita_value: Optional[Decimal] = None
    year: Optional[str] = None
    change_from_previous: Optional[int] = None  # Rank change
    percentile: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert Decimal to float for JSON
        for key in ['value', 'display_value', 'per_capita_value']:
            if data.get(key) is not None:
                data[key] = float(data[key])
        return data


@dataclass
class ContributorEntry:
    """Represents a contributor in the leaderboard"""
    rank: int
    username: str
    user_id: int
    points: int
    badge: Optional[str]
    contributions_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeaderboardData:
    """Complete leaderboard data structure"""
    category: str
    category_name: str
    category_description: str
    entries: List[LeaderboardEntry]
    year: Optional[str] = None
    per_capita: bool = False
    total_count: int = 0
    generated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API-friendly dictionary"""
        return {
            'category': self.category,
            'category_name': self.category_name,
            'category_description': self.category_description,
            'year': self.year,
            'per_capita': self.per_capita,
            'total_count': self.total_count,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'entries': [entry.to_dict() for entry in self.entries]
        }
    
    def get_council_rank(self, council_slug: str) -> Optional[int]:
        """Get rank for a specific council"""
        for entry in self.entries:
            if entry.council_slug == council_slug:
                return entry.rank
        return None
    
    def get_percentile(self, council_slug: str) -> Optional[float]:
        """Get percentile for a specific council"""
        for entry in self.entries:
            if entry.council_slug == council_slug:
                return entry.percentile
        return None


class LeaderboardService:
    """Service for generating leaderboard data"""
    
    # Leaderboard category definitions
    CATEGORIES = {
        'contributors': {
            'name': 'Top Contributors',
            'description': 'Users who have contributed the most data',
            'icon': 'users',
            'type': 'user',
        },
        'total-debt': {
            'name': 'Total Debt',
            'description': 'Councils with the highest total debt levels',
            'field_slug': 'total-debt',
            'icon': 'calculator',
            'reverse': True,
        },
        'interest-payments': {
            'name': 'Interest Payments',
            'description': 'Councils paying the most in interest',
            'field_slug': 'interest-paid',
            'icon': 'currency-pound',
            'reverse': True,
        },
        'current-liabilities': {
            'name': 'Current Liabilities',
            'description': 'Councils with highest short-term liabilities',
            'field_slug': 'current-liabilities',
            'icon': 'trending-up',
            'reverse': True,
        },
        'long-term-liabilities': {
            'name': 'Long-term Liabilities',
            'description': 'Councils with highest long-term debt obligations',
            'field_slug': 'long-term-liabilities',
            'icon': 'chart-bar',
            'reverse': True,
        },
        'reserves-balances': {
            'name': 'Reserves & Balances',
            'description': 'Councils with the highest usable reserves',
            'field_slug': 'usable-reserves',
            'icon': 'check-circle',
            'reverse': True,
        },
        'council-tax-income': {
            'name': 'Council Tax Income',
            'description': 'Councils generating the most council tax revenue',
            'field_slug': 'council-tax-income',
            'icon': 'receipt-refund',
            'reverse': True,
        },
        'lowest-debt': {
            'name': 'Lowest Debt',
            'description': 'Councils with the lowest total debt levels',
            'field_slug': 'total-debt',
            'icon': 'badge-check',
            'reverse': False,
        },
        'lowest-interest': {
            'name': 'Lowest Interest Payments',
            'description': 'Councils paying the least in interest',
            'field_slug': 'interest-paid',
            'icon': 'emoji-happy',
            'reverse': False,
        },
    }
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        
    def get_leaderboard(
        self, 
        category: str, 
        year: Optional[str] = None,
        per_capita: bool = False,
        limit: int = 50
    ) -> Optional[LeaderboardData]:
        """Get leaderboard data for a specific category"""
        
        # Check cache
        cache_key = f"leaderboard:{category}:{year}:{per_capita}:{limit}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        # Validate category
        if category not in self.CATEGORIES:
            logger.error(f"Invalid leaderboard category: {category}")
            return None
            
        category_info = self.CATEGORIES[category]
        
        # Handle contributors differently
        if category == 'contributors':
            data = self._get_contributor_leaderboard(limit)
        else:
            data = self._get_financial_leaderboard(
                category, 
                category_info, 
                year, 
                per_capita, 
                limit
            )
            
        if data:
            # Cache the result
            cache.set(cache_key, data, self.cache_timeout)
            
        return data
    
    def _get_contributor_leaderboard(self, limit: int) -> LeaderboardData:
        """Get contributor leaderboard data"""
        profiles = (
            UserProfile.objects
            .select_related('user')
            .filter(points__gt=0)
            .order_by('-points')[:limit]
        )
        
        # Create leaderboard entries (not contributor entries for consistency)
        entries = []
        for idx, profile in enumerate(profiles):
            # Create a LeaderboardEntry with contributor data mapped to council fields
            entry = LeaderboardEntry(
                rank=idx + 1,
                council_name=profile.user.username,  # Map username to council_name for template consistency
                council_slug=str(profile.user.id),   # Map user_id to council_slug
                council_type=profile.badge() if hasattr(profile, 'badge') else None,  # Map badge to council_type
                council_nation=None,
                value=Decimal(str(profile.points)),
                display_value=Decimal(str(profile.points)),
                population=None,
                per_capita_value=None,
                year=None
            )
            # Add custom attributes for contributor data
            entry.username = profile.user.username
            entry.user_id = profile.user.id
            entry.points = profile.points
            entry.badge = profile.badge() if hasattr(profile, 'badge') else None
            entries.append(entry)
        
        return LeaderboardData(
            category='contributors',
            category_name=self.CATEGORIES['contributors']['name'],
            category_description=self.CATEGORIES['contributors']['description'],
            entries=entries,
            total_count=UserProfile.objects.filter(points__gt=0).count(),
            generated_at=datetime.now()
        )
    
    def _get_financial_leaderboard(
        self,
        category: str,
        category_info: Dict[str, Any],
        year: Optional[str],
        per_capita: bool,
        limit: int
    ) -> Optional[LeaderboardData]:
        """Get financial leaderboard data"""
        
        # Get financial year
        if not year:
            financial_year = FinancialYear.objects.filter(is_current=True).first()
            if not financial_year:
                financial_year = FinancialYear.objects.order_by('-start_date').first()
        else:
            financial_year = FinancialYear.objects.filter(label=year).first()
            
        if not financial_year:
            logger.error(f"No financial year found for: {year}")
            return None
            
        # Get the field
        field_slug = category_info.get('field_slug')
        if not field_slug:
            logger.error(f"No field_slug for category: {category}")
            return None
            
        try:
            field = DataField.objects.get(slug=field_slug)
        except DataField.DoesNotExist:
            logger.error(f"Field not found: {field_slug}")
            return None
            
        # Build query
        figures_query = FinancialFigure.objects.filter(
            field=field,
            year=financial_year,
            value__isnull=False
        ).select_related('council', 'council__council_type', 'council__council_nation')
        
        # Get all data for percentile calculation
        all_figures = list(figures_query)
        total_count = len(all_figures)
        
        if per_capita:
            entries = self._calculate_per_capita_rankings(
                all_figures, 
                category_info.get('reverse', True),
                limit
            )
        else:
            entries = self._calculate_absolute_rankings(
                all_figures,
                category_info.get('reverse', True),
                limit
            )
            
        # Calculate percentiles
        for entry in entries:
            entry.percentile = ((total_count - entry.rank + 1) / total_count) * 100
            
        return LeaderboardData(
            category=category,
            category_name=category_info['name'],
            category_description=category_info['description'],
            year=financial_year.label,
            per_capita=per_capita,
            entries=entries,
            total_count=total_count,
            generated_at=datetime.now()
        )
    
    def _calculate_per_capita_rankings(
        self, 
        figures: List[FinancialFigure],
        reverse: bool,
        limit: int
    ) -> List[LeaderboardEntry]:
        """Calculate per capita rankings"""
        
        # Get population field
        try:
            pop_field = DataField.objects.get(slug='population')
        except DataField.DoesNotExist:
            logger.error("Population field not found")
            return []
            
        # Get all populations in one query
        council_ids = [fig.council_id for fig in figures]
        populations = CouncilCharacteristic.objects.filter(
            council_id__in=council_ids,
            field=pop_field
        ).values('council_id', 'value')
        
        pop_map = {}
        for pop in populations:
            try:
                pop_map[pop['council_id']] = int(pop['value'])
            except (ValueError, TypeError):
                continue
                
        # Calculate per capita values
        entries_data = []
        for figure in figures:
            if figure.council_id in pop_map and pop_map[figure.council_id] > 0:
                population = pop_map[figure.council_id]
                per_capita = float(figure.value) / population
                
                entries_data.append({
                    'figure': figure,
                    'population': population,
                    'per_capita': per_capita,
                    'sort_value': per_capita
                })
                
        # Sort
        entries_data.sort(key=lambda x: x['sort_value'], reverse=reverse)
        
        # Create entries
        entries = []
        for idx, data in enumerate(entries_data[:limit]):
            figure = data['figure']
            entries.append(LeaderboardEntry(
                rank=idx + 1,
                council_name=figure.council.name,
                council_slug=figure.council.slug,
                council_type=figure.council.council_type.name if figure.council.council_type else None,
                council_nation=figure.council.council_nation.name if figure.council.council_nation else None,
                value=figure.value,
                display_value=Decimal(str(data['per_capita'])),
                population=data['population'],
                per_capita_value=Decimal(str(data['per_capita'])),
                year=figure.year.label
            ))
            
        return entries
    
    def _calculate_absolute_rankings(
        self,
        figures: List[FinancialFigure],
        reverse: bool,
        limit: int
    ) -> List[LeaderboardEntry]:
        """Calculate absolute value rankings"""
        
        # Sort figures
        figures.sort(key=lambda x: x.value, reverse=reverse)
        
        # Create entries
        entries = []
        for idx, figure in enumerate(figures[:limit]):
            entries.append(LeaderboardEntry(
                rank=idx + 1,
                council_name=figure.council.name,
                council_slug=figure.council.slug,
                council_type=figure.council.council_type.name if figure.council.council_type else None,
                council_nation=figure.council.council_nation.name if figure.council.council_nation else None,
                value=figure.value,
                display_value=figure.value,
                year=figure.year.label
            ))
            
        return entries
    
    def get_council_rankings(self, council_slug: str, year: Optional[str] = None) -> Dict[str, Any]:
        """Get all rankings for a specific council"""
        rankings = {}
        
        for category in self.CATEGORIES:
            if category == 'contributors':
                continue
                
            leaderboard = self.get_leaderboard(category, year, per_capita=False)
            if leaderboard:
                rank = leaderboard.get_council_rank(council_slug)
                if rank:
                    rankings[category] = {
                        'rank': rank,
                        'total': leaderboard.total_count,
                        'percentile': leaderboard.get_percentile(council_slug),
                        'category_name': leaderboard.category_name
                    }
                    
        return rankings