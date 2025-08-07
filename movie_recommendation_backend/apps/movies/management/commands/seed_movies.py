"""
Management command to seed movies from TMDB and OMDB APIs.
Usage: python manage.py seed_movies --popular --target-count 500
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Seed movies from TMDB and OMDB APIs with enriched data."""
    
    help = 'Seed movies from TMDB and OMDB APIs with enriched data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--popular',
            action='store_true',
            help='Sync popular movies',
        )
        parser.add_argument(
            '--top-rated',
            action='store_true',
            help='Sync top-rated movies',
        )
        parser.add_argument(
            '--trending',
            action='store_true',
            help='Sync trending movies',
        )
        parser.add_argument(
            '--pages',
            type=int,
            default=5,
            help='Number of pages to sync (default: 5, ~100 movies)',
        )
        parser.add_argument(
            '--target-count',
            type=int,
            help='Target number of movies to seed (overrides --pages)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if movies already exist',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )
        parser.add_argument(
            '--skip-genres',
            action='store_true',
            help='Skip genre synchronization',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
        parser.add_argument(
            '--omdb-enrichment',
            action='store_true',
            help='Enable OMDB enrichment for additional ratings (slower but richer data)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🎬 Starting movie synchronization from TMDB + OMDB...')
        )
        
        try:
            # Import here to avoid circular imports
            from services.movie_data_service import get_movie_data_service
            from apps.movies.models import Movie, Genre
            
            # Initialize service
            movie_service = get_movie_data_service()
            
            # Health check
            if options['verbose']:
                self.stdout.write('🏥 Checking API connectivity...')
            
            health = movie_service.health_check()
            if health['status'] != 'healthy':
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Service health: {health["status"]}')
                )
                if health['status'] == 'unhealthy':
                    raise CommandError('🚨 Movie service is unhealthy - check your API keys')
            
            if options['verbose']:
                self.stdout.write(self.style.SUCCESS('✅ API connectivity confirmed'))
                # Show service health details
                for service_name, service_health in health.get('services', {}).items():
                    status_icon = '✅' if service_health['status'] == 'healthy' else '❌'
                    self.stdout.write(f'  {status_icon} {service_name.upper()}: {service_health["status"]}')
            
            # Check prerequisites - genres should exist first
            genre_count = Genre.objects.count()
            if genre_count == 0 and not options['skip_genres']:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  No genres found! Running genre sync first...'
                    )
                )
                
                try:
                    genres_synced = movie_service.sync_genres_to_database()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Synced {genres_synced} genres as prerequisite')
                    )
                except Exception as e:
                    raise CommandError(f'Failed to sync genres: {e}')
            
            elif genre_count > 0 and options['verbose']:
                self.stdout.write(self.style.SUCCESS(f'✅ Found {genre_count} existing genres'))
            
            # Check existing movies
            existing_count = Movie.objects.count()
            
            if existing_count > 100 and not options['force']:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  {existing_count} movies already exist. Use --force to add more.'
                    )
                )
                
                if options['verbose']:
                    # Show sample existing movies
                    sample_movies = Movie.objects.order_by('-popularity_score')[:5]
                    self.stdout.write('\n📊 Top existing movies:')
                    for movie in sample_movies:
                        rating = f"⭐ {movie.tmdb_rating}" if movie.tmdb_rating else "No rating"
                        self.stdout.write(f'  • {movie.title} ({movie.year}) - {rating}')
                
                self.stdout.write(
                    f'\n💡 To add more movies: python manage.py seed_movies --force --popular --target-count {existing_count + 500}'
                )
                return
            
            # Calculate pages based on target count
            if options['target_count']:
                # Approximate 20 movies per page
                calculated_pages = max(1, options['target_count'] // 20)
                pages = calculated_pages
                self.stdout.write(
                    self.style.SUCCESS(
                        f'🎯 Targeting {options["target_count"]} movies (~{pages} pages)'
                    )
                )
            else:
                pages = options['pages']
            
            # Determine what to sync
            sync_popular = options['popular']
            sync_top_rated = options['top_rated']
            sync_trending = options['trending']
            
            # Default to popular if nothing specified
            if not any([sync_popular, sync_top_rated, sync_trending]):
                sync_popular = True
                self.stdout.write(
                    self.style.WARNING(
                        '📝 No specific type selected, defaulting to popular movies'
                    )
                )
            
            # Dry run mode
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('🔍 DRY RUN: Showing what would be synced...')
                )
                
                self._show_dry_run_preview(
                    movie_service, sync_popular, sync_top_rated, sync_trending, pages, options
                )
                return
            
            # Start actual seeding
            start_time = timezone.now()
            
            self.stdout.write('🚀 Starting movie seeding process...')
            
            if options['verbose']:
                sync_types = []
                if sync_popular: sync_types.append(f'Popular ({pages} pages)')
                if sync_top_rated: sync_types.append(f'Top-rated ({pages} pages)')
                if sync_trending: sync_types.append('Trending')
                
                self.stdout.write(f'📋 Sync plan: {", ".join(sync_types)}')
                self.stdout.write(f'🔗 OMDB enrichment: {"✅ Enabled" if options["omdb_enrichment"] else "❌ Disabled"}')
            
            # Use the service's seeding method
            stats = movie_service.seed_database(
                popular_pages=pages if sync_popular else 0,
                top_rated_pages=pages if sync_top_rated else 0,
                sync_genres=not options['skip_genres']
            )
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            # Display results
            self._display_seeding_results(stats, duration, options)
            
            # Show sample of seeded movies
            if options['verbose'] and stats.get('movies_created', 0) > 0:
                self._show_sample_movies()
            
            # Next steps guidance
            self._display_next_steps(stats)
            
            if stats.get('fatal_error'):
                raise CommandError(f'❌ Fatal error occurred: {stats["fatal_error"]}')
            
        except ImportError as e:
            raise CommandError(
                f'Import error - check if services are properly installed: {e}'
            )
        except Exception as e:
            logger.error(f'Movie seeding failed: {e}')
            raise CommandError(f'Movie seeding failed: {e}')
    
    def _show_dry_run_preview(self, movie_service, sync_popular, sync_top_rated, sync_trending, pages, options):
        """Show what would be synced in dry run mode."""
        
        try:
            preview_count = 0
            
            if sync_popular:
                self.stdout.write(f'\n📈 Would sync ~{pages * 20} popular movies:')
                
                # Get a sample of popular movies
                popular = movie_service.tmdb.get_popular_movies(page=1)
                sample_movies = popular.get('results', [])[:5]
                
                for movie in sample_movies:
                    year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'N/A'
                    rating = movie.get('vote_average', 'N/A')
                    self.stdout.write(f'  • {movie.get("title")} ({year}) - ⭐ {rating}')
                
                self.stdout.write(f'  ... and ~{pages * 20 - 5} more popular movies')
                preview_count += pages * 20
            
            if sync_top_rated:
                self.stdout.write(f'\n🏆 Would sync ~{pages * 20} top-rated movies')
                preview_count += pages * 20
            
            if sync_trending:
                self.stdout.write('\n🔥 Would sync trending movies')
                preview_count += 20
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ DRY RUN: Would potentially create/update ~{preview_count} movies'
                )
            )
            
            # Estimate time
            estimated_time = preview_count * 0.5  # Rough estimate: 0.5 seconds per movie
            self.stdout.write(f'⏱️  Estimated time: ~{estimated_time/60:.1f} minutes')
            
            if options['omdb_enrichment']:
                self.stdout.write('⚠️  OMDB enrichment would add ~2x more time')
            
        except Exception as e:
            self.stdout.write(f'Could not generate preview: {e}')
    
    def _display_seeding_results(self, stats, duration, options):
        """Display comprehensive seeding results."""
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('🎬 MOVIE SEEDING RESULTS')
        self.stdout.write('=' * 60)
        
        # Main statistics
        self.stdout.write(f'⏱️  Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)')
        self.stdout.write(f'🎭 Genres synced: {stats.get("genres_synced", 0)}')
        self.stdout.write(f'🎬 Movies created: {stats.get("movies_created", 0)}')
        self.stdout.write(f'🔄 Movies updated: {stats.get("movies_updated", 0)}')
        self.stdout.write(f'❌ Errors: {stats.get("errors", 0)}')
        
        # Calculate success rate
        total_processed = stats.get("movies_created", 0) + stats.get("movies_updated", 0) + stats.get("errors", 0)
        if total_processed > 0:
            success_rate = ((stats.get("movies_created", 0) + stats.get("movies_updated", 0)) / total_processed) * 100
            self.stdout.write(f'✅ Success rate: {success_rate:.1f}%')
        
        # Performance metrics
        if duration > 0:
            movies_per_minute = ((stats.get("movies_created", 0) + stats.get("movies_updated", 0)) / duration) * 60
            self.stdout.write(f'🚀 Processing speed: {movies_per_minute:.1f} movies/minute')
        
        # Show total in database now
        try:
            from apps.movies.models import Movie
            total_movies = Movie.objects.count()
            self.stdout.write(f'📊 Total movies in database: {total_movies}')
        except:
            pass
        
        self.stdout.write('=' * 60)
        
        # Status message
        if stats.get("errors", 0) == 0:
            self.stdout.write(self.style.SUCCESS('🎉 Seeding completed successfully!'))
        elif stats.get("errors", 0) < 10:
            self.stdout.write(self.style.WARNING('⚠️  Seeding completed with minor errors'))
        else:
            self.stdout.write(self.style.ERROR('❌ Seeding completed with significant errors'))
    
    def _show_sample_movies(self):
        """Show a sample of newly seeded movies."""
        try:
            from apps.movies.models import Movie
            
            recent_movies = Movie.objects.order_by('-created_at')[:5]
            
            self.stdout.write('\n🎬 Sample of newly added movies:')
            for movie in recent_movies:
                genres = ', '.join(movie.genre_names[:3]) if movie.genre_names else 'No genres'
                rating = f"⭐ {movie.tmdb_rating}" if movie.tmdb_rating else "No rating"
                self.stdout.write(f'  • {movie.title} ({movie.year}) - {rating} - {genres}')
        
        except Exception as e:
            self.stdout.write(f'Could not show sample movies: {e}')
    
    def _display_next_steps(self, stats):
        """Display helpful next steps."""
        
        movies_created = stats.get("movies_created", 0)
        
        if movies_created > 0:
            self.stdout.write('\n🚀 NEXT STEPS:')
            self.stdout.write('-' * 20)
            
            self.stdout.write('1. 👥 Create test users:')
            self.stdout.write('   python manage.py createsuperuser')
            
            self.stdout.write('\n2. 🎯 Generate recommendations:')
            self.stdout.write('   python manage.py generate_recommendations --all-users --algorithm hybrid')
            
            self.stdout.write('\n3. 🏃‍♀️ Start Django server:')
            self.stdout.write('   python manage.py runserver')
            
            self.stdout.write('\n4. 🧪 Test API endpoints:')
            self.stdout.write('   curl http://localhost:8000/api/v1/recommendations/trending/')
            
            self.stdout.write('\n5. 📊 View analytics:')
            self.stdout.write('   python manage.py recommendation_analytics --days 7')
            
            self.stdout.write('\n6. 🎛️  Admin panel:')
            self.stdout.write('   http://localhost:8000/admin/')
        
        else:
            self.stdout.write('\n💡 No movies were created. Try running with --force or check your API keys.')
    
    def handle_label(self, label, **options):
        """Handle individual label (not used but required by Django)."""
        pass