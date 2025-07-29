import os
import django
import random
import string
import sys
from django.utils import timezone

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recommendation_backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def generate_random_username(length=8):
    return 'user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_random_email(username):
    return f"{username}@example.com"


def create_superuser():
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        print("[+] Superuser created: admin / adminpass123")
    else:
        print("[!] Superuser already exists. Skipping...")


def create_test_users(count=100):
    for _ in range(count):
        username = generate_random_username()
        email = generate_random_email(username)
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(
                username=username,
                email=email,
                password="testpass123",
                date_joined=timezone.now()
            )
            print(f"[+] Created user: {username}")
        else:
            print(f"[!] Skipped existing user: {username}")


if __name__ == "__main__":
    print("Seeding users into the database...")
    create_superuser()
    create_test_users()
    print("Seeding complete.")
