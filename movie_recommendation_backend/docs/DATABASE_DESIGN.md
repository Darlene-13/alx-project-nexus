# Movie Recommendation System - Final Database Design

**Project:** Movie Recommendation Backend (Enterprise-Level)  
**Technology Stack:** Django 5.0+ + PostgreSQL 14+ + Redis 6+  
**Date:** August 2025  
**Author:** ALX ProDev Backend Engineering Program  
**Development Status:** Production Ready  

---

## 🎯 **Design Philosophy**

This comprehensive database design balances **enterprise functionality** with **development efficiency**. Built for production-scale movie recommendation systems with ML capabilities, A/B testing, multi-channel notifications, and comprehensive analytics.

**Total Tables:** 12  
**Database Engine:** PostgreSQL 14+  
**Caching Layer:** Redis 6+  
**Architecture:** Microservices-ready with proper domain separation

---

## 📊 **Table Distribution by App**

| App | Tables | Core Purpose |
|-----|--------|--------------|
| **Authentication** | 1 | Extended user management with preferences |
| **Movies** | 3 | Movie catalog with genre relationships |
| **Recommendations** | 3 | ML-powered recommendation engine with A/B testing |
| **Notifications** | 3 | Multi-channel communication system |
| **Analytics** | 2 | User behavior tracking & popularity metrics |
| **Total** | **12** | Complete enterprise system |

---

## 🗄️ **Complete Database Schema**

### **1. Authentication App (1 Table)**

#### **1.1 users**
Extended Django AbstractUser with recommendation preferences and device management.

```sql
users {
    -- Django AbstractUser Fields
    id: bigint PRIMARY KEY
    password: varchar(128) NOT NULL
    last_login: timestamp NULL
    is_superuser: boolean DEFAULT false
    username: varchar(150) UNIQUE NOT NULL
    first_name: varchar(30) DEFAULT ''
    last_name: varchar(30) DEFAULT ''
    email: varchar(254) UNIQUE NOT NULL
    is_staff: boolean DEFAULT false
    is_active: boolean DEFAULT true
    date_joined: timestamp NOT NULL
    
    -- Extended Profile Fields
    date_of_birth: date NULL
    is_premium: boolean DEFAULT false
    phone_number: varchar(20) NOT NULL
    bio: text DEFAULT ''
    avatar: varchar(200) NULL
    country: varchar(100) DEFAULT ''
    preferred_timezone: varchar(50) DEFAULT 'GMT+3'
    preferred_language: varchar(50) DEFAULT 'en' -- en, es, fr, de, zh, ja, ru, it, pt, hi, ar, ko
    
    -- Device Information for Push Notifications
    device_token: varchar(255) UNIQUE NULL
    device_type: varchar(50) NULL -- android, ios, web
    
    -- Recommendation Preferences (JSONField)
    favorite_genres: jsonb DEFAULT '[]' -- Array of genre objects
    algorithm_preference: varchar(50) NULL
    diversity_preference: float DEFAULT 0.5 CHECK (diversity_preference BETWEEN 0.0 AND 1.0)
    novelty_preference: float DEFAULT 0.5 CHECK (novelty_preference BETWEEN 0.0 AND 1.0)
    content_rating_preference: varchar(10) NULL
    preferred_decade: varchar(10) NULL
    
    -- Onboarding & Privacy
    onboarding_completed: boolean DEFAULT false
    onboarding_completed_at: timestamp NULL
    cold_start_preferences_collected: boolean DEFAULT false
    allow_demographic_targeting: boolean DEFAULT true
    data_usage_consent: boolean DEFAULT false
    
    -- Timestamps
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- Performance Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_device_token ON users(device_token) WHERE device_token IS NOT NULL;
CREATE INDEX idx_users_country ON users(country);
CREATE INDEX idx_users_created_at ON users(created_at);
```

---

### **2. Movies App (3 Tables)**

#### **2.1 genres**
Movie genres from TMDB API with SEO optimization.

```sql
genres {
    id: bigint PRIMARY KEY
    tmdb_id: integer UNIQUE NOT NULL
    name: varchar(100) UNIQUE NOT NULL
    slug: varchar(100) UNIQUE NOT NULL
    created_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_genres_tmdb_id ON genres(tmdb_id);
CREATE INDEX idx_genres_slug ON genres(slug);
CREATE INDEX idx_genres_name ON genres(name);
```

#### **2.2 movies**
Comprehensive movie information with TMDB/OMDB integration.

```sql
movies {
    id: bigint PRIMARY KEY
    
    -- External API IDs
    tmdb_id: integer UNIQUE NOT NULL
    omdb_id: varchar(20) UNIQUE NULL
    
    -- Basic Information
    title: varchar(255) NOT NULL
    original_title: varchar(255) NOT NULL
    tagline: varchar(255) DEFAULT ''
    overview: text DEFAULT ''
    release_date: date NULL
    runtime: integer NULL -- minutes
    
    -- Cast & Crew (Simplified JSON)
    director: varchar(255) NULL
    main_cast: jsonb DEFAULT '[]' -- JSON array of actor names
    
    -- Ratings System
    tmdb_rating: float NULL CHECK (tmdb_rating BETWEEN 0.0 AND 10.0)
    tmdb_vote_count: integer DEFAULT 0
    omdb_rating: float NULL CHECK (omdb_rating BETWEEN 0.0 AND 10.0)
    our_rating: float NULL CHECK (our_rating BETWEEN 0.0 AND 10.0) -- User-generated
    
    -- Media Assets
    poster_path: varchar(255) DEFAULT ''
    backdrop_path: varchar(255) DEFAULT ''
    
    -- Performance Metrics
    popularity_score: float DEFAULT 0.0
    views: integer DEFAULT 0
    like_count: integer DEFAULT 0
    
    -- Metadata
    adult: boolean DEFAULT false
    original_language: varchar(10) DEFAULT ''
    
    -- Timestamps
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- High-Performance Indexes
CREATE INDEX idx_movies_tmdb_id ON movies(tmdb_id);
CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movies_release_date ON movies(release_date DESC);
CREATE INDEX idx_movies_popularity_score ON movies(popularity_score DESC);
CREATE INDEX idx_movies_tmdb_rating ON movies(tmdb_rating DESC);
CREATE INDEX idx_movies_omdb_rating ON movies(omdb_rating DESC);
CREATE INDEX idx_movies_original_language ON movies(original_language);
CREATE INDEX idx_movies_adult ON movies(adult);
CREATE INDEX idx_movies_created_at ON movies(created_at);

-- Full-text search
CREATE INDEX idx_movies_search ON movies USING GIN (to_tsvector('english', title || ' ' || overview));
```

#### **2.3 movie_genres**
Many-to-many relationship for movie-genre associations.

```sql
movie_genres {
    id: bigint PRIMARY KEY
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    genre_id: bigint NOT NULL REFERENCES genres(id) ON DELETE CASCADE
    
    CONSTRAINT unique_movie_genre UNIQUE(movie_id, genre_id)
}

-- Indexes
CREATE INDEX idx_movie_genre_movie ON movie_genres(movie_id);
CREATE INDEX idx_movie_genre_genre ON movie_genres(genre_id);
```

---

### **3. Recommendations App (3 Tables)**

#### **3.1 user_movie_interactions**
Comprehensive user-movie interaction tracking with integrated feedback system.

```sql
user_movie_interactions {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    
    -- Interaction Details
    interaction_type: varchar(50) NULL -- view, like, dislike, click, rating, favorite, watchlist
    rating: float NULL CHECK (rating BETWEEN 1.0 AND 5.0)
    
    -- Integrated Feedback System
    feedback_type: varchar(50) NULL -- positive, negative, neutral
    feedback_comment: text NULL
    
    -- Metadata
    metadata: jsonb NULL
    source: varchar(50) NULL -- web, mobile, email, push
    
    -- Timestamp
    timestamp: timestamp DEFAULT CURRENT_TIMESTAMP
    
    CONSTRAINT unique_user_movie_interaction UNIQUE(user_id, movie_id, interaction_type)
}

-- ML-Optimized Indexes
CREATE INDEX idx_interactions_user_type ON user_movie_interactions(user_id, interaction_type);
CREATE INDEX idx_interactions_movie_type ON user_movie_interactions(movie_id, interaction_type);
CREATE INDEX idx_interactions_timestamp ON user_movie_interactions(timestamp DESC);
CREATE INDEX idx_interactions_rating ON user_movie_interactions(rating) WHERE rating IS NOT NULL;
CREATE INDEX idx_interactions_feedback ON user_movie_interactions(feedback_type) WHERE feedback_type IS NOT NULL;
```

#### **3.2 user_recommendations**
ML-generated personalized movie recommendations.

```sql
user_recommendations {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    
    -- Recommendation Details
    score: float NOT NULL CHECK (score >= 0.0)
    algorithm: varchar(50) NOT NULL -- collaborative, content_based, hybrid, trending, etc.
    
    -- Tracking
    generated_at: timestamp NOT NULL
    clicked: boolean DEFAULT false
    clicked_at: timestamp NULL
    
    CONSTRAINT unique_user_movie_algorithm UNIQUE(user_id, movie_id, algorithm)
}

-- Recommendation Serving Indexes
CREATE INDEX idx_recommendations_user_score ON user_recommendations(user_id, score DESC);
CREATE INDEX idx_recommendations_generated ON user_recommendations(generated_at DESC);
CREATE INDEX idx_recommendations_algorithm ON user_recommendations(algorithm);
CREATE INDEX idx_recommendations_clicked ON user_recommendations(clicked, clicked_at);
```

#### **3.3 recommendation_experiments**
A/B testing framework for algorithm comparison and optimization.

```sql
recommendation_experiments {
    id: bigint PRIMARY KEY
    
    -- Experiment Configuration
    name: varchar(100) UNIQUE NOT NULL
    description: text NULL
    
    -- Algorithm Variants
    algorithm_a: varchar(50) NOT NULL -- collaborative, content_based, hybrid, trending, demographic, matrix_factorization
    algorithm_b: varchar(50) NOT NULL
    
    -- Test Configuration
    traffic_split: float DEFAULT 0.5 CHECK (traffic_split BETWEEN 0.1 AND 0.9)
    start_date: timestamp NOT NULL
    end_date: timestamp NOT NULL
    is_active: boolean DEFAULT true
    
    -- Success Metrics Configuration
    target_metric: varchar(50) NOT NULL -- ctr, engagement, retention, conversion, rating, time_spent
    minimum_sample_size: integer DEFAULT 1000
    confidence_level: float DEFAULT 0.95 CHECK (confidence_level BETWEEN 0.8 AND 0.99)
    
    -- Statistical Results (Updated by Analytics)
    statistical_significance: float NULL
    winner_algorithm: varchar(50) NULL
    p_value: float NULL
    effect_size: float NULL
    
    -- Metadata
    created_by: bigint NULL REFERENCES users(id) ON DELETE SET NULL
    created_at: timestamp DEFAULT CURRENT_TIMESTAMP
    updated_at: timestamp DEFAULT CURRENT_TIMESTAMP
}

-- A/B Testing Indexes
CREATE INDEX idx_experiments_active ON recommendation_experiments(is_active, start_date, end_date);
CREATE INDEX idx_experiments_date_range ON recommendation_experiments(start_date, end_date);
CREATE INDEX idx_experiments_target_metric ON recommendation_experiments(target_metric);
CREATE INDEX idx_experiments_algorithms ON recommendation_experiments(algorithm_a, algorithm_b);
```

---

### **4. Notifications App (3 Tables)**

#### **4.1 notifications_preferences**
Comprehensive user notification preferences for all channels.

```sql
notifications_preferences {
    id: bigint PRIMARY KEY
    user_id: bigint UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE
    
    -- Email Notification Preferences
    weekly_digest: boolean DEFAULT false
    recommendation_alerts: boolean DEFAULT false
    trending_alerts: boolean DEFAULT false
    
    -- Push Notification Preferences
    push_recommendations: boolean DEFAULT false
    push_trending: boolean DEFAULT false
    
    -- In-App Notification Preferences
    in_app_recommendations: boolean DEFAULT false
    in_app_system_updates: boolean DEFAULT false
    
    -- Timing Preferences
    digest_day: integer DEFAULT 0 CHECK (digest_day BETWEEN 0 AND 6) -- 0=Monday, 6=Sunday
    digest_time: time DEFAULT '09:00:00'
    timezone: varchar(50) DEFAULT 'UTC'
    
    -- Timestamps
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- Indexes
CREATE INDEX idx_notifprefs_user ON notifications_preferences(user_id);
CREATE INDEX idx_notifprefs_digest ON notifications_preferences(digest_day, digest_time);
```

#### **4.2 notification_logs**
Comprehensive notification delivery tracking and analytics.

```sql
notification_logs {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    
    -- Notification Details
    notification_type: varchar(50) NOT NULL
    subject: varchar(255) NOT NULL
    content: text NOT NULL
    recipient: varchar(255) NOT NULL -- Email address or device token
    
    -- Status Tracking
    status: varchar(50) DEFAULT 'sent' -- sent, failed, clicked, opened, delivered, scheduled
    external_id: varchar(255) UNIQUE NULL
    
    -- Delivery Timestamps
    sent_at: timestamp NOT NULL
    delivered_at: timestamp NULL
    opened_at: timestamp NULL
    clicked_at: timestamp NULL
    created_at: timestamp NOT NULL
}

-- Analytics Indexes
CREATE INDEX idx_notif_log_user_type ON notification_logs(user_id, notification_type);
CREATE INDEX idx_notif_log_status ON notification_logs(status);
CREATE INDEX idx_notif_log_type_sent ON notification_logs(notification_type, sent_at);
CREATE INDEX idx_notif_log_created_at ON notification_logs(created_at DESC);
```

#### **4.3 in_app_notifications**
Rich in-app notifications with actions and expiration.

```sql
in_app_notifications {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    
    -- Notification Content
    category: varchar(50) DEFAULT 'system' -- recommendation, system, social, promotion, announcement
    title: varchar(255) NULL
    message: text NULL
    
    -- Action System
    action_url: varchar(200) NULL
    action_data: jsonb NULL
    
    -- Status
    is_read: boolean DEFAULT false
    is_archived: boolean DEFAULT false
    
    -- Timestamps
    created_at: timestamp NOT NULL
    read_at: timestamp NOT NULL
    expires_at: timestamp NULL
}

-- Performance Indexes
CREATE INDEX idx_in_app_user_created ON in_app_notifications(user_id, created_at DESC);
CREATE INDEX idx_in_app_user_read ON in_app_notifications(user_id, is_read);
CREATE INDEX idx_in_app_expires ON in_app_notifications(expires_at);
```

---

### **5. Analytics App (2 Tables)**

#### **5.1 user_activity_logs**
Comprehensive user behavior tracking for ML and analytics.

```sql
user_activity_logs {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    
    -- Activity Details
    session_id: varchar(255) NULL
    action_type: varchar(50) NULL -- movie_view, movie_search, recommendation_click, email_open, email_click, push_click, rating_submit, favorite_add, watchlist_add
    movie_id: bigint NULL REFERENCES movies(id) ON DELETE CASCADE
    
    -- Request Metadata
    ip_address: inet NULL
    user_agent: text NULL
    referer: varchar(255) NULL
    source: varchar(50) NULL
    metadata: jsonb NULL
    
    -- Timestamp
    timestamp: timestamp NOT NULL
}

-- Analytics-Optimized Indexes
CREATE INDEX idx_activity_logs_user_action ON user_activity_logs(user_id, action_type);
CREATE INDEX idx_activity_logs_movie_action ON user_activity_logs(movie_id, action_type);
CREATE INDEX idx_activity_logs_timestamp ON user_activity_logs(timestamp DESC);
CREATE INDEX idx_activity_logs_session ON user_activity_logs(session_id);
CREATE INDEX idx_activity_logs_source ON user_activity_logs(source);
```

#### **5.2 popularity_metrics**
Daily aggregated movie popularity and performance metrics.

```sql
popularity_metrics {
    id: bigint PRIMARY KEY
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    
    -- Metric Date
    date: date NOT NULL
    
    -- Daily Aggregated Metrics
    view_count: integer DEFAULT 0
    like_count: integer DEFAULT 0
    rating_count: integer DEFAULT 0
    average_rating: float DEFAULT 0.0
    recommendation_count: integer DEFAULT 0
    click_through_rate: decimal(5,2) DEFAULT 0.0
    
    CONSTRAINT unique_popularity_metrics_per_movie_per_day UNIQUE(movie_id, date)
}

-- Trending Analysis Indexes
CREATE INDEX idx_popularity_movie ON popularity_metrics(movie_id);
CREATE INDEX idx_popularity_views ON popularity_metrics(view_count DESC);
CREATE INDEX idx_popularity_date ON popularity_metrics(date DESC);
CREATE INDEX idx_popularity_ctr ON popularity_metrics(click_through_rate DESC);
```

---

## 🔗 **Relationships & Constraints**

### **Primary Relationships**
```sql
-- One-to-One Relationships
users.id ←→ notifications_preferences.user_id

-- One-to-Many Relationships
users.id → user_movie_interactions.user_id (CASCADE)
users.id → user_recommendations.user_id (CASCADE)
users.id → notification_logs.user_id (CASCADE)
users.id → in_app_notifications.user_id (CASCADE)
users.id → user_activity_logs.user_id (CASCADE)
users.id → recommendation_experiments.created_by (SET NULL)

movies.id → user_movie_interactions.movie_id (CASCADE)
movies.id → user_recommendations.movie_id (CASCADE)
movies.id → movie_genres.movie_id (CASCADE)
movies.id → user_activity_logs.movie_id (CASCADE)
movies.id → popularity_metrics.movie_id (CASCADE)

genres.id → movie_genres.genre_id (CASCADE)

-- Many-to-Many Relationships
movies ←→ genres (via movie_genres junction table)
users ←→ genres (via favorite_genres JSONField)
```

### **Advanced Constraints**
```sql
-- Business Logic Constraints
ALTER TABLE user_movie_interactions ADD CONSTRAINT check_rating_range
    CHECK (rating IS NULL OR (rating >= 1.0 AND rating <= 5.0));

ALTER TABLE user_recommendations ADD CONSTRAINT check_score_positive
    CHECK (score >= 0.0);

ALTER TABLE notifications_preferences ADD CONSTRAINT check_digest_day
    CHECK (digest_day >= 0 AND digest_day <= 6);

ALTER TABLE recommendation_experiments ADD CONSTRAINT check_traffic_split
    CHECK (traffic_split BETWEEN 0.1 AND 0.9);

ALTER TABLE recommendation_experiments ADD CONSTRAINT check_date_order
    CHECK (end_date > start_date);

-- Prevent duplicate experiments
ALTER TABLE recommendation_experiments ADD CONSTRAINT check_different_algorithms
    CHECK (algorithm_a != algorithm_b);
```

---

## 📈 **Performance Optimization**

### **JSON Field Queries**
```sql
-- Efficient favorite genres queries
SELECT * FROM users WHERE favorite_genres @> '[{"genre_id": 1}]';

-- Cast search in movies
SELECT * FROM movies WHERE main_cast @> '["Tom Hanks"]';

-- Metadata searches in interactions
SELECT * FROM user_movie_interactions 
WHERE metadata @> '{"source": "recommendation"}';
```

### **Composite Indexes for Common Patterns**
```sql
-- User recommendation serving
CREATE INDEX idx_user_recs_serving ON user_recommendations(
    user_id, score DESC, generated_at DESC
) WHERE clicked = false;

-- Movie popularity ranking
CREATE INDEX idx_movie_popularity_ranking ON movies(
    popularity_score DESC, tmdb_rating DESC, views DESC
);

-- User activity analysis
CREATE INDEX idx_user_activity_analysis ON user_activity_logs(
    user_id, action_type, timestamp DESC
);

-- Experiment user assignment
CREATE INDEX idx_experiment_user_assignment ON recommendation_experiments(
    is_active, start_date, end_date
) WHERE is_active = true;
```

### **Partitioning Strategy**
```sql
-- Partition activity logs by month for performance
CREATE TABLE user_activity_logs_y2025m08 PARTITION OF user_activity_logs
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

-- Partition notification logs by quarter
CREATE TABLE notification_logs_2025q3 PARTITION OF notification_logs
    FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');

-- Partition popularity metrics by year
CREATE TABLE popularity_metrics_2025 PARTITION OF popularity_metrics
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

---

## 🎯 **Enterprise Features**

### **A/B Testing Capabilities**
- **Algorithm Comparison:** Test different recommendation algorithms
- **Statistical Significance:** Built-in p-value and effect size tracking
- **Traffic Splitting:** Configurable user assignment percentages
- **Experiment Lifecycle:** Start, stop, analyze, and conclude experiments

### **Multi-Channel Notifications**
- **Email Campaigns:** Weekly digests and recommendation alerts
- **Push Notifications:** Real-time engagement on mobile devices
- **In-App Notifications:** Rich notifications with custom actions
- **Delivery Tracking:** Comprehensive analytics on open/click rates

### **Advanced Analytics**
- **User Behavior Tracking:** Complete activity logging for ML
- **Popularity Metrics:** Daily aggregated movie performance data
- **Recommendation Performance:** Algorithm effectiveness measurement
- **Engagement Analysis:** User interaction patterns and preferences

---

## 🛡️ **Data Privacy & Security**

### **GDPR Compliance**
```sql
-- User data export for GDPR requests
SELECT 
    u.*,
    np.*,
    array_agg(DISTINCT umi.*) as interactions,
    array_agg(DISTINCT ur.*) as recommendations,
    array_agg(DISTINCT ual.*) as activity_logs
FROM users u
LEFT JOIN notifications_preferences np ON u.id = np.user_id
LEFT JOIN user_movie_interactions umi ON u.id = umi.user_id
LEFT JOIN user_recommendations ur ON u.id = ur.user_id
LEFT JOIN user_activity_logs ual ON u.id = ual.user_id
WHERE u.id = :user_id
GROUP BY u.id, np.id;

-- User data deletion (cascading deletes handle cleanup)
DELETE FROM users WHERE id = :user_id;
```

### **Privacy Controls**
- **Demographic Targeting:** User-controllable via `allow_demographic_targeting`
- **Data Usage Consent:** Explicit consent tracking in `data_usage_consent`
- **Notification Preferences:** Granular control over all communication channels
- **Data Minimization:** Only collect necessary fields for functionality

---

## 📊 **Estimated Data Volumes (Production Scale)**

| Table | Year 1 | Year 3 | Storage (Y3) |
|-------|--------|--------|--------------|
| users | 100K | 500K | ~400 MB |
| genres | 50 | 50 | ~1 KB |
| movies | 50K | 150K | ~600 MB |
| movie_genres | 200K | 600K | ~60 MB |
| user_movie_interactions | 10M | 100M | ~20 GB |
| user_recommendations | 5M | 50M | ~10 GB |
| recommendation_experiments | 100 | 500 | ~1 MB |
| notifications_preferences | 100K | 500K | ~100 MB |
| notification_logs | 5M | 50M | ~10 GB |
| in_app_notifications | 2M | 20M | ~4 GB |
| user_activity_logs | 100M | 1B | ~200 GB |
| popularity_metrics | 2M | 20M | ~4 GB |
| **Total** | **122M** | **1.2B** | **~250 GB** |

**With Indexes & Overhead:** ~350 GB  
**Archive Strategy:** Move data older than 2 years to cold storage

---

## 📚 **Technical Decisions & Rationale**

### **PostgreSQL Over NoSQL**
**Decision:** Use PostgreSQL with JSON fields  
**Rationale:** ACID compliance, mature ecosystem, excellent JSON support  
**Trade-off:** Less horizontal scaling vs better consistency

### **Integrated Feedback System**
**Decision:** Merge feedback into `user_movie_interactions`  
**Rationale:** Simpler queries, better performance, unified user actions  
**Trade-off:** Larger table size vs query simplicity

### **JSON for Flexible Data**
**Decision:** Use JSON for `favorite_genres`, `main_cast`, and `metadata`  
**Rationale:** Schema flexibility, faster development, good PostgreSQL support  
**Trade-off:** Less strict validation vs development speed

### **Comprehensive A/B Testing**
**Decision:** Built-in experiment framework  
**Rationale:** Data-driven algorithm optimization, business value measurement  
**Trade-off:** Increased complexity vs measurable improvements

---

## 🚀 **Deployment & Scaling Strategy**

### **Development Environment**
- **Single PostgreSQL Instance:** All tables in one database
- **Redis Cache:** Session storage and frequent queries
- **Django Development Server:** Hot reloading for rapid iteration

### **Production Environment**
- **Primary/Replica Setup:** Read replicas for analytics queries
- **Connection Pooling:** PgBouncer for connection management
- **Monitoring:** PostgreSQL query performance and slow query logging
- **Backup Strategy:** Daily full backups with point-in-time recovery

### **Scaling Triggers & Strategies**

| Metric | Trigger | Strategy |
|--------|---------|----------|
| **Users** | > 1M | Consider read replicas |
| **Interactions** | > 100M | Implement table partitioning |
| **Activity Logs** | > 500M | Move to time-series database |
| **Query Response** | > 500ms | Add specialized indexes |
| **Storage** | > 500GB | Implement data archiving |

---

## 🔧 **Implementation Guidelines**

### **Django Model Optimization**
```python
# Use select_related for foreign keys
Movie.objects.select_related('user').all()

# Use prefetch_related for many-to-many
Movie.objects.prefetch_related('genres').all()

# Use database functions for aggregations
from django.db.models import Count, Avg
Movie.objects.annotate(
    interaction_count=Count('interactions'),
    avg_rating=Avg('interactions__rating')
)

# Use bulk operations for large datasets
UserMovieInteraction.objects.bulk_create([...])
```

### **API Design Patterns**
- **Pagination:** Use cursor-based pagination for large datasets
- **Filtering:** Leverage Django Filter for complex filtering
- **Caching:** Cache frequent queries with Redis
- **Rate Limiting:** Implement per-user rate limits for API endpoints

### **Background Jobs**
- **Recommendation Generation:** Celery tasks for ML pipeline
- **Metrics Aggregation:** Daily popularity metrics calculation
- **Notification Sending:** Async email and push notification delivery
- **Data Cleanup:** Archive old logs and recommendations

---

## 📝 **API Endpoint Overview**

### **Core Endpoints (150+ Total)**
- **Authentication:** 12 endpoints (login, register, profile, preferences)
- **Movies:** 25 endpoints (CRUD, search, recommendations, analytics)
- **Recommendations:** 45 endpoints (interactions, recommendations, experiments)
- **Notifications:** 35 endpoints (preferences, logs, in-app, health)
- **Analytics:** 30 endpoints (activity, popularity, trending, dashboards)

### **Real-Time Features**
- **WebSocket Notifications:** In-app notification delivery
- **Server-Sent Events:** Real-time recommendation updates
- **Live Analytics:** Dashboard updates for admin users

---

## 🎯 **Success Metrics & KPIs**

### **Business Metrics**
- **User Engagement:** Daily/Monthly Active Users
- **Recommendation CTR:** Click-through rates by algorithm
- **User Retention:** Cohort analysis and churn rates
- **Content Discovery:** Movies discovered through recommendations

### **Technical Metrics**
- **API Response Time:** < 200ms for 95th percentile
- **Database Query Performance:** < 100ms for complex queries
- **Notification Delivery Rate:** > 99% success rate
- **System Uptime:** > 99.9% availability

---

**Last Updated:** August 2025  
**Version:** 3.0 (Production Ready)  
**Status:** Enterprise-Level with ML & A/B Testing  
**Tables:** 12 (Comprehensive Feature Set)  
**Estimated Development:** 12-15 days for full implementation