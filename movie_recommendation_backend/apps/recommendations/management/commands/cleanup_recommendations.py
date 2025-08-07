"""
Management command to clean up old recommendation data.
Usage: python manage.py cleanup_recommendations --days 30
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from services.recommendation_service import get_recommendation_service

class Command(BaseCommand):
    """Clean up old recommendation data to maintain database performance."""
    
    help = 'Clean up old recommendation data and optimize database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Remove unclicked recommendations older than N days (default: 30)',
        )
        parser.add_argument(
            '--interaction-days',
            type=int,
            default=90,
            help='Remove old interactions older than N days (default: 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without making changes',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run database vacuum after cleanup (PostgreSQL)',
        )
        parser.add_argument(
            '--clean-interactions',
            action='store_true',
            help='Also clean up old user interactions',
        )
        parser.add_argument(
            '--optimize-db',
            action='store_true',
            help='Run database optimization queries',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting recommendation cleanup...')
        )
        
        cleanup_stats = {
            'recommendations_removed': 0,
            'interactions_removed': 0,
            'experiments_cleaned': 0
        }
        
        try:
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No changes will be made')
                )
                cleanup_stats = self._dry_run_analysis(options)
            else:
                cleanup_stats = self._perform_cleanup(options)
            
            # Display results
            self._display_cleanup_results(cleanup_stats, options)
            
            # Optional database optimization
            if options['optimize_db'] and not options['dry_run']:
                self._optimize_database()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cleanup failed: {e}')
            )
    
    def _dry_run_analysis(self, options):
        """Analyze what would be cleaned without making changes."""
        from apps.recommendations.models import UserRecommendations, UserMovieInteraction
        
        cutoff_date = timezone.now() - timedelta(days=options['days'])
        interaction_cutoff = timezone.now() - timedelta(days=options['interaction_days'])
        
        # Count recommendations that would be removed
        old_recs = UserRecommendations.objects.filter(
            generated_at__lt=cutoff_date,
            clicked=False
        )
        
        stats = {
            'recommendations_removed': old_recs.count(),
            'interactions_removed': 0,
            'experiments_cleaned': 0
        }
        
        # Count interactions that would be removed
        if options['clean_interactions']:
            old_interactions = UserMovieInteraction.objects.filter(
                timestamp__lt=interaction_cutoff,
                interaction_type__in=['view', 'click']  # Only clean low-value interactions
            )
            stats['interactions_removed'] = old_interactions.count()
        
        # Count expired experiments
        expired_experiments = self._get_expired_experiments()
        stats['experiments_cleaned'] = len(expired_experiments)
        
        return stats
    
    def _perform_cleanup(self, options):
        """Perform the actual cleanup operations."""
        start_time = timezone.now()
        stats = {'recommendations_removed': 0, 'interactions_removed': 0, 'experiments_cleaned': 0}
        
        # Clean up recommendations
        rec_service = get_recommendation_service()
        stats['recommendations_removed'] = rec_service.cleanup_old_recommendations(options['days'])
        
        # Clean up interactions if requested
        if options['clean_interactions']:
            stats['interactions_removed'] = self._cleanup_old_interactions(options['interaction_days'])
        
        # Clean up expired experiments
        stats['experiments_cleaned'] = self._cleanup_expired_experiments()
        
        # Optional database vacuum
        if options['vacuum']:
            self._vacuum_database()
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        stats['duration'] = duration
        
        return stats
    
    def _cleanup_old_interactions(self, days):
        """Clean up old, low-value user interactions."""
        from apps.recommendations.models import UserMovieInteraction
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Only remove low-value interactions (keep ratings, favorites, etc.)
        low_value_interactions = UserMovieInteraction.objects.filter(
            timestamp__lt=cutoff_date,
            interaction_type__in=['view', 'click'],  # Keep ratings, favorites, etc.
        )
        
        count = low_value_interactions.count()
        
        with transaction.atomic():
            low_value_interactions.delete()
        
        self.stdout.write(f'Removed {count} old interactions')
        return count
    
    def _cleanup_expired_experiments(self):
        """Clean up completed A/B test experiments."""
        from apps.recommendations.models import RecommendationExperiment
        
        # Find experiments that ended more than 30 days ago
        cutoff_date = timezone.now() - timedelta(days=30)
        
        expired_experiments = RecommendationExperiment.objects.filter(
            end_date__lt=cutoff_date,
            is_active=False
        )
        
        count = expired_experiments.count()
        
        if count > 0:
            # Archive experiment data before deletion
            for exp in expired_experiments:
                self._archive_experiment_data(exp)
            
            expired_experiments.delete()
            self.stdout.write(f'Cleaned up {count} expired experiments')
        
        return count
    
    def _get_expired_experiments(self):
        """Get list of expired experiments for dry run."""
        from apps.recommendations.models import RecommendationExperiment
        
        cutoff_date = timezone.now() - timedelta(days=30)
        
        return list(RecommendationExperiment.objects.filter(
            end_date__lt=cutoff_date,
            is_active=False
        ).values_list('name', flat=True))
    
    def _archive_experiment_data(self, experiment):
        """Archive experiment data before deletion."""
        # This could save experiment results to a separate archive table
        # or export to a file for historical analysis
        try:
            metrics = experiment.calculate_metrics()
            if metrics:
                # Log final results
                self.stdout.write(f'Archiving experiment: {experiment.name}')
                # In a real implementation, you might save this to an archive table
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not archive experiment {experiment.name}: {e}')
            )
    
    def _vacuum_database(self):
        """Run database vacuum (PostgreSQL specific)."""
        self.stdout.write('Running database vacuum...')
        
        try:
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Vacuum specific tables
                tables_to_vacuum = [
                    'user_recommendations',
                    'user_movie_interactions',
                    'recommendation_experiments'
                ]
                
                for table in tables_to_vacuum:
                    cursor.execute(f'VACUUM ANALYZE {table};')
                    self.stdout.write(f'Vacuumed table: {table}')
                
            self.stdout.write(self.style.SUCCESS('Database vacuum completed'))
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Database vacuum failed (might not be PostgreSQL): {e}')
            )
    
    def _optimize_database(self):
        """Run database optimization queries."""
        self.stdout.write('Running database optimization...')
        
        try:
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Update table statistics
                optimization_queries = [
                    "ANALYZE user_recommendations;",
                    "ANALYZE user_movie_interactions;",
                    "ANALYZE movies;",
                    "REINDEX INDEX idx_recommendations_user_score;",
                    "REINDEX INDEX idx_interactions_user_type;",
                ]
                
                for query in optimization_queries:
                    try:
                        cursor.execute(query)
                        self.stdout.write(f'Executed: {query}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'Query failed: {query} - {e}')
                        )
                
            self.stdout.write(self.style.SUCCESS('Database optimization completed'))
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Database optimization failed: {e}')
            )
    
    def _display_cleanup_results(self, stats, options):
        """Display cleanup results."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('CLEANUP RESULTS'))
        self.stdout.write('='*50)
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes made'))
            self.stdout.write(f'Would remove {stats["recommendations_removed"]} old recommendations')
            if options['clean_interactions']:
                self.stdout.write(f'Would remove {stats["interactions_removed"]} old interactions')
            self.stdout.write(f'Would clean {stats["experiments_cleaned"]} expired experiments')
        else:
            self.stdout.write(f'Removed {stats["recommendations_removed"]} old recommendations')
            if options['clean_interactions']:
                self.stdout.write(f'Removed {stats["interactions_removed"]} old interactions')
            self.stdout.write(f'Cleaned {stats["experiments_cleaned"]} expired experiments')
            
            if 'duration' in stats:
                self.stdout.write(f'Total cleanup time: {stats["duration"]:.2f} seconds')
        
        self.stdout.write('='*50)