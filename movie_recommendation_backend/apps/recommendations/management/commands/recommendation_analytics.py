"""
Management command to display recommendation system analytics.
Usage: python manage.py recommendation_analytics --days 30
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Avg
from datetime import timedelta
import json

from services.recommendation_service import get_recommendation_service

class Command(BaseCommand):
    """Display recommendation system analytics and performance metrics."""
    
    help = 'Display recommendation system analytics and performance metrics'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to analyze (default: 30)',
        )
        parser.add_argument(
            '--algorithm',
            type=str,
            help='Analyze specific algorithm (leave empty for all)',
        )
        parser.add_argument(
            '--export-json',
            type=str,
            help='Export results to JSON file',
        )
        parser.add_argument(
            '--user-stats',
            action='store_true',
            help='Include detailed user interaction statistics',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'Recommendation Analytics Report ({options["days"]} days)')
        )
        self.stdout.write('=' * 60)
        
        try:
            # Initialize service
            rec_service = get_recommendation_service()
            
            # Get performance metrics
            performance = rec_service.get_recommendation_performance(
                algorithm=options['algorithm'],
                days=options['days']
            )
            
            analytics_data = {
                'report_date': timezone.now().isoformat(),
                'period_days': options['days'],
                'performance': performance
            }
            
            # Display performance by algorithm
            if isinstance(performance, dict) and 'algorithm' in performance:
                # Single algorithm
                self._display_algorithm_performance(performance)
            else:
                # Multiple algorithms
                for algorithm, metrics in performance.items():
                    self.stdout.write(f'\n{algorithm.upper()} Algorithm:')
                    self.stdout.write('-' * 30)
                    self._display_algorithm_performance(metrics)
            
            # User interaction statistics
            if options['user_stats']:
                self.stdout.write('\nUser Interaction Statistics:')
                self.stdout.write('-' * 30)
                user_stats = self._get_user_interaction_stats(options['days'])
                analytics_data['user_stats'] = user_stats
                
                for stat, value in user_stats.items():
                    self.stdout.write(f'{stat}: {value}')
            
            # Active experiments
            self.stdout.write('\nActive A/B Tests:')
            self.stdout.write('-' * 30)
            experiment_stats = self._get_experiment_stats()
            analytics_data['experiments'] = experiment_stats
            
            if experiment_stats:
                for exp in experiment_stats:
                    self.stdout.write(
                        f"'{exp['name']}': {exp['algorithm_a']} vs {exp['algorithm_b']} "
                        f"({exp['progress']:.1f}% complete)"
                    )
            else:
                self.stdout.write('No active experiments')
            
            # System health check
            self.stdout.write('\nSystem Health:')
            self.stdout.write('-' * 30)
            health_stats = self._get_system_health()
            analytics_data['system_health'] = health_stats
            
            for stat, value in health_stats.items():
                color = self.style.SUCCESS if value == 'healthy' or isinstance(value, (int, float)) else self.style.WARNING
                self.stdout.write(color(f'{stat}: {value}'))
            
            # Export to JSON if requested
            if options['export_json']:
                with open(options['export_json'], 'w') as f:
                    json.dump(analytics_data, f, indent=2, default=str)
                self.stdout.write(f'\nAnalytics exported to: {options["export_json"]}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Analytics generation failed: {e}')
            )
    
    def _display_algorithm_performance(self, metrics):
        """Display performance metrics for a single algorithm."""
        self.stdout.write(f'  Total Recommendations: {metrics.get("total_recommendations", 0)}')
        self.stdout.write(f'  Clicked Recommendations: {metrics.get("clicked_recommendations", 0)}')
        self.stdout.write(f'  Click-Through Rate: {metrics.get("click_through_rate", 0)}%')
        self.stdout.write(f'  Average Score: {metrics.get("average_score", 0)}')
    
    def _get_user_interaction_stats(self, days):
        """Get user interaction statistics."""
        from apps.recommendations.models import UserMovieInteraction
        from django.db.models import Count
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        interactions = UserMovieInteraction.objects.filter(
            timestamp__gte=cutoff_date
        )
        
        stats = {
            'Total Interactions': interactions.count(),
            'Unique Users': interactions.values('user').distinct().count(),
            'Unique Movies': interactions.values('movie').distinct().count(),
        }
        
        # Calculate average rating
        rating_interactions = interactions.filter(
            interaction_type='rating',
            rating__isnull=False
        )
        
        if rating_interactions.exists():
            avg_rating = rating_interactions.aggregate(avg=Avg('rating'))['avg']
            stats['Average Rating'] = round(avg_rating, 2) if avg_rating else 0
        else:
            stats['Average Rating'] = 'No ratings'
        
        # Interaction type breakdown
        interaction_counts = interactions.values('interaction_type').annotate(
            count=Count('id')
        )
        
        for item in interaction_counts:
            stats[f"{item['interaction_type'].title()} Interactions"] = item['count']
        
        return stats
    
    def _get_experiment_stats(self):
        """Get active experiment statistics."""
        from apps.recommendations.models import RecommendationExperiment
        
        active_experiments = RecommendationExperiment.objects.filter(
            is_active=True
        )
        
        experiments = []
        for exp in active_experiments:
            experiments.append({
                'name': exp.name,
                'algorithm_a': exp.algorithm_a,
                'algorithm_b': exp.algorithm_b,
                'progress': exp.progress_percentage,
                'start_date': exp.start_date,
                'end_date': exp.end_date,
                'traffic_split': exp.traffic_split
            })
        
        return experiments
    
    def _get_system_health(self):
        """Get system health statistics."""
        from apps.movies.models import Movie, Genre
        from apps.recommendations.models import UserRecommendations, UserMovieInteraction
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Basic counts
        stats = {
            'Total Users': User.objects.filter(is_active=True).count(),
            'Total Movies': Movie.objects.count(),
            'Total Genres': Genre.objects.count(),
            'Total Recommendations': UserRecommendations.objects.count(),
            'Total Interactions': UserMovieInteraction.objects.count(),
        }
        
        # Check for recent activity
        recent_cutoff = timezone.now() - timedelta(days=1)
        stats['Recent Interactions (24h)'] = UserMovieInteraction.objects.filter(
            timestamp__gte=recent_cutoff
        ).count()
        
        stats['Recent Recommendations (24h)'] = UserRecommendations.objects.filter(
            generated_at__gte=recent_cutoff
        ).count()
        
        # Data quality checks
        movies_with_ratings = Movie.objects.filter(tmdb_rating__isnull=False).count()
        total_movies = Movie.objects.count()
        
        if total_movies > 0:
            quality_percentage = (movies_with_ratings / total_movies) * 100
            stats['Movie Data Quality'] = f'{quality_percentage:.1f}% have ratings'
        
        return stats