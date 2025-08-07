import os
import sys
import django
import random
from datetime import date, timedelta
from faker import Faker

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recommendation_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

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

if __name__ == '__main__':
    print("=" * 60)
    print("🔐 Seeding authentication users...")
    create_superuser()
    seed_users(50)
    print("✅ All users seeded! Default password: demo123")
    print("=" * 60)

