"""
Management command to generate recommendations for users.
Usage: python manage.py generate_recommendations --all-users
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
import logging

from services.recommendation_service import get_recommendation_service

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Generate movie recommendations for users."""
    
    help = 'Generate personalized movie recommendations for users'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Generate recommendations for specific user ID',
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Generate recommendations for all active users',
        )
        parser.add_argument(
            '--algorithm',
            type=str,
            choices=['collaborative', 'content_based', 'hybrid', 'trending'],
            default='hybrid',
            help='Recommendation algorithm to use (default: hybrid)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Number of recommendations per user (default: 10)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Process users in batches (default: 100)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regenerate even if fresh recommendations exist',
        )
        parser.add_argument(
            '--use-ab-testing',
            action='store_true',
            help='Use A/B testing framework for algorithm selection',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting recommendation generation...')
        )
        
        try:
            # Initialize service
            rec_service = get_recommendation_service()
            
            # Determine users to process
            if options['user_id']:
                users = [User.objects.get(id=options['user_id'])]
                self.stdout.write(f'Generating recommendations for user {options["user_id"]}')
            elif options['all_users']:
                users = User.objects.filter(is_active=True)
                self.stdout.write(f'Generating recommendations for {users.count()} active users')
            else:
                raise CommandError('Must specify --user-id or --all-users')
            
            # Process users
            total_generated = 0
            total_errors = 0
            start_time = timezone.now()
            
            for i, user in enumerate(users):
                try:
                    # Check if user needs fresh recommendations
                    if not options['force']:
                        from apps.recommendations.models import UserRecommendations
                        fresh_recs = UserRecommendations.get_user_recommendations(
                            user, limit=1
                        )
                        if fresh_recs.exists():
                            continue
                    
                    # Generate recommendations
                    if options['use_ab_testing']:
                        recommendations = rec_service.get_recommendations_with_ab_testing(
                            user.id, options['limit']
                        )
                    else:
                        algorithm = options['algorithm']
                        if algorithm == 'collaborative':
                            recommendations = rec_service.get_user_based_recommendations(
                                user.id, options['limit']
                            )
                        elif algorithm == 'content_based':
                            recommendations = rec_service.get_content_based_recommendations(
                                user.id, options['limit']
                            )
                        elif algorithm == 'trending':
                            recommendations = rec_service.get_trending_recommendations(
                                user.id, options['limit']
                            )
                        else:  # hybrid
                            recommendations = rec_service.get_hybrid_recommendations(
                                user.id, options['limit']
                            )
                    
                    total_generated += len(recommendations)
                    
                    # Progress update for batch processing
                    if (i + 1) % options['batch_size'] == 0:
                        elapsed = (timezone.now() - start_time).total_seconds()
                        self.stdout.write(
                            f'Processed {i + 1} users, generated {total_generated} recommendations '
                            f'({elapsed:.1f}s elapsed)'
                        )
                
                except Exception as e:
                    total_errors += 1
                    logger.error(f'Error generating recommendations for user {user.id}: {e}')
                    
                    if total_errors > 10:  # Stop if too many errors
                        raise CommandError(f'Too many errors ({total_errors}), stopping')
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nRecommendation generation completed in {duration:.2f} seconds:\n'
                    f'  - Users processed: {len(users)}\n'
                    f'  - Recommendations generated: {total_generated}\n'
                    f'  - Errors: {total_errors}\n'
                    f'  - Algorithm used: {options["algorithm"] if not options["use_ab_testing"] else "A/B Testing"}'
                )
            )
            
        except Exception as e:
            logger.error(f'Recommendation generation failed: {e}')
            raise CommandError(f'Recommendation generation failed: {e}')