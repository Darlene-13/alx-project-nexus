"""
Management command to seed movie genres from TMDB API.
Usage: python manage.py seed_genres
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Seed movie genres from TMDB API."""
    
    help = 'Seed movie genres from TMDB API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-sync even if genres already exist',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🎭 Starting genre synchronization from TMDB...')
        )
        
        try:
            # Import here to avoid circular imports
            from services.movie_data_service import get_movie_data_service
            from apps.movies.models import Genre
            
            # Initialize service
            movie_service = get_movie_data_service()
            
            # Health check
            if options['verbose']:
                self.stdout.write('Checking API connectivity...')
            
            health = movie_service.health_check()
            if health['status'] != 'healthy':
                raise CommandError(f'Movie service unhealthy: {health}')
            
            if options['verbose']:
                self.stdout.write(self.style.SUCCESS('✅ API connectivity confirmed'))
            
            # Check existing genres
            existing_count = Genre.objects.count()
            
            if existing_count > 0 and not options['force']:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  {existing_count} genres already exist. Use --force to re-sync.'
                    )
                )
                
                # Show existing genres
                if options['verbose']:
                    self.stdout.write('\nExisting genres:')
                    for genre in Genre.objects.all()[:10]:
                        self.stdout.write(f'  • {genre.name} (TMDB ID: {genre.tmdb_id})')
                    
                    if existing_count > 10:
                        self.stdout.write(f'  ... and {existing_count - 10} more')
                
                return
            
            # Dry run mode
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('🔍 DRY RUN: Fetching genres to show what would be synced...')
                )
                
                # Get genres from TMDB without saving
                tmdb_service = movie_service.tmdb
                genres_data = tmdb_service.get_genres()
                
                self.stdout.write(f'\nWould sync {len(genres_data)} genres from TMDB:')
                for genre_data in genres_data:
                    self.stdout.write(f'  • {genre_data["name"]} (ID: {genre_data["id"]})')
                
                self.stdout.write(
                    self.style.SUCCESS(f'\n✅ DRY RUN: Would create/update {len(genres_data)} genres')
                )
                return
            
            # Actual sync
            start_time = timezone.now()
            
            if options['verbose']:
                self.stdout.write('Fetching genres from TMDB API...')
            
            genres_synced = movie_service.sync_genres_to_database()
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            # Success message
            self.stdout.write(
                self.style.SUCCESS(
                    f'🎉 Successfully synced {genres_synced} genres in {duration:.2f} seconds'
                )
            )
            
            # Show some synced genres
            if options['verbose'] and genres_synced > 0:
                self.stdout.write('\nGenres in database:')
                for genre in Genre.objects.all()[:10]:
                    self.stdout.write(f'  • {genre.name}')
                
                total_count = Genre.objects.count()
                if total_count > 10:
                    self.stdout.write(f'  ... and {total_count - 10} more')
            
            # Next steps
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🚀 Next step: python manage.py seed_movies --popular --target-count 500'
                )
            )
            
        except ImportError as e:
            raise CommandError(
                f'Import error - check if services are properly installed: {e}'
            )
        except Exception as e:
            logger.error(f'Genre sync failed: {e}')
            raise CommandError(f'Genre sync failed: {e}')
    
    def handle_label(self, label, **options):
        """Handle individual label (not used but required by Django)."""
        pass