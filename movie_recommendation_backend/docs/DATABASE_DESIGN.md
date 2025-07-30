# Movie Recommendation System - Final Database Design

**Project:** Movie Recommendation Backend (Simplified)  
**Technology Stack:** Django + PostgreSQL + Redis  
**Date:** December 2024  
**Author:** ALX ProDev Backend Engineering Program  
**Development Timeline:** 12 Days  

---

## 🎯 **Design Philosophy**

This simplified database design prioritizes **rapid development** and **core functionality** over complex normalization. Perfect for a 12-day sprint while maintaining all essential features for an enterprise-level movie recommendation system.

**Total Tables:** 10  
**Database Engine:** PostgreSQL 13+  
**Caching Layer:** Redis 6+  
**Reduction:** 50% fewer tables than original design (20 → 10)

---

## 📊 **Table Distribution by App**

| App | Tables | Core Purpose |
|-----|--------|--------------|
| **Authentication** | 1 | User management (merged profile) |
| **Movies** | 3 | Movie catalog with genres |
| **Recommendations** | 2 | AI-powered recommendation engine |
| **Notifications** | 2 | Multi-channel communication |
| **Analytics** | 2 | User behavior & performance tracking |
| **Total** | **10** | Complete system functionality |

---

## 🗄️ **Complete Database Schema**

### **1. Authentication App (1 Table)**

#### **1.1 users**
Consolidated user table with authentication, profile, and device information.

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
    
    -- User Profile Fields (Merged)
    date_of_birth: date NULL
    is_premium: boolean DEFAULT false
    phone_number: varchar(20) NULL
    bio: text DEFAULT ''
    avatar: varchar(200) NULL
    preferred_language: varchar(10) DEFAULT 'en'
    timezone: varchar(50) DEFAULT 'UTC'
    country: varchar(50) DEFAULT ''
    
    -- Device Information (Merged)
    device_token: varchar(500) NULL -- For push notifications
    device_type: varchar(20) NULL   -- 'ios', 'android', 'web'
    
    -- Preferences as JSON
    favorite_genres: text DEFAULT '[]' -- JSON array of genre IDs
    
    -- Timestamps
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- Indexes for Performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_device_token ON users(device_token) WHERE device_token IS NOT NULL;
```

---

### **2. Movies App (3 Tables)**

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
Core movie information with simplified cast/crew data.

```sql
movies {
    id: bigint PRIMARY KEY
    tmdb_id: integer UNIQUE NOT NULL
    omdb_id: varchar(20) UNIQUE NULL
    title: varchar(200) NOT NULL
    original_title: varchar(200) NOT NULL
    overview: text DEFAULT ''
    tagline: varchar(300) DEFAULT ''
    release_date: date NULL
    runtime: integer NULL -- minutes
    
    -- Simplified Cast/Crew (JSON)
    director: varchar(200) NULL        -- Main director name
    main_cast: text DEFAULT '[]'       -- JSON array of main actor names
    
    -- Ratings
    tmdb_rating: decimal(3,1) NULL
    tmdb_vote_count: integer DEFAULT 0
    omdb_rating: decimal(3,1) NULL
    our_rating: decimal(3,1) NULL      -- User-generated average
    
    -- Media Assets
    poster_path: varchar(200) NULL
    backdrop_path: varchar(200) NULL
    
    -- Performance Metrics
    popularity_score: float DEFAULT 0.0
    view_count: integer DEFAULT 0
    like_count: integer DEFAULT 0
    
    -- Metadata  
    adult: boolean DEFAULT false
    original_language: varchar(10) NOT NULL
    
    created_at: timestamp NOT NULL
    updated_at: timestamp NOT NULL
}

-- High-Performance Indexes
CREATE INDEX idx_movies_tmdb_id ON movies(tmdb_id);
CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movies_release_date ON movies(release_date DESC);
CREATE INDEX idx_movies_popularity ON movies(popularity_score DESC);
CREATE INDEX idx_movies_rating ON movies(tmdb_rating DESC);

-- Full-text search index
CREATE INDEX idx_movies_search ON movies USING GIN (to_tsvector('english', title || ' ' || overview));
```

#### **2.3 movie_genres**
Many-to-many relationship between movies and genres.

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

---

### **3. Recommendations App (2 Tables)**

#### **3.1 user_movie_interactions**
Comprehensive user-movie interaction tracking with integrated feedback.

```sql
user_movie_interactions {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    interaction_type: varchar(20) NOT NULL -- 'view', 'like', 'dislike', 'favorite', 'watchlist', 'rating'
    rating: integer NULL CHECK (rating BETWEEN 1 AND 5) -- For rating interactions
    
    -- Integrated Feedback System
    feedback_type: varchar(20) NULL       -- 'positive', 'negative', 'not_interested', 'already_seen'
    feedback_comment: text DEFAULT ''     -- Optional user comment
    
    -- Metadata
    source: varchar(30) DEFAULT 'web' NOT NULL -- 'web', 'mobile', 'email', 'push'
    timestamp: timestamp NOT NULL
    
    CONSTRAINT unique_user_movie_interaction UNIQUE(user_id, movie_id, interaction_type)
}

-- Machine Learning Optimized Indexes
CREATE INDEX idx_interactions_user_type ON user_movie_interactions(user_id, interaction_type);
CREATE INDEX idx_interactions_movie_type ON user_movie_interactions(movie_id, interaction_type);
CREATE INDEX idx_interactions_timestamp ON user_movie_interactions(timestamp DESC);
CREATE INDEX idx_interactions_rating ON user_movie_interactions(rating) WHERE rating IS NOT NULL;
CREATE INDEX idx_interactions_feedback ON user_movie_interactions(feedback_type) WHERE feedback_type IS NOT NULL;
```

#### **3.2 user_recommendations**
AI-generated movie recommendations for users.

```sql
user_recommendations {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    movie_id: bigint NOT NULL REFERENCES movies(id) ON DELETE CASCADE
    score: float NOT NULL CHECK (score BETWEEN 0.0 AND 1.0) -- Confidence score
    algorithm: varchar(50) NOT NULL -- 'collaborative', 'content_based', 'hybrid', 'trending'
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

---

### **4. Notifications App (2 Tables)**

#### **4.1 notification_preferences**
User preferences for email and push notifications.

```sql
notification_preferences {
    id: bigint PRIMARY KEY
    user_id: bigint UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE
    
    -- Email Notification Preferences
    weekly_digest: boolean DEFAULT true
    recommendation_alerts: boolean DEFAULT true
    trending_alerts: boolean DEFAULT false
    
    -- Push Notification Preferences
    push_recommendations: boolean DEFAULT true
    push_trending: boolean DEFAULT false
    
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

#### **4.2 notification_logs**
Comprehensive notification delivery tracking and analytics.

```sql
notification_logs {
    id: bigint PRIMARY KEY
    user_id: bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE
    notification_type: varchar(30) NOT NULL -- 'email', 'push'
    subject: varchar(200) NOT NULL
    content: text NOT NULL
    recipient: varchar(200) NOT NULL         -- Email address or device token
    status: varchar(20) DEFAULT 'pending'    -- 'pending', 'sent', 'delivered', 'failed', 'opened', 'clicked'
    external_id: varchar(100) NULL           -- SendGrid/Firebase message ID
    error_message: text DEFAULT ''
    
    -- Delivery Tracking Timestamps
    sent_at: timestamp NULL
    delivered_at: timestamp NULL
    opened_at: timestamp NULL
    clicked_at: timestamp NULL
    created_at: timestamp NOT NULL
}

-- Analytics Indexes
CREATE INDEX idx_notification_logs_user ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_status ON notification_logs(status);
CREATE INDEX idx_notification_logs_type ON notification_logs(notification_type);
CREATE INDEX idx_notification_logs_created ON notification_logs(created_at DESC);
```

---

### **5. Analytics App (2 Tables)**

#### **5.1 user_activity_logs**
Comprehensive user behavior tracking for analytics and machine learning.

```sql
user_activity_logs {
    id: bigint PRIMARY KEY
    user_id: bigint NULL REFERENCES users(id) ON DELETE SET NULL -- Can track anonymous users
    session_id: varchar(100) NOT NULL
    action_type: varchar(30) NOT NULL -- 'movie_view', 'movie_search', 'recommendation_click', 'email_open', 'email_click', 'push_click', 'rating_submit', 'favorite_add', 'watchlist_add'
    movie_id: bigint NULL REFERENCES movies(id) ON DELETE SET NULL
    
    -- Request Metadata
    ip_address: varchar(45) NOT NULL        -- IPv4 or IPv6
    user_agent: text NOT NULL
    referer: varchar(500) NULL
    source: varchar(30) NOT NULL           -- 'web', 'mobile', 'email', 'push'
    
    -- Flexible Additional Data
    metadata: text DEFAULT '{}'            -- JSON string for extensibility
    timestamp: timestamp NOT NULL
}

-- Analytics-Optimized Indexes
CREATE INDEX idx_activity_logs_user_action ON user_activity_logs(user_id, action_type);
CREATE INDEX idx_activity_logs_timestamp ON user_activity_logs(timestamp DESC);
CREATE INDEX idx_activity_logs_movie_action ON user_activity_logs(movie_id, action_type);
CREATE INDEX idx_activity_logs_session ON user_activity_logs(session_id);
CREATE INDEX idx_activity_logs_source ON user_activity_logs(source);

-- Time-based partitioning for large datasets
-- CREATE TABLE user_activity_logs_2024_12 PARTITION OF user_activity_logs
--   FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
```

#### **5.2 popularity_metrics**
Daily aggregated movie popularity and performance metrics.

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
    recommendation_count: integer DEFAULT 0    -- Times recommended
    click_through_rate: decimal(5,4) DEFAULT 0.0000 -- CTR for recommendations
    
    CONSTRAINT unique_movie_date UNIQUE(movie_id, date)
}

-- Trending and Analytics Indexes
CREATE INDEX idx_popularity_metrics_movie ON popularity_metrics(movie_id);
CREATE INDEX idx_popularity_metrics_date ON popularity_metrics(date DESC);
CREATE INDEX idx_popularity_metrics_views ON popularity_metrics(view_count DESC);
CREATE INDEX idx_popularity_metrics_ctr ON popularity_metrics(click_through_rate DESC);
```

---

## 🔗 **Relationships & Constraints**

### **Primary Relationships**
```sql
-- One-to-One Relationships
users.id ←→ notification_preferences.user_id

-- One-to-Many Relationships
users.id → user_movie_interactions.user_id
users.id → user_recommendations.user_id
users.id → notification_logs.user_id
users.id → user_activity_logs.user_id

movies.id → user_movie_interactions.movie_id
movies.id → user_recommendations.movie_id
movies.id → movie_genres.movie_id
movies.id → popularity_metrics.movie_id

genres.id → movie_genres.genre_id

-- Many-to-Many Relationships
users ←→ genres (via favorite_genres JSON field)
movies ←→ genres (via movie_genres junction table)
```

### **Referential Integrity**
```sql
-- Cascade Deletes for User Data
ALTER TABLE user_movie_interactions ADD CONSTRAINT fk_interactions_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE notification_preferences ADD CONSTRAINT fk_notification_prefs_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Set NULL for Optional References
ALTER TABLE user_activity_logs ADD CONSTRAINT fk_activity_logs_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- Check Constraints
ALTER TABLE user_movie_interactions ADD CONSTRAINT check_rating_range
    CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5));

ALTER TABLE user_recommendations ADD CONSTRAINT check_score_range
    CHECK (score >= 0.0 AND score <= 1.0);

ALTER TABLE notification_preferences ADD CONSTRAINT check_digest_day
    CHECK (digest_day >= 1 AND digest_day <= 7);
```

---

## 📈 **Performance Optimization**

### **JSON Field Usage**
```sql
-- Efficient JSON queries for favorite genres
SELECT * FROM users WHERE favorite_genres::jsonb ? '1'; -- Check if genre ID 1 is in favorites

-- Efficient JSON queries for cast search
SELECT * FROM movies WHERE main_cast::jsonb ? 'Tom Hanks'; -- Check if actor is in main cast
```

### **Composite Indexes**
```sql
-- Multi-column indexes for common query patterns
CREATE INDEX idx_interactions_user_movie_type ON user_movie_interactions(user_id, movie_id, interaction_type);
CREATE INDEX idx_recommendations_user_score_generated ON user_recommendations(user_id, score DESC, generated_at DESC);
CREATE INDEX idx_movies_rating_popularity ON movies(tmdb_rating DESC, popularity_score DESC);
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

## 🎯 **Simplification Benefits**

### **Development Speed**
- **50% fewer tables** (10 vs 20)
- **Simpler relationships**
- **Faster migrations**
- **Reduced complexity**

### **Performance Benefits**
- **Fewer JOINs** required
- **Better cache locality**
- **Simplified queries**
- **Faster API responses**

### **Maintenance Benefits**
- **Easier debugging**
- **Simpler backup/restore**
- **Reduced index maintenance**
- **Clearer data model**

---

## 🛡️ **Data Privacy & Security**

### **Sensitive Data Handling**
```sql
-- Encrypt sensitive PII at application level
-- Email addresses, phone numbers, IP addresses
-- Use Django's encryption utilities

-- Row Level Security (if needed)
ALTER TABLE user_movie_interactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_data_policy ON user_movie_interactions
    FOR ALL TO authenticated_users
    USING (user_id = current_setting('app.current_user_id')::bigint);
```

### **GDPR Compliance**
```sql
-- User data export query
SELECT u.*, np.*, array_agg(umi.*) as interactions
FROM users u
LEFT JOIN notification_preferences np ON u.id = np.user_id
LEFT JOIN user_movie_interactions umi ON u.id = umi.user_id
WHERE u.id = :user_id
GROUP BY u.id, np.id;

-- User data deletion (cascading deletes handle most cleanup)
DELETE FROM users WHERE id = :user_id;
```

---

## 📊 **Estimated Data Volumes (1 Year)**

| Table | Estimated Rows | Storage Size |
|-------|---------------|--------------|
| users | 100,000 | ~80 MB |
| genres | 50 | ~1 KB |
| movies | 50,000 | ~200 MB |
| movie_genres | 200,000 | ~20 MB |
| user_movie_interactions | 10,000,000 | ~2 GB |
| user_recommendations | 5,000,000 | ~1 GB |
| notification_preferences | 100,000 | ~20 MB |
| notification_logs | 2,000,000 | ~500 MB |
| user_activity_logs | 50,000,000 | ~10 GB |
| popularity_metrics | 1,800,000 | ~200 MB |
| **Total** | **68,350,050** | **~14 GB** |

**With Indexes:** ~20 GB  
**Archive Strategy:** Move logs older than 1 year to cold storage

---

## 📚 **Technical Decisions & Trade-offs**

### **JSON vs Normalized Tables**
**Decision:** Use JSON for `favorite_genres` and `main_cast`  
**Rationale:** Faster development, flexible schema, good PostgreSQL JSON support  
**Trade-off:** Less strict data integrity, harder complex queries

### **Merged User Profile**
**Decision:** Store profile data in `users` table  
**Rationale:** Simpler queries, better performance, faster development  
**Trade-off:** Larger user table, less separation of concerns

### **Simplified Cast/Crew**
**Decision:** Store only director name and main cast JSON  
**Rationale:** 80% of use cases covered, much simpler implementation  
**Trade-off:** Loss of detailed person information and relationships

---

## 🎯 **Future Scaling Options**

### **When to Split Tables**
- **Users > 1M:** Consider splitting profile data
- **Movies > 100K:** Consider normalizing cast/crew
- **Interactions > 50M:** Implement sharding
- **Activity Logs > 100M:** Move to time-series database

### **Scaling Strategies**
- **Read Replicas:** For analytics queries
- **Sharding:** By user_id for interactions
- **Caching:** Redis for frequently accessed data
- **CDN:** For movie posters and static assets

---

## 📝 **Implementation Notes**

1. **Django Models:** Use `JSONField` for flexible data
2. **API Design:** Leverage fewer JOINs for better performance
3. **Testing:** Focus on core workflows with simplified relationships
4. **Documentation:** API docs generated from simplified schema
5. **Monitoring:** Track performance metrics in `popularity_metrics`

---

**Last Updated:** December 2024  
**Version:** 2.0 (Simplified)  
**Status:** Production Ready - Optimized for 12-Day Development  
**Tables:** 10 (50% reduction from original 20-table design)