# apps/movies/management/commands/test_celery.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from celery.result import AsyncResult
from celery import current_app
import time
import redis

# Import YOUR actual tasks from apps/movies/tasks.py
try:
    from apps.movies.tasks import (
        generate_recommendations_for_user,
        generate_recommendations_for_all_users, 
        update_movie_database
    )
    TASKS_AVAILABLE = True
except ImportError as e:
    TASKS_AVAILABLE = False
    IMPORT_ERROR = str(e)

User = get_user_model()

class Command(BaseCommand):
    help = 'Test your Movie Recommendation Celery tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            default='basic',
            choices=['basic', 'user-rec', 'all-users', 'movie-update', 'all'],
            help='Type of test to run'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Specific user ID to test recommendations for'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🎬 Testing YOUR Movie Recommendation Celery Tasks...'))
        
        if not TASKS_AVAILABLE:
            self.stdout.write(self.style.ERROR(f'❌ Could not import tasks: {IMPORT_ERROR}'))
            self.stdout.write('   Make sure apps/movies/tasks.py exists and is accessible')
            return
        
        self.stdout.write(self.style.SUCCESS('✅ Successfully imported tasks from apps.movies.tasks'))
        
        # Test basic connectivity first
        self.test_redis()
        self.test_workers()
        
        test_type = options['test_type']
        
        if test_type in ['basic', 'all']:
            self.test_basic_connectivity()
        
        if test_type in ['user-rec', 'all']:
            user_id = options.get('user_id') or self.get_test_user_id()
            if user_id:
                self.test_user_recommendations(user_id)
        
        if test_type in ['all-users', 'all']:
            self.test_all_users_recommendations()
        
        if test_type in ['movie-update', 'all']:
            self.test_movie_database_update()
        
        self.stdout.write(self.style.SUCCESS('✅ All tests completed!'))

    def test_redis(self):
        self.stdout.write('🔗 Testing Redis connection...')
        try:
            r = redis.Redis(host='redis', port=6379, db=0)
            r.set('test_key', 'working')
            result = r.get('test_key').decode()
            if result == 'working':
                self.stdout.write(self.style.SUCCESS('✅ Redis: Connected and working'))
                r.delete('test_key')  # Cleanup
            else:
                self.stdout.write(self.style.ERROR('❌ Redis: Connection test failed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Redis error: {e}'))

    def test_workers(self):
        self.stdout.write('👷 Testing Celery workers...')
        try:
            inspect = current_app.control.inspect()
            active = inspect.active()
            registered = inspect.registered()
            
            if active:
                worker_count = len(active.keys())
                self.stdout.write(self.style.SUCCESS(f'✅ Workers: {worker_count} active worker(s)'))
                
                if registered:
                    for worker, tasks in registered.items():
                        # Look for your specific tasks
                        your_tasks = [task for task in tasks if any(x in task for x in [
                            'generate_recommendations_for_user',
                            'generate_recommendations_for_all_users', 
                            'update_movie_database'
                        ])]
                        if your_tasks:
                            self.stdout.write(f'   📋 {worker}: Found your movie tasks!')
                            for task in your_tasks:
                                task_name = task.split('.')[-1]  # Get just the function name
                                self.stdout.write(f'      ✓ {task_name}')
                        else:
                            self.stdout.write(f'   📋 {worker}: {len(tasks)} tasks registered (searching for yours...)')
            else:
                self.stdout.write(self.style.ERROR('❌ Workers: No active workers found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Worker error: {e}'))

    def test_basic_connectivity(self):
        self.stdout.write('🔧 Testing basic Celery connectivity...')
        try:
            broker_url = current_app.conf.broker_url
            self.stdout.write(f'📡 Broker URL: {broker_url}')
            
            # Ping workers
            pong = current_app.control.ping(timeout=5)
            if pong:
                self.stdout.write(self.style.SUCCESS(f'✅ Connectivity: Workers responding ({len(pong)} workers)'))
                for worker_info in pong:
                    for worker_name, status in worker_info.items():
                        self.stdout.write(f'   🤖 {worker_name}: {status}')
            else:
                self.stdout.write(self.style.ERROR('❌ Connectivity: No workers responding'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Connectivity error: {e}'))

    def get_test_user_id(self):
        """Get a test user ID"""
        try:
            user = User.objects.filter(is_active=True).first()
            if user:
                username = getattr(user, 'username', getattr(user, 'email', f'User-{user.id}'))
                self.stdout.write(f'👤 Using test user: ID={user.id}, Name={username}')
                return user.id
            else:
                self.stdout.write(self.style.WARNING('⚠️  No active users found. Please create a user first.'))
                return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error getting test user: {e}'))
            return None

    def test_user_recommendations(self, user_id):
        self.stdout.write(f'🎯 Testing generate_recommendations_for_user(user_id={user_id}, limit=5)...')
        try:
            # Check if we have movies first
            try:
                from apps.movies.models import Movie
                movie_count = Movie.objects.filter(is_active=True).count()
                self.stdout.write(f'🎬 Found {movie_count} active movies in database')
                
                if movie_count == 0:
                    self.stdout.write(self.style.WARNING('⚠️  No active movies found. Task may return empty results.'))
            except ImportError:
                try:
                    from movies.models import Movie
                    movie_count = Movie.objects.filter(is_active=True).count()
                    self.stdout.write(f'🎬 Found {movie_count} active movies in database')
                except ImportError:
                    self.stdout.write(self.style.WARNING('⚠️  Could not import Movie model. Task may fail.'))
            
            result = generate_recommendations_for_user.delay(user_id, limit=5)
            self.stdout.write(f'📤 Task submitted: {result.task_id}')
            
            # Wait for completion
            for i in range(15):
                if result.ready():
                    break
                time.sleep(1)
                if i % 3 == 0:  # Show progress every 3 seconds
                    self.stdout.write(f'⏳ Processing... ({i+1}/15 seconds)')
            
            if result.successful():
                task_result = result.get()
                if task_result.get('success'):
                    rec_count = len(task_result.get('recommendations', []))
                    self.stdout.write(self.style.SUCCESS(f'✅ Task completed: Generated {rec_count} recommendations'))
                    
                    # Show recommendations
                    recommendations = task_result.get('recommendations', [])
                    if recommendations:
                        self.stdout.write('   🎬 Recommendations:')
                        for i, rec in enumerate(recommendations[:5], 1):
                            title = rec.get('title', 'Unknown')
                            score = rec.get('score', 0)
                            movie_id = rec.get('movie_id', 'N/A')
                            self.stdout.write(f'      {i}. "{title}" (ID: {movie_id}, Score: {score:.2f})')
                    else:
                        self.stdout.write('   📭 No recommendations returned')
                else:
                    error = task_result.get('error', 'Unknown error')
                    self.stdout.write(self.style.ERROR(f'❌ Task returned error: {error}'))
            else:
                self.stdout.write(self.style.ERROR('❌ Task failed or timed out'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Task execution error: {e}'))

    def test_all_users_recommendations(self):
        self.stdout.write('👥 Testing generate_recommendations_for_all_users()...')
        try:
            user_count = User.objects.filter(is_active=True).count()
            self.stdout.write(f'📊 Found {user_count} active users in database')
            
            if user_count == 0:
                self.stdout.write(self.style.WARNING('⚠️  No active users found. Task will have nothing to process.'))
                return
            
            result = generate_recommendations_for_all_users.delay()
            self.stdout.write(f'📤 Task submitted: {result.task_id}')
            
            # Wait for completion
            for i in range(15):
                if result.ready():
                    break
                time.sleep(1)
                if i % 3 == 0:
                    self.stdout.write(f'⏳ Processing... ({i+1}/15 seconds)')
            
            if result.successful():
                task_result = result.get()
                if task_result.get('success'):
                    queued = task_result.get('queued_users', 0)
                    self.stdout.write(self.style.SUCCESS(f'✅ Task completed: Queued recommendations for {queued}/{user_count} users'))
                else:
                    error = task_result.get('error', 'Unknown error')
                    self.stdout.write(self.style.ERROR(f'❌ Task returned error: {error}'))
            else:
                self.stdout.write(self.style.ERROR('❌ Task failed or timed out'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Task execution error: {e}'))

    def test_movie_database_update(self):
        self.stdout.write('🎬 Testing update_movie_database()...')
        try:
            result = update_movie_database.delay()
            self.stdout.write(f'📤 Task submitted: {result.task_id}')
            
            # Wait for completion
            for i in range(20):
                if result.ready():
                    break
                time.sleep(1)
                if i % 5 == 0:
                    self.stdout.write(f'⏳ Processing... ({i+1}/20 seconds)')
            
            if result.successful():
                task_result = result.get()
                if task_result.get('success'):
                    updated = task_result.get('updated_movies', 0)
                    self.stdout.write(self.style.SUCCESS(f'✅ Task completed: Updated {updated} movies'))
                    self.stdout.write('   💡 Note: This is currently a placeholder task')
                else:
                    error = task_result.get('error', 'Unknown error')
                    self.stdout.write(self.style.ERROR(f'❌ Task returned error: {error}'))
            else:
                self.stdout.write(self.style.ERROR('❌ Task failed or timed out'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Task execution error: {e}'))