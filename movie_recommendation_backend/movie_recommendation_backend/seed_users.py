import os
import sys
import django
from django.conf import settings
import random

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recommendation_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

# Realistic names for seeding
FIRST_NAMES = [
    'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
    'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
    'Thomas', 'Sarah', 'Christopher', 'Karen', 'Charles', 'Nancy', 'Daniel', 'Lisa',
    'Matthew', 'Betty', 'Anthony', 'Helen', 'Mark', 'Sandra', 'Donald', 'Donna',
    'Steven', 'Carol', 'Paul', 'Ruth', 'Andrew', 'Sharon', 'Joshua', 'Michelle',
    'Kenneth', 'Laura', 'Kevin', 'Sarah', 'Brian', 'Kimberly', 'George', 'Deborah',
    'Timothy', 'Dorothy', 'Ronald', 'Lisa', 'Jason', 'Nancy', 'Edward', 'Karen',
    'Jeffrey', 'Betty', 'Ryan', 'Helen', 'Jacob', 'Sandra', 'Gary', 'Donna',
    'Nicholas', 'Carol', 'Eric', 'Ruth', 'Jonathan', 'Sharon', 'Stephen', 'Michelle',
    'Larry', 'Laura', 'Justin', 'Sarah', 'Scott', 'Kimberly', 'Brandon', 'Deborah',
    'Benjamin', 'Dorothy', 'Samuel', 'Amy', 'Gregory', 'Angela', 'Alexander', 'Ashley',
    'Patrick', 'Brenda', 'Frank', 'Emma', 'Raymond', 'Olivia', 'Jack', 'Cynthia',
    'Dennis', 'Marie', 'Jerry', 'Janet', 'Tyler', 'Catherine', 'Aaron', 'Frances',
    'Jose', 'Christine', 'Henry', 'Samantha', 'Adam', 'Debra', 'Douglas', 'Rachel',
    'Zachary', 'Carolyn', 'Peter', 'Janet', 'Kyle', 'Virginia', 'Noah', 'Maria'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
    'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
    'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill',
    'Flores', 'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell',
    'Mitchell', 'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner',
    'Diaz', 'Parker', 'Cruz', 'Edwards', 'Collins', 'Reyes', 'Stewart', 'Morris',
    'Morales', 'Murphy', 'Cook', 'Rogers', 'Gutierrez', 'Ortiz', 'Morgan',
    'Cooper', 'Peterson', 'Bailey', 'Reed', 'Kelly', 'Howard', 'Ramos', 'Kim',
    'Cox', 'Ward', 'Richardson', 'Watson', 'Brooks', 'Chavez', 'Wood', 'James',
    'Bennett', 'Gray', 'Mendoza', 'Ruiz', 'Hughes', 'Price', 'Alvarez', 'Castillo',
    'Sanders', 'Patel', 'Myers', 'Long', 'Ross', 'Foster', 'Jimenez'
]

def create_superuser():
    """Create superuser from environment variables or defaults"""
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@movierecommendation.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
    
    try:
        if not User.objects.filter(username=username).exists():
            superuser = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='Super',
                last_name='Admin'
            )
            print(f'👑 Superuser created: {username} ({email})')
            return superuser
        else:
            print(f'👑 Superuser already exists: {username}')
            return User.objects.get(username=username)
    except IntegrityError as e:
        print(f'⚠️  Superuser creation failed: {e}')
        return None

def generate_username(first_name, last_name, index):
    """Generate a unique username"""
    base_username = f"{first_name.lower()}.{last_name.lower()}"
    
    # Add number if needed to make it unique
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    return username

def get_sample_genres(index):
    """Return sample genre preferences for users"""
    all_genres = [
        'Action', 'Adventure', 'Animation', 'Comedy', 'Crime',
        'Documentary', 'Drama', 'Family', 'Fantasy', 'History',
        'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction',
        'TV Movie', 'Thriller', 'War', 'Western'
    ]
    
    # Use index as seed for consistent results
    random.seed(index)
    num_genres = random.randint(2, 6)
    selected_genres = random.sample(all_genres, num_genres)
    return selected_genres

def get_sample_preferences(index):
    """Return sample user preferences"""
    random.seed(index)
    
    algorithms = ['collaborative_filtering', 'content_based', 'hybrid', 'popularity_based']
    decades = ['1980s', '1990s', '2000s', '2010s', '2020s']
    ratings = ['G', 'PG', 'PG-13', 'R']
    
    return {
        'algorithm_preference': random.choice(algorithms),
        'preferred_decade': random.choice(decades),
        'content_rating_preference': random.choice(ratings),
        'diversity_preference': round(random.uniform(0.2, 0.9), 2),
        'novelty_preference': round(random.uniform(0.1, 0.8), 2),
        'allow_demographic_targeting': random.choice([True, False]),
        'data_usage_consent': random.choice([True, True, True, False]),  # 75% consent
        'onboarding_completed': True,
        'cold_start_preferences_collected': True
    }

def create_regular_users(count=50):
    """Create regular users with realistic names and movie preferences"""
    print(f'👥 Creating {count} regular users with realistic names...')
    
    created_count = 0
    used_combinations = set()
    
    for i in range(count):
        # Generate unique name combination
        attempts = 0
        while attempts < 100:  # Prevent infinite loop
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            name_combo = (first_name, last_name)
            
            if name_combo not in used_combinations:
                used_combinations.add(name_combo)
                break
            attempts += 1
        
        username = generate_username(first_name, last_name, i)
        email = f'{username}@example.com'
        
        try:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='demo123',
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Set movie preferences if fields exist
                preferences = get_sample_preferences(i)
                
                if hasattr(user, 'favorite_genres'):
                    user.favorite_genres = get_sample_genres(i)
                
                for field, value in preferences.items():
                    if hasattr(user, field):
                        setattr(user, field, value)
                
                user.save()
                created_count += 1
                
                # Print every 10th user for progress tracking
                if created_count % 10 == 0:
                    print(f'   ✓ Created {created_count} users...')
                    
        except IntegrityError as e:
            print(f'⚠️  User creation failed for {username}: {e}')
    
    print(f'✅ Created {created_count} regular users')
    return created_count

def display_sample_users():
    """Display a sample of created users"""
    print('\n📋 Sample of created users:')
    sample_users = User.objects.filter(is_superuser=False)[:5]
    
    for user in sample_users:
        genres = getattr(user, 'favorite_genres', [])
        algorithm = getattr(user, 'algorithm_preference', 'N/A')
        print(f'   • {user.first_name} {user.last_name} (@{user.username})')
        print(f'     Email: {user.email}')
        print(f'     Favorite genres: {", ".join(genres[:3])}{"..." if len(genres) > 3 else ""}')
        print(f'     Algorithm preference: {algorithm}')
        print()

def seed_database():
    """Main seeding function"""
    print('🌱 Starting database seeding with realistic users...')
    print('=' * 60)
    
    # Create superuser
    superuser = create_superuser()
    
    # Create 50 regular users
    users_created = create_regular_users(50)
    
    # Display sample users
    display_sample_users()
    
    print('=' * 60)
    print(f'✅ Database seeded successfully!')
    print(f'   - 1 superuser (admin access)')
    print(f'   - {users_created} regular users with realistic names')
    print(f'   - All users have movie preferences and genre selections')
    print(f'   - Default password for all users: "demo123"')
    print('=' * 60)

if __name__ == '__main__':
    seed_database()