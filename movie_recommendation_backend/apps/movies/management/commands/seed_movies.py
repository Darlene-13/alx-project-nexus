"""
Management command to seed movies from TMDB and OMDB APIs.
Usage: python manage.py seed_movies --popular --pages 10
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
        # Movie source options
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
        
        # Quantity options
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
        
        # Control options
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
            help='Show detailed progress output',
        )
        parser.add_argument(
            '--fast-mode',
            action='store_true',
            help='Skip OMDB enrichment for faster seeding',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🎬 Starting movie synchronization...')
        )
        
        try:
            # Import here to avoid circular imports
            from services.movie_data_service import get_movie_data_service
            from apps.movies.models import Movie, Genre
            
            # Initialize service
            movie_service = get_movie_data_service()
            
            # Health check
            if options['verbose']:
                self.stdout.write('🔍 Checking API connectivity...')
            
            health = movie_service.health_check()
            if health['status'] != 'healthy':
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Service health: {health["status"]}')
                )
                if health['status'] == 'unhealthy':
                    raise CommandError('Movie service is unhealthy')
            
            if options['verbose']:
                self.stdout.write(self.style.SUCCESS('✅ API connectivity confirmed'))
            
            # Check prerequisites
            self._check_prerequisites(options)
            
            # Calculate pages and validate options
            pages, movie_types = self._calculate_pages_and_types(options)
            
            # Check existing movies
            existing_count = Movie.objects.count()
            
            if existing_count > 100 and not options['force']:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  {existing_count} movies already exist. Use --force to add more.'
                    )
                )
                
                if options['verbose']:
                    self._show_existing_stats()
                
                return
            
            # Dry run mode
            if options['dry_run']:
                self._perform_dry_run(movie_service, pages, movie_types, options)
                return
            
            # Actual seeding
            self._perform_seeding(movie_service, pages, movie_types, options)
            
        except ImportError as e:
            raise CommandError(
                f'Import error - check if services are properly installed: {e}'
            )
        except Exception as e:
            logger.error(f'Movie seeding failed: {e}')
            raise CommandError(f'Movie seeding failed: {e}')
    
    def _check_prerequisites(self, options):
        """Check if prerequisites are met."""
        from apps.movies.models import Genre
        
        # Check if genres exist (unless skipping)
        if not options['skip_genres']:
            genre_count = Genre.objects.count()
            if genre_count == 0:
                self.stdout.write(
                    self.style.WARNING('⚠️  No genres found. Syncing genres first...')
                )
                
                # Auto-sync genres
                from services.movie_data_service import get_movie_data_service
                movie_service = get_movie_data_service()
                genres_synced = movie_service.sync_genres_to_database()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Synced {genres_synced} genres')
                )
            else:
                if options['verbose']:
                    self.stdout.write(f'✅ Found {genre_count} genres in database')
    
    def _calculate_pages_and_types(self, options):
        """Calculate pages and determine movie types to sync."""
        # Determine what to sync
        sync_popular = options['popular']
        sync_top_rated = options['top_rated']
        sync_trending = options['trending']
        
        # If nothing specified, default to popular
        if not any([sync_popular, sync_top_rated, sync_trending]):
            sync_popular = True
            self.stdout.write('ℹ️  No specific type selected, defaulting to popular movies')
        
        movie_types = []
        if sync_popular:
            movie_types.append('popular')
        if sync_top_rated:
            movie_types.append('top_rated')
        if sync_trending:
            movie_types.append('trending')
        
        # Calculate pages
        if options['target_count']:
            # Approximate 20 movies per page
            calculated_pages = max(1, options['target_count'] // (20 * len(movie_types)))
            pages = calculated_pages
            self.stdout.write(
                f'🎯 Targeting {options["target_count"]} movies '
                f'(~{pages} pages per type: {", ".join(movie_types)})'
            )
        else:
            pages = options['pages']
        
        return pages, movie_types
    
    def _show_existing_stats(self):
        """Show statistics about existing movies."""
        from apps.movies.models import Movie, Genre
        
        movie_count = Movie.objects.count()
        movies_with_ratings = Movie.objects.filter(tmdb_rating__isnull=False).count()
        movies_with_posters = Movie.objects.exclude(poster_path='').count()
        
        self.stdout.write(f'\n📊 Current Database Stats:')
        self.stdout.write(f'  • Total movies: {movie_count}')
        self.stdout.write(f'  • Movies with ratings: {movies_with_ratings}')
        self.stdout.write(f'  • Movies with posters: {movies_with_posters}')
        
        # Show genre distribution
        genres_with_movies = Genre.objects.annotate(
            movie_count=models.Count('movies')
        ).filter(movie_count__gt=0).order_by('-movie_count')[:5]
        
        if genres_with_movies:
            self.stdout.write(f'  • Top genres:')
            for genre in genres_with_movies:
                self.stdout.write(f'    - {genre.name}: {genre.movie_count} movies')
    
    def _perform_dry_run(self, movie_service, pages, movie_types, options):
        """Perform dry run to show what would be synced."""
        self.stdout.write(
            self.style.WARNING('🔍 DRY RUN: Fetching sample data to show what would be synced...')
        )
        
        total_estimated = 0
        
        for movie_type in movie_types:
            self.stdout.write(f'\n--- {movie_type.upper()} MOVIES ---')
            
            try:
                if movie_type == 'popular':
                    sample_data = movie_service.tmdb.get_popular_movies(page=1)
                elif movie_type == 'top_rated':
                    sample_data = movie_service.tmdb.get_top_rated_movies(page=1)
                elif movie_type == 'trending':
                    sample_data = movie_service.tmdb.get_trending_movies()
                
                sample_movies = sample_data.get('results', [])
                estimated_total = min(sample_data.get('total_results', 0), pages * 20)
                total_estimated += estimated_total
                
                self.stdout.write(f'📊 Would fetch ~{estimated_total} {movie_type} movies ({pages} pages)')
                
                # Show sample movies
                if options['verbose'] and sample_movies:
                    self.stdout.write('Sample movies:')
                    for movie in sample_movies[:5]:
                        title = movie.get('title', 'Unknown')
                        year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'Unknown'
                        rating = movie.get('vote_average', 'N/A')
                        self.stdout.write(f'  • {title} ({year}) - Rating: {rating}')
                    
                    if len(sample_movies) > 5:
                        self.stdout.write(f'  ... and {len(sample_movies) - 5} more in this page')
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error fetching {movie_type} movies: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ DRY RUN SUMMARY:\n'
                f'  • Would sync approximately {total_estimated} movies\n'
                f'  • From {len(movie_types)} source(s): {", ".join(movie_types)}\n'
                f'  • OMDB enrichment: {"Disabled (fast mode)" if options["fast_mode"] else "Enabled"}\n'
                f'  • Estimated time: {self._estimate_sync_time(total_estimated, options["fast_mode"])} minutes'
            )
        )
    
    def _perform_seeding(self, movie_service, pages, movie_types, options):
        """Perform the actual movie seeding."""
        start_time = timezone.now()
        total_stats = {
            'movies_created': 0,
            'movies_updated': 0,
            'errors': 0,
            'genres_synced': 0 if options['skip_genres'] else 0
        }
        
        try:
            # Use the service's seeding method
            if 'popular' in movie_types and 'top_rated' in movie_types:
                # Both types
                stats = movie_service.seed_database(
                    popular_pages=pages,
                    top_rated_pages=pages,
                    sync_genres=not options['skip_genres']
                )
            elif 'popular' in movie_types:
                # Only popular
                stats = movie_service.seed_database(
                    popular_pages=pages,
                    top_rated_pages=0,
                    sync_genres=not options['skip_genres']
                )
            elif 'top_rated' in movie_types:
                # Only top rated
                stats = movie_service.seed_database(
                    popular_pages=0,
                    top_rated_pages=pages,
                    sync_genres=not options['skip_genres']
                )
            else:
                # Trending or other
                stats = movie_service.seed_database(
                    popular_pages=pages,
                    top_rated_pages=0,
                    sync_genres=not options['skip_genres']
                )
            
            # Merge stats
            total_stats.update(stats)
            
        except Exception as e:
            raise CommandError(f'Seeding process failed: {e}')
        
        # Calculate duration
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        total_stats['duration'] = duration
        
        # Display results
        self._display_seeding_results(total_stats, movie_types, options)
        
        # Check for errors
        if total_stats.get('fatal_error'):
            raise CommandError(f'Fatal error occurred: {total_stats["fatal_error"]}')
    
    def _estimate_sync_time(self, movie_count, fast_mode):
        """Estimate sync time based on movie count and mode."""
        # Rough estimates: 2 seconds per movie with OMDB, 0.5 seconds without
        time_per_movie = 0.5 if fast_mode else 2.0
        estimated_seconds = movie_count * time_per_movie
        return round(estimated_seconds / 60, 1)
    
    def _display_seeding_results(self, stats, movie_types, options):
        """Display comprehensive seeding results."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎉 MOVIE SEEDING COMPLETED'))
        self.stdout.write('='*60)
        
        # Basic stats
        self.stdout.write(f'⏱️  Duration: {stats["duration"]:.2f} seconds')
        self.stdout.write(f'🎭 Genres synced: {stats["genres_synced"]}')
        self.stdout.write(f'🎬 Movies created: {stats["movies_created"]}')
        self.stdout.write(f'📝 Movies updated: {stats["movies_updated"]}')
        self.stdout.write(f'❌ Errors: {stats["errors"]}')
        self.stdout.write(f'📊 Types synced: {", ".join(movie_types)}')
        
        # Current database stats
        from apps.movies.models import Movie, Genre
        
        total_movies = Movie.objects.count()
        total_genres = Genre.objects.count()
        movies_with_ratings = Movie.objects.filter(tmdb_rating__isnull=False).count()
        
        self.stdout.write(f'\n📈 Database Status:')
        self.stdout.write(f'  • Total movies: {total_movies}')
        self.stdout.write(f'  • Total genres: {total_genres}')
        self.stdout.write(f'  • Movies with ratings: {movies_with_ratings}')
        
        # Data quality
        if total_movies > 0:
            quality_percentage = (movies_with_ratings / total_movies) * 100
            quality_color = self.style.SUCCESS if quality_percentage > 80 else self.style.WARNING
            self.stdout.write(
                quality_color(f'  • Data quality: {quality_percentage:.1f}% have ratings')
            )
        
        # Next steps
        self.stdout.write(f'\n🚀 Next Steps:')
        self.stdout.write(f'  1. Generate recommendations:')
        self.stdout.write(f'     python manage.py generate_recommendations --all-users')
        self.stdout.write(f'  2. Start Django server:')
        self.stdout.write(f'     python manage.py runserver')
        self.stdout.write(f'  3. Test API endpoints:')
        self.stdout.write(f'     curl http://localhost:8000/api/v1/recommendations/trending/')
        
        if stats['errors'] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠️  {stats["errors"]} errors occurred during seeding. '
                    f'Check logs for details.'
                )
            )