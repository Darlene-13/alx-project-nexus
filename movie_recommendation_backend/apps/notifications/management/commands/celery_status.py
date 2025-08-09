"""
This file contains management commands for checking Celery status and testing Celery functionality.
It includes commands to check the status of Celery workers, Redis, and to test email sending
using Celery tasks.
"""
from django.core.management.base import BaseCommand
from celery import current_app
import redis
import subprocess

class Command(BaseCommand):
    help = 'Check Celery worker and system status'
    
    def add_arguments(self, parser):
        parser.add_argument('--detailed', action='store_true', help='Show detailed information')
    
    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking Celery Status...")
        self.stdout.write("=" * 50)
        
        # Check Redis
        self._check_redis()
        
        # Check Workers
        self._check_workers(detailed=options['detailed'])
        
        # Check Queues (if detailed)
        if options['detailed']:
            self._check_queues()
    
    def _check_redis(self):
        """Check Redis connection"""
        try:
            result = subprocess.run(['redis-cli', 'ping'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS('✓ Redis: Running'))
            else:
                self.stdout.write(self.style.ERROR('✗ Redis: Not responding'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('✗ Redis: redis-cli not found'))
        except subprocess.TimeoutExpired:
            self.stdout.write(self.style.ERROR('✗ Redis: Connection timeout'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Redis: {e}'))
    
    def _check_workers(self, detailed=False):
        """Check Celery workers"""
        try:
            inspect = current_app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                self.stdout.write(self.style.SUCCESS(f'✓ Workers: {len(active_workers)} active'))
                for worker, tasks in active_workers.items():
                    self.stdout.write(f'  - {worker}: {len(tasks)} active tasks')
                    
                if detailed:
                    # Show registered tasks
                    registered = inspect.registered()
                    if registered:
                        self.stdout.write("\n📋 Registered Tasks:")
                        for worker, task_list in registered.items():
                            app_tasks = [t for t in task_list if 'notifications.' in t or 'analytics.' in t or 'movies.' in t]
                            if app_tasks:
                                self.stdout.write(f"  {worker}: {len(app_tasks)} app tasks")
            else:
                self.stdout.write(self.style.WARNING('⚠ Workers: No active workers'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Celery Error: {e}'))
    
    def _check_queues(self):
        """Check queue lengths"""
        try:
            from django.conf import settings
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            
            queues = ['notifications', 'analytics', 'recommendations']
            self.stdout.write("\n📊 Queue Status:")
            
            total_queued = 0
            for queue in queues:
                try:
                    length = r.llen(queue)
                    total_queued += length
                    status_style = self.style.SUCCESS if length < 10 else self.style.WARNING
                    self.stdout.write(f"  - {queue}: {status_style(str(length))} tasks")
                except Exception as e:
                    self.stdout.write(f"  - {queue}: Error ({e})")
            
            if total_queued > 50:
                self.stdout.write(self.style.WARNING(f"⚠ High queue volume: {total_queued} total tasks"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Queue check failed: {e}"))

