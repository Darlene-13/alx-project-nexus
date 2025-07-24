# Movie Recommendation System - Database Design

**Project:** Movie Recommendation Backend  
**Technology Stack:** Django + PostgreSQL + Redis  
**Date:** December 2024  
**Author:** ALX ProDev Backend Engineering Program  

---

## **System Overview**

This database design supports an enterprise-level movie recommendation system with the following core features:
- User authentication and profiling
- Movie catalog with TMDb integration
- AI-powered recommendation engine
- Multi-channel notification system
- Comprehensive analytics tracking
- Real-time performance monitoring

**Total Tables:** 20  
**Database Engine:** PostgreSQL 13+  
**Caching Layer:** Redis 6+  

---

## **Database Schema**

### **1. Authentication App (2 Tables)**

#### **1.1 users (Django AbstractUser)**
Primary table for user authentication and basic information.

```sql
users {
    -- Django AbstractUser Fields
    id: bigint PRIMARY KEY
    password: varchar(128) NOT NULL
    last_login: timestamp NULL
    is_superuser: boolean DEFAULT false
    username: varchar(150) UNIQUE NOT NULL
    first_name: varchar(150) DEFAULT ''
    last_name: varchar(150) DEFAULT ''
    email: varchar(254) NOT NULL
    is_staff: boolean DEFAULT false
    is_active: boolean DEFAULT true
    date_joined: timestamp NOT NULL
    
    -- Custom Fields for Movie Recommendation
    date_of_birth: date NULL
    is_premium: boolean DEFAULT false
    phone_number: varchar(20) NULL
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
```

#### **1.2 user_profiles**
Extended user information and preferences.

```sql
user_profiles {
    id: bigint PRIMARY KEY
    user_id: bigint UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE
    bio: text DEFAULT ''
    avatar: varchar(200) NULL
    preferred_language: varchar(10) DEFAULT 'en'
    timezone: varchar(50) DEFAULT 'UTC'
    country: varchar(50) DEFAULT ''
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_user_profiles_user ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_country ON user_profiles(country);
```

---

### **2. Movies App (8 Tables)**

#### **2.1 genres**
Movie genres from TMDb API.

```sql
genres {
    id: bigint PRIMARY KEY
    tmdb_id: integer UNIQUE NOT NULL
    name: varchar(100) UNIQUE NOT NULL
    slug: varchar(50) UNIQUE NOT NULL
    created_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_genres_tmdb_id ON genres(tmdb_id);
CREATE INDEX idx_genres_slug ON genres(slug);
```

#### **2.2 movies**
Core movie information integrated from TMDb and OMDb APIs.

```sql
movies {
    id: bigint PRIMARY KEY
    tmdb_id: integer UNIQUE NOT NULL
    imdb_id: varchar(20) UNIQUE NULL
    title: varchar(200) NOT NULL
    original_title: varchar(200) NOT NULL
    overview: text DEFAULT ''
    tagline: varchar(300) DEFAULT ''
    release_date: date NULL
    runtime: integer NULL -- minutes
    budget: bigint NULL
    revenue: bigint NULL
    status: varchar(20) DEFAULT 'Released' -- 'Released', 'In Production', 'Post Production'
    
    -- Ratings
    tmdb_rating: decimal(3,1) NULL
    tmdb_vote_count: integer DEFAULT 0
    imdb_rating: decimal(3,1) NULL
    our_rating: decimal(3,1) NULL -- User-generated rating
    
    -- Media Assets
    poster_path: varchar(200) NULL
    backdrop_path: varchar(200) NULL
    
    -- Performance Metrics
    popularity_score: float DEFAULT 0.0
    view_count: integer DEFAULT 0
    like_count: integer DEFAULT 0
    
    -- Metadata
    adult: boolean DEFAULT false
    video: boolean DEFAULT false
    original_language: varchar(10) NOT NULL
    
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- Indexes for Performance
CREATE INDEX idx_movies_tmdb_id ON movies(tmdb_id);
CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movies_release_date ON movies(release_date DESC);
CREATE INDEX idx_movies_popularity ON movies(popularity_score DESC);
CREATE INDEX idx_movies_rating ON movies(tmdb_rating DESC);
CREATE INDEX idx_movies_status ON movies(status);
```

#### **2.3 movie_genres (Many-to-Many Junction)**
Relationship between movies and genres.

```sql
movie_genres {
    id: bigint PRIMARY KEY
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    genre_id: bigint NOT NULL REFERENCES genres(id) ON DELETE CASCADE
    
    CONSTRAINT unique_movie_genre UNIQUE(movie_id, genre_id)
}

-- Indexes
CREATE INDEX idx_movie_genres_movie ON movie_genres(movie_id);
CREATE INDEX idx_movie_genres_genre ON movie_genres(genre_id);
```

#### **2.4 user_favorite_genres (Many-to-Many Junction)**
User's favorite genres for personalization.

```sql
user_favorite_genres {
    id: bigint PRIMARY KEY
    userprofile_id: bigint NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE
    genre_id: bigint NOT NULL REFERENCES genres(id) ON DELETE CASCADE
    
    CONSTRAINT unique_user_favorite_genre UNIQUE(userprofile_id, genre_id)
}

-- Indexes
CREATE INDEX idx_user_fav_genres_profile ON user_favorite_genres(userprofile_id);
CREATE INDEX idx_user_fav_genres_genre ON user_favorite_genres(genre_id);
```

#### **2.5 persons**
Actors, directors, and other movie personnel.

```sql
persons {
    id: bigint PRIMARY KEY
    tmdb_id: integer UNIQUE NOT NULL
    name: varchar(200) NOT NULL
    biography: text DEFAULT ''
    birthday: date NULL
    deathday: date NULL
    place_of_birth: varchar(200) DEFAULT ''
    profile_path: varchar(200) NULL
    known_for_department: varchar(50) NOT NULL -- 'Acting', 'Directing', 'Writing'
    popularity: float DEFAULT 0.0
    created_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_persons_tmdb_id ON persons(tmdb_id);
CREATE INDEX idx_persons_name ON persons(name);
CREATE INDEX idx_persons_department ON persons(known_for_department);
```

#### **2.6 movie_cast**
Movie cast information (actors and their characters).

```sql
movie_cast {
    id: bigint PRIMARY KEY
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    person_id: bigint NOT NULL REFERENCES persons(id) ON DELETE CASCADE
    character: varchar(200) NOT NULL
    order: integer NOT NULL -- billing order
    created_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_movie_cast_movie ON movie_cast(movie_id);
CREATE INDEX idx_movie_cast_person ON movie_cast(person_id);
CREATE INDEX idx_movie_cast_order ON movie_cast(movie_id, order);
```

#### **2.7 movie_crew**
Movie crew information (directors, producers, etc.).

```sql
movie_crew {
    id: bigint PRIMARY KEY
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    person_id: bigint NOT NULL REFERENCES persons(id) ON DELETE CASCADE
    job: varchar(100) NOT NULL -- 'Director', 'Producer', 'Writer'
    department: varchar(50) NOT NULL -- 'Directing', 'Production', 'Writing'
    created_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_movie_crew_movie ON movie_crew(movie_id);
CREATE INDEX idx_movie_crew_person ON movie_crew(person_id);
CREATE INDEX idx_movie_crew_job ON movie_crew(job);
```

#### **2.8 production_companies**
Movie production companies.

```sql
production_companies {
    id: bigint PRIMARY KEY
    tmdb_id: integer UNIQUE NOT NULL
    name: varchar(200) NOT NULL
    logo_path: varchar(200) NULL
    origin_country: varchar(10) NOT NULL
    created_at: timestamp NOT NULL
}

-- Junction table for movie-production company relationship
movie_production_companies {
    id: bigint PRIMARY KEY
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    production_company_id: bigint NOT NULL REFERENCES production_companies(id) ON DELETE CASCADE
    
    CONSTRAINT unique_movie_company UNIQUE(movie_id, production_company_id)
}
```

---

### **3. Recommendations App (3 Tables)**

#### **3.1 user_movie_interactions**
Core table tracking all user interactions with movies.

```sql
user_movie_interactions {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    interaction_type: varchar(20) NOT NULL -- 'view', 'like', 'dislike', 'favorite', 'watchlist', 'rating', 'share'
    rating: integer NULL CHECK (rating BETWEEN 1 AND 5) -- 1-5 stars for rating interactions
    source: varchar(30) DEFAULT 'web' NOT NULL -- 'web', 'mobile', 'email', 'push'
    timestamp: timestamp NOT NULL
    
    CONSTRAINT unique_user_movie_interaction UNIQUE(user_id, movie_id, interaction_type)
}

-- High-Performance Indexes for ML Algorithms
CREATE INDEX idx_interactions_user_type ON user_movie_interactions(user_id, interaction_type);
CREATE INDEX idx_interactions_movie_type ON user_movie_interactions(movie_id, interaction_type);
CREATE INDEX idx_interactions_timestamp ON user_movie_interactions(timestamp DESC);
CREATE INDEX idx_interactions_rating ON user_movie_interactions(rating) WHERE rating IS NOT NULL;
```

#### **3.2 user_recommendations**
Generated recommendations for users.

```sql
user_recommendations {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    score: float NOT NULL CHECK (score BETWEEN 0.0 AND 1.0) -- recommendation confidence score
    algorithm: varchar(50) NOT NULL -- 'collaborative', 'content_based', 'hybrid', 'trending'
    generated_at: timestamp NOT NULL
    clicked: boolean DEFAULT false
    clicked_at: timestamp NULL
    
    CONSTRAINT unique_user_movie_algorithm UNIQUE(user_id, movie_id, algorithm)
}

-- Indexes for Recommendation Serving
CREATE INDEX idx_recommendations_user_score ON user_recommendations(user_id, score DESC);
CREATE INDEX idx_recommendations_generated ON user_recommendations(generated_at DESC);
CREATE INDEX idx_recommendations_algorithm ON user_recommendations(algorithm);
CREATE INDEX idx_recommendations_clicked ON user_recommendations(clicked, clicked_at);
```

#### **3.3 recommendation_feedback**
User feedback on recommendations for ML improvement.

```sql
recommendation_feedback {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    recommendation_id: bigint NOT NULL REFERENCES user_recommendations(id) ON DELETE CASCADE
    feedback_type: varchar(20) NOT NULL -- 'positive', 'negative', 'not_interested', 'already_seen'
    comment: text DEFAULT ''
    timestamp: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_feedback_user ON recommendation_feedback(user_id);
CREATE INDEX idx_feedback_recommendation ON recommendation_feedback(recommendation_id);
CREATE INDEX idx_feedback_type ON recommendation_feedback(feedback_type);
```

---

### **4. Notifications App (4 Tables)**

#### **4.1 notification_preferences**
User notification preferences for multi-channel communication.

```sql
notification_preferences {
    id: bigint PRIMARY KEY
    user_id: bigint UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE
    
    -- Email Preferences
    weekly_digest: boolean DEFAULT true
    recommendation_alerts: boolean DEFAULT true
    trending_alerts: boolean DEFAULT false
    new_release_alerts: boolean DEFAULT false
    
    -- Push Notification Preferences  
    push_recommendations: boolean DEFAULT true
    push_trending: boolean DEFAULT false
    push_new_releases: boolean DEFAULT false
    
    -- Timing Preferences
    digest_day: integer DEFAULT 1 CHECK (digest_day BETWEEN 1 AND 7) -- 1=Monday, 7=Sunday
    digest_time: time DEFAULT '09:00:00'
    timezone: varchar(50) DEFAULT 'UTC'
    
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_notification_prefs_user ON notification_preferences(user_id);
CREATE INDEX idx_notification_prefs_digest ON notification_preferences(digest_day, digest_time);
```

#### **4.2 notification_templates**
Email and push notification templates.

```sql
notification_templates {
    id: bigint PRIMARY KEY
    name: varchar(100) UNIQUE NOT NULL
    template_type: varchar(30) NOT NULL -- 'email_weekly_digest', 'email_recommendation', 'push_trending', 'push_recommendation'
    subject: varchar(200) NOT NULL -- For emails
    html_content: text NOT NULL -- Email HTML template
    text_content: text NOT NULL -- Email text/Push notification content
    is_active: boolean DEFAULT true
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_templates_type ON notification_templates(template_type);
CREATE INDEX idx_templates_active ON notification_templates(is_active);
```

#### **4.3 notification_logs**
Comprehensive notification delivery tracking.

```sql
notification_logs {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    template_id: bigint NULL REFERENCES notification_templates(id) ON DELETE SET NULL
    notification_type: varchar(30) NOT NULL -- 'email', 'push'
    subject: varchar(200) NOT NULL
    content: text NOT NULL
    recipient: varchar(200) NOT NULL -- email address or device token
    status: varchar(20) DEFAULT 'pending' -- 'pending', 'sent', 'delivered', 'failed', 'opened', 'clicked'
    external_id: varchar(100) NULL -- SendGrid/Firebase message ID
    error_message: text DEFAULT ''
    
    -- Delivery Tracking Timestamps
    sent_at: timestamp NULL
    delivered_at: timestamp NULL
    opened_at: timestamp NULL
    clicked_at: timestamp NULL
    created_at: timestamp NOT NULL
}

-- Indexes for Notification Analytics
CREATE INDEX idx_notification_logs_user ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_status ON notification_logs(status);
CREATE INDEX idx_notification_logs_type ON notification_logs(notification_type);
CREATE INDEX idx_notification_logs_created ON notification_logs(created_at DESC);
```

#### **4.4 user_devices**
User devices for push notifications.

```sql
user_devices {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    device_token: varchar(500) UNIQUE NOT NULL
    device_type: varchar(20) NOT NULL -- 'ios', 'android', 'web'
    device_name: varchar(100) DEFAULT ''
    is_active: boolean DEFAULT true
    registered_at: timestamp NOT NULL
    last_used_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_user_devices_user ON user_devices(user_id);
CREATE INDEX idx_user_devices_active ON user_devices(is_active);
CREATE INDEX idx_user_devices_type ON user_devices(device_type);
```

---

### **5. Analytics App (3 Tables)**

#### **5.1 user_activity_logs**
Comprehensive user behavior tracking for analytics and ML.

```sql
user_activity_logs {
    id: bigint PRIMARY KEY
    user_id: bigint NULL REFERENCES users(id) ON DELETE SET NULL -- Can track anonymous users
    session_id: varchar(100) NOT NULL
    action_type: varchar(30) NOT NULL -- 'movie_view', 'movie_search', 'recommendation_click', 'email_open', 'email_click', 'push_click', 'rating_submit', 'review_submit', 'favorite_add', 'watchlist_add'
    movie_id: bigint NULL REFERENCES movies(id) ON DELETE SET NULL
    
    -- Request Metadata
    ip_address: inet NOT NULL
    user_agent: text NOT NULL
    referer: varchar(500) NULL
    source: varchar(30) NOT NULL -- 'web', 'mobile', 'email', 'push'
    
    -- Flexible Additional Data (JSON for extensibility)
    metadata: jsonb DEFAULT '{}'
    timestamp: timestamp NOT NULL
}

-- High-Performance Indexes for Analytics Queries
CREATE INDEX idx_activity_logs_user_action ON user_activity_logs(user_id, action_type);
CREATE INDEX idx_activity_logs_timestamp ON user_activity_logs(timestamp DESC);
CREATE INDEX idx_activity_logs_movie_action ON user_activity_logs(movie_id, action_type);
CREATE INDEX idx_activity_logs_session ON user_activity_logs(session_id);
CREATE INDEX idx_activity_logs_source ON user_activity_logs(source);

-- GIN index for JSON metadata queries
CREATE INDEX idx_activity_logs_metadata ON user_activity_logs USING GIN (metadata);
```

#### **5.2 performance_metrics**
System performance monitoring and optimization data.

```sql
performance_metrics {
    id: bigint PRIMARY KEY
    metric_name: varchar(100) NOT NULL
    metric_value: float NOT NULL
    metric_unit: varchar(20) NOT NULL -- 'ms', 'seconds', 'count', 'percentage', 'bytes'
    endpoint: varchar(200) NULL -- API endpoint if applicable
    user_id: bigint NULL REFERENCES users(id) ON DELETE SET NULL
    additional_data: jsonb DEFAULT '{}'
    timestamp: timestamp NOT NULL
}

-- Indexes for Performance Analysis
CREATE INDEX idx_performance_metrics_name_time ON performance_metrics(metric_name, timestamp DESC);
CREATE INDEX idx_performance_metrics_endpoint_time ON performance_metrics(endpoint, timestamp DESC);
CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp DESC);
```

#### **5.3 popularity_metrics**
Daily aggregated movie popularity metrics.

```sql
popularity_metrics {
    id: bigint PRIMARY KEY
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    date: date NOT NULL
    
    -- Daily Aggregated Metrics
    view_count: integer DEFAULT 0
    like_count: integer DEFAULT 0
    rating_count: integer DEFAULT 0
    avg_rating: decimal(3,2) NULL
    recommendation_count: integer DEFAULT 0 -- Times recommended to users
    click_through_rate: decimal(5,4) DEFAULT 0.0000 -- CTR for recommendations
    
    CONSTRAINT unique_movie_date UNIQUE(movie_id, date)
}

-- Indexes for Trending Analysis
CREATE INDEX idx_popularity_metrics_movie ON popularity_metrics(movie_id);
CREATE INDEX idx_popularity_metrics_date ON popularity_metrics(date DESC);
CREATE INDEX idx_popularity_metrics_views ON popularity_metrics(view_count DESC);
CREATE INDEX idx_popularity_metrics_ctr ON popularity_metrics(click_through_rate DESC);
```

---

## 🔗 **Key Relationships & Constraints**

### **Primary Relationships**
```sql
-- One-to-One Relationships
users.id ←→ user_profiles.user_id
users.id ←→ notification_preferences.user_id

-- One-to-Many Relationships  
users.id → user_movie_interactions.user_id
users.id → user_recommendations.user_id
users.id → notification_logs.user_id
users.id → user_devices.user_id
users.id → user_activity_logs.user_id

movies.id → user_movie_interactions.movie_id
movies.id → user_recommendations.movie_id
movies.id → movie_cast.movie_id
movies.id → movie_crew.movie_id
movies.id → popularity_metrics.movie_id

-- Many-to-Many Relationships (via Junction Tables)
users ←→ genres (via user_profiles → user_favorite_genres)
movies ←→ genres (via movie_genres)
movies ←→ persons (via movie_cast and movie_crew)
movies ←→ production_companies (via movie_production_companies)
```

### **Referential Integrity Constraints**
```sql
-- Cascade Deletes for Dependent Data
ALTER TABLE user_profiles ADD CONSTRAINT fk_user_profiles_user 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_movie_interactions ADD CONSTRAINT fk_interactions_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Set NULL for Optional References
ALTER TABLE user_activity_logs ADD CONSTRAINT fk_activity_logs_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- Check Constraints for Data Validation
ALTER TABLE user_movie_interactions ADD CONSTRAINT check_rating_range
    CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5));

ALTER TABLE user_recommendations ADD CONSTRAINT check_score_range
    CHECK (score >= 0.0 AND score <= 1.0);
```

---

## **Performance Optimization Strategy**

### **Database Indexes Strategy**
```sql
-- Composite Indexes for Common Query Patterns
CREATE INDEX idx_interactions_user_movie_type ON user_movie_interactions(user_id, movie_id, interaction_type);
CREATE INDEX idx_recommendations_user_score_generated ON user_recommendations(user_id, score DESC, generated_at DESC);
CREATE INDEX idx_movies_rating_popularity ON movies(tmdb_rating DESC, popularity_score DESC);

-- Partial Indexes for Filtered Queries
CREATE INDEX idx_movies_active ON movies(id) WHERE is_active = true;
CREATE INDEX idx_notifications_pending ON notification_logs(id) WHERE status = 'pending';

-- Text Search Indexes
CREATE INDEX idx_movies_title_search ON movies USING GIN (to_tsvector('english', title));
CREATE INDEX idx_persons_name_search ON persons USING GIN (to_tsvector('english', name));
```

### **Partitioning Strategy**
```sql
-- Partition large tables by date for better performance
-- user_activity_logs partitioned by month
CREATE TABLE user_activity_logs_y2024m12 PARTITION OF user_activity_logs
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- notification_logs partitioned by quarter
CREATE TABLE notification_logs_2024q4 PARTITION OF notification_logs
    FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');
```

---

## **Security & Data Privacy**

### **Data Protection Measures**
```sql
-- Sensitive Data Encryption (handled at application level)
-- Email addresses, phone numbers, IP addresses should be encrypted

-- Row Level Security for Multi-tenancy
ALTER TABLE user_movie_interactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_interactions_policy ON user_movie_interactions
    FOR ALL TO authenticated_users
    USING (user_id = current_user_id());

-- Audit Trail (optional)
CREATE TABLE audit_log (
    id: bigint PRIMARY KEY,
    table_name: varchar(50),
    operation: varchar(10), -- INSERT, UPDATE, DELETE
    old_values: jsonb,
    new_values: jsonb,
    user_id: bigint,
    timestamp: timestamp
);
```

---

## **Data Volume Estimates**

### **Expected Growth (1 Year)**
```
users:                    100,000 records      (~50 MB)
user_profiles:            100,000 records      (~30 MB)
movies:                   50,000 records       (~200 MB)
genres:                   50 records           (~1 KB)
user_movie_interactions:  10,000,000 records   (~2 GB)
user_recommendations:     5,000,000 records    (~1 GB)
notification_logs:        2,000,000 records    (~500 MB)
user_activity_logs:       50,000,000 records   (~10 GB)

Total Estimated Size:     ~14 GB (without indexes)
With Indexes:             ~20 GB
```

### **Scaling Considerations**
- **Read Replicas** for heavy analytical queries
- **Connection Pooling** (PgBouncer) for high concurrency
- **Materialized Views** for complex aggregations
- **Redis Caching** for frequently accessed data
- **Archive Strategy** for old logs (> 1 year)

---

## **Migration Strategy**

### **Phase 1: Core Tables (Day 1-2)**
```sql
-- Create base tables
users, user_profiles, genres, movies, movie_genres
```

### **Phase 2: Interaction Tables (Day 3-4)**
```sql
-- Add recommendation engine tables
user_movie_interactions, user_recommendations, recommendation_feedback
```

### **Phase 3: Feature Tables (Day 5-8)**
```sql
-- Add advanced features
notification_preferences, notification_templates, notification_logs
user_devices, user_activity_logs, performance_metrics
```

### **Phase 4: Optimization (Day 9-10)**
```sql
-- Add indexes, constraints, and performance optimizations
-- Populate initial data from fixtures
```

---

## **Notes & Assumptions**

1. **Django AbstractUser** is used instead of extending User model
2. **PostgreSQL JSONB** is used for flexible metadata storage
3. **Timezone handling** is done at application level
4. **File uploads** (avatars, posters) are stored in cloud storage (URLs in DB)
5. **API rate limiting** is handled at application level
6. **Soft deletes** may be implemented for critical data
7. **Database backups** should be automated (daily + transaction log)

---
 
**Version:** 1.0  
**Status:** Final Design Ready for Implementation