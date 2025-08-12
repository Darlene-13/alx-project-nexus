import os
import sys
import django
import random
import json
from datetime import date, timedelta
from faker import Faker

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recommendation_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from apps.movies.models import Movie
from apps.analytics.models import UserActivityLog, PopularityMetrics
User = get_user_model()
fake = Faker()

# Choices from your model
LANGUAGES = [lang[0] for lang in User._meta.get_field('preferred_language').choices]
DEVICES = ['android', 'ios', 'web']
ALGORITHMS = ['collaborative_filtering', 'content_based', 'hybrid', 'popularity_based']
DECADES = ['1980s', '1990s', '2000s', '2010s', '2020s']
RATINGS = ['G', 'PG', 'PG-13', 'R']
GENRES = [
    'Action', 'Adventure', 'Animation', 'Comedy', 'Crime',
    'Documentary', 'Drama', 'Family', 'Fantasy', 'History',
    'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction',
    'TV Movie', 'Thriller', 'War', 'Western'
]


# Analytics specific data
ACTION_TYPES = [
    'movie_view', 'movie_search', 'recommendation_click', 'email_open', 
    'email_click', 'push_click', 'rating_submit', 'favorite_add', 'watchlist_add'
]

SOURCES = ['web', 'mobile_app', 'email_campaign', 'push_notification', 'direct']
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
    'Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0 Firefox/88.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
]



def create_superuser():
    username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@movierecommendation.com')
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')

    User.objects.filter(username=username).delete()

    superuser = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name='Super',
        last_name='Admin'
    )
    print(f'✅ Superuser created: {superuser.username}')
    return superuser

def random_dob(min_age=18, max_age=50):
    today = date.today()
    start = today - timedelta(days=365 * max_age)
    end = today - timedelta(days=365 * min_age)
    return fake.date_between(start_date=start, end_date=end)

def generate_user(index):
    first = fake.first_name()
    last = fake.last_name()
    username = f"{first.lower()}.{last.lower()}{index}"
    email = f"{username}@example.com"

    user = User(
        username=username,
        email=email,
        password='demo123',
        first_name=first,
        last_name=last,
        is_premium=random.choice([True, False]),
        phone_number=fake.phone_number()[:15],
        date_of_birth=random_dob(),
        preferred_timezone='GMT+3',
        bio=fake.sentence(),
        preferred_language=random.choice(LANGUAGES),
        country=fake.country(),
        device_type=random.choice(DEVICES),
        device_token=fake.uuid4(),
        favorite_genres=random.sample(GENRES, random.randint(2, 6)),
        algorithm_preference=random.choice(ALGORITHMS),
        diversity_preference=round(random.uniform(0.2, 0.9), 2),
        novelty_preference=round(random.uniform(0.1, 0.8), 2),
        content_rating_preference=random.choice(RATINGS),
        preferred_decade=random.choice(DECADES),
        onboarding_completed=True,
        onboarding_completed_at=timezone.now(),
        cold_start_preferences_collected=True,
        allow_demographic_targeting=random.choice([True, False]),
        data_usage_consent=random.choice([True, True, False])
    )
    user.set_password('demo123')
    user.save()
    return user

def seed_users(count=150):
    print(f"🌱 Creating {count} users...")
    created = 0
    for i in range(count):
        try:
            user = generate_user(i)
            created += 1
            if created % 10 == 0:
                print(f"   → {created} users created...")
        except IntegrityError as e:
            print(f"⚠️  Failed to create user: {e}")
    print(f"✅ Created {created} users")

def generate_realistic_metadata(action_type, user, movie=None):
    """Generate realistic metadata based on action type"""
    base_metadata = {
        'browser': fake.random_element(['Chrome', 'Firefox', 'Safari', 'Edge']),
        'screen_resolution': fake.random_element(['1920x1080', '1366x768', '1440x900', '2560x1440']),
        'language': user.preferred_language if user else 'en',
        'timezone': user.preferred_timezone if user else 'GMT+3'
    }
    
    if action_type == 'movie_view':
        base_metadata.update({
            'watch_duration': random.randint(30, 7200),  # 30 seconds to 2 hours
            'completion_rate': round(random.uniform(0.1, 1.0), 2),
            'quality': fake.random_element(['720p', '1080p', '4K'])
        })
    elif action_type == 'rating_submit':
        base_metadata.update({
            'rating_value': round(random.uniform(1.0, 10.0), 1),
            'review_text': fake.sentence() if random.choice([True, False]) else None
        })
    elif action_type == 'movie_search':
        base_metadata.update({
            'search_query': fake.word(),
            'results_count': random.randint(0, 50),
            'clicked_result_position': random.randint(1, 10) if random.choice([True, False]) else None
        })
    elif action_type == 'recommendation_click':
        base_metadata.update({
            'recommendation_algorithm': user.algorithm_preference if user else 'collaborative_filtering',
            'position_in_list': random.randint(1, 20),
            'recommendation_score': round(random.uniform(0.5, 1.0), 3)
        })
    
    return base_metadata

def seed_user_activity_logs(days=30, activities_per_day=100):
    """Generate realistic user activity logs over a time period"""
    print(f"📊 Creating user activity logs for {days} days...")
    
    users = list(User.objects.all())
    movies = list(Movie.objects.all())
    
    if not users:
        print("❌ No users found! Please create users first.")
        return 0
    
    if not movies:
        print("❌ No movies found! Please create movies first.")
        return 0
    
    created_count = 0
    
    for day in range(days):
        # Create activities for this day
        activity_date = timezone.now() - timedelta(days=day)
        
        # Vary activity by day (more on weekends, less on weekdays)
        if activity_date.weekday() in [5, 6]:  # Weekend
            daily_activities = int(activities_per_day * 1.3)
        else:  # Weekday
            daily_activities = activities_per_day
        
        for _ in range(daily_activities):
            user = random.choice(users)
            movie = random.choice(movies) if random.choice([True, True, False]) else None
            action_type = fake.random_element(ACTION_TYPES)
            
            # Create realistic session ID
            session_id = f"sess_{fake.uuid4()}"
            
            # Generate realistic timestamp for this day
            start_of_day = activity_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = activity_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            timestamp = fake.date_time_between(start_date=start_of_day, end_date=end_of_day, tzinfo=timezone.utc)
            
            # Generate metadata
            metadata = generate_realistic_metadata(action_type, user, movie)
            
            try:
                activity_log = UserActivityLog.objects.create(
                    user=user,
                    session_id=session_id,
                    action_type=action_type,
                    movie=movie,
                    ip_address=fake.ipv4(),
                    user_agent=fake.random_element(USER_AGENTS),
                    referer=fake.url() if random.choice([True, False]) else None,
                    source=fake.random_element(SOURCES),
                    metadata=json.dumps(metadata),
                    timestamp=timestamp
                )
                created_count += 1
                
            except IntegrityError as e:
                print(f"⚠️  Failed to create activity log: {e}")
        
        if (day + 1) % 5 == 0:
            print(f"   → {day + 1} days processed, {created_count} activities created...")
    
    print(f"✅ Created {created_count} user activity logs")
    return created_count

def seed_popularity_metrics(days=30):
    """Generate popularity metrics based on user activity logs"""
    print(f"📈 Creating popularity metrics for {days} days...")
    
    movies = Movie.objects.all()
    if not movies:
        print("❌ No movies found! Please create movies first.")
        return 0
    
    created_count = 0
    
    for day in range(days):
        metric_date = (timezone.now() - timedelta(days=day)).date()
        
        for movie in movies:
            # Get activities for this movie on this day
            daily_activities = UserActivityLog.objects.filter(
                movie=movie,
                timestamp__date=metric_date
            )
            
            if daily_activities.exists():
                # Calculate real metrics from activity logs
                view_count = daily_activities.filter(action_type='movie_view').count()
                rating_activities = daily_activities.filter(action_type='rating_submit')
                rating_count = rating_activities.count()
                
                # Calculate average rating from metadata
                average_rating = 0.0
                if rating_count > 0:
                    ratings = []
                    for activity in rating_activities:
                        try:
                            metadata = json.loads(activity.metadata) if activity.metadata else {}
                            if 'rating_value' in metadata:
                                ratings.append(metadata['rating_value'])
                        except:
                            pass
                    if ratings:
                        average_rating = sum(ratings) / len(ratings)
                
                # Other metrics
                recommendation_count = daily_activities.filter(action_type='recommendation_click').count()
                like_count = daily_activities.filter(action_type='favorite_add').count()
                
                # Calculate CTR (simplified)
                click_through_rate = round(random.uniform(0.5, 8.0), 2) if view_count > 0 else 0.0
                
            else:
                # No activity for this movie on this day - create minimal metrics
                view_count = random.randint(0, 10) if random.choice([True, False, False]) else 0
                like_count = random.randint(0, max(1, view_count // 10))
                rating_count = random.randint(0, max(1, view_count // 20))
                average_rating = round(random.uniform(5.0, 9.5), 1) if rating_count > 0 else 0.0
                recommendation_count = random.randint(0, max(1, view_count // 5))
                click_through_rate = round(random.uniform(0.5, 3.0), 2) if view_count > 0 else 0.0
            
            # Create or update popularity metrics
            metric, created = PopularityMetrics.objects.get_or_create(
                movie=movie,
                date=metric_date,
                defaults={
                    'view_count': view_count,
                    'like_count': like_count,
                    'rating_count': rating_count,
                    'average_rating': average_rating,
                    'recommendation_count': recommendation_count,
                    'click_through_rate': click_through_rate
                }
            )
            
            if created:
                created_count += 1
        
        if (day + 1) % 5 == 0:
            print(f"   → {day + 1} days processed, {created_count} metrics created...")
    
    print(f"✅ Created {created_count} popularity metrics")
    return created_count

def show_analytics_summary():
    """Display a summary of generated analytics data"""
    print("\n" + "=" * 60)
    print("📊 ANALYTICS DATA SUMMARY")
    print("=" * 60)
    
    # User stats
    user_count = User.objects.count()
    print(f"👥 Total Users: {user_count}")
    
    # Activity stats
    activity_count = UserActivityLog.objects.count()
    print(f"📝 Total Activity Logs: {activity_count}")
    
    # Most active action types
    from django.db.models import Count
    top_actions = UserActivityLog.objects.values('action_type').annotate(
        count=Count('id')
    ).order_by('-count')[:3]
    
    print("🔥 Top Actions:")
    for action in top_actions:
        print(f"   → {action['action_type']}: {action['count']} times")
    
    # Popularity metrics stats
    metrics_count = PopularityMetrics.objects.count()
    print(f"📈 Total Popularity Metrics: {metrics_count}")
    
    # Top trending movies (last 7 days)
    trending = PopularityMetrics.get_trending_movies(days=7, limit=3)
    print("🎬 Top Trending Movies (Last 7 Days):")
    for i, trend in enumerate(trending, 1):
        try:
            movie = Movie.objects.get(id=trend['movie'])
            print(f"   {i}. {movie.title} - {trend['total_views']} views")
        except Movie.DoesNotExist:
            pass
    
    print("=" * 60)

if __name__ == '__main__':
    print("=" * 60)
    print("🎬 COMPREHENSIVE MOVIE PLATFORM SEEDER")
    print("=" * 60)
    
    # 1. Create superuser
    print("\n🔐 Creating superuser...")
    create_superuser()
    
    # 2. Create users
    print("\n👥 Creating users...")
    user_count = seed_users(50)
    
    # 3. Create user activity logs
    print("\n📊 Creating user activity logs...")
    activity_count = seed_user_activity_logs(days=30, activities_per_day=150)
    
    # 4. Create popularity metrics
    print("\n📈 Creating popularity metrics...")
    metrics_count = seed_popularity_metrics(days=30)
    
    # 5. Show summary
    show_analytics_summary()
    
    print(f"\n✅ SEEDING COMPLETE!")
    print(f"   → Users: {user_count}")
    print(f"   → Activity Logs: {activity_count}")
    print(f"   → Popularity Metrics: {metrics_count}")
    print(f"   → Default password: demo123")
    print("=" * 60)
