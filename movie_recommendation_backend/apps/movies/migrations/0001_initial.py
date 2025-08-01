# Generated by Django 5.2.4 on 2025-07-30 11:14

import apps.movies.models
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Movie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tmdb_id', models.PositiveIntegerField(help_text='The unique ID of the movie from TMDB', unique=True, verbose_name='TMDB ID')),
                ('omdb_id', models.CharField(blank=True, help_text='The unique ID of the movie from OMDB', max_length=20, null=True, unique=True, verbose_name='OMDB ID')),
                ('title', models.CharField(help_text='The title of the movie', max_length=255, verbose_name='Movie Title')),
                ('original_title', models.CharField(help_text='The original title of the movie', max_length=255, verbose_name='Original Title')),
                ('tagline', models.CharField(blank=True, help_text='A tagline for the movie', max_length=255, verbose_name='Tagline')),
                ('overview', models.TextField(blank=True, help_text='A brief overview of the movie', verbose_name='Overview')),
                ('release_date', models.DateField(blank=True, help_text='The release date of the movie', null=True, verbose_name='Release Date')),
                ('runtime', models.PositiveIntegerField(blank=True, help_text='The runtime of the movie in minutes', null=True, verbose_name='Runtime')),
                ('director', models.CharField(blank=True, help_text='The director of the movie', max_length=255, verbose_name='Director')),
                ('main_cast', models.JSONField(default=list, help_text='List of main cast members', validators=[apps.movies.models.validate_json_array], verbose_name='Main Cast')),
                ('tmdb_rating', models.DecimalField(blank=True, decimal_places=1, help_text='The TMDB rating of the movie', max_digits=3, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)], verbose_name='TMDB Rating')),
                ('tmdb_vote_count', models.PositiveIntegerField(default=0, help_text='The number of votes for the TMDB rating', verbose_name='TMDB Vote Count')),
                ('omdb_rating', models.DecimalField(blank=True, decimal_places=1, help_text='The OMDB rating of the movie', max_digits=3, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)], verbose_name='OMDB Rating')),
                ('our_rating', models.DecimalField(blank=True, decimal_places=1, help_text='User-generated average rating of the movie', max_digits=3, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)], verbose_name='Our Rating')),
                ('poster_path', models.CharField(blank=True, help_text='Path to the movie poster image', max_length=255, verbose_name='Poster Path')),
                ('backdrop_path', models.CharField(blank=True, help_text='Path to the movie backdrop image', max_length=255, verbose_name='Backdrop Path')),
                ('popularity_score', models.DecimalField(decimal_places=2, default=0.0, help_text='The popularity score of the movie', max_digits=10, verbose_name='Popularity')),
                ('views', models.PositiveIntegerField(default=0, help_text='The number of views for the movie', verbose_name='Views')),
                ('like_count', models.PositiveIntegerField(default=0, help_text='The number of likes for the movie', verbose_name='Like Count')),
                ('adult', models.BooleanField(default=False, help_text='Indicates if the movie contains adult content', verbose_name='Adult Content')),
                ('original_language', models.CharField(blank=True, help_text='The original language of the movie', max_length=10, verbose_name='Original Language')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='The timestamp when the movie was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='The timestamp when the movie was last updated', verbose_name='Updated At')),
            ],
            options={
                'verbose_name': 'Movie',
                'verbose_name_plural': 'Movies',
                'db_table': 'movies',
                'ordering': ['-release_date', '-popularity_score'],
            },
        ),
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tmdb_id', models.PositiveIntegerField(help_text='The unique ID of the genre from TMDB', unique=True, verbose_name='TMDB ID')),
                ('name', models.CharField(help_text='The name of the genre', max_length=100, unique=True, verbose_name='Genre Name')),
                ('slug', models.SlugField(blank=True, editable=False, help_text='A URL-friendly version of the genre name', max_length=100, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='The timestamp when the genre was created', verbose_name='Created At')),
            ],
            options={
                'verbose_name': 'Genre',
                'verbose_name_plural': 'Genres',
                'db_table': 'genres',
                'ordering': ['name'],
                'indexes': [models.Index(fields=['tmdb_id'], name='idx_genres_tmdb_id'), models.Index(fields=['slug'], name='idx_genres_slug'), models.Index(fields=['name'], name='idx_genres_name')],
            },
        ),
        migrations.CreateModel(
            name='MovieGenre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('genre', models.ForeignKey(help_text='Genre in this relationship', on_delete=django.db.models.deletion.CASCADE, related_name='movie_genres', to='movies.genre')),
                ('movie', models.ForeignKey(help_text='Movie in this relationship', on_delete=django.db.models.deletion.CASCADE, related_name='movie_genres', to='movies.movie')),
            ],
            options={
                'verbose_name': 'Movie Genre',
                'verbose_name_plural': 'Movie Genres',
                'db_table': 'movie_genres',
            },
        ),
        migrations.AddField(
            model_name='movie',
            name='genres',
            field=models.ManyToManyField(blank=True, help_text='The genres associated with the movie', related_name='movies', through='movies.MovieGenre', to='movies.genre', verbose_name='Genres'),
        ),
        migrations.AddIndex(
            model_name='moviegenre',
            index=models.Index(fields=['movie'], name='idx_movie_genre_movie'),
        ),
        migrations.AddIndex(
            model_name='moviegenre',
            index=models.Index(fields=['genre'], name='idx_movie_genre_genre'),
        ),
        migrations.AddConstraint(
            model_name='moviegenre',
            constraint=models.UniqueConstraint(fields=('movie', 'genre'), name='unique_movie_genre'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['tmdb_id'], name='idx_movies_tmdb_id'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['title'], name='idx_movies_title'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['release_date'], name='idx_movies_release_date'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['popularity_score'], name='idx_movies_popularity_score'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['tmdb_rating'], name='idx_movies_tmdb_rating'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['omdb_rating'], name='idx_movies_omdb_rating'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['original_language'], name='idx_movies_original_language'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['adult'], name='idx_movies_adult'),
        ),
        migrations.AddIndex(
            model_name='movie',
            index=models.Index(fields=['created_at'], name='idx_movies_created_at'),
        ),
    ]
