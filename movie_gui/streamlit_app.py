# streamlit_app.py
import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Dict, Any, Optional, List
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Enhanced Configuration with production and local support
class Config:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "auto")  # auto, production, local
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
    
    @property
    def api_base_url(self) -> str:
        """Get API URL based on environment with fallback logic"""
        if self.environment == "production":
            return "https://alx-project-nexus-y0c5.onrender.com"
        elif self.environment == "local":
            return "http://127.0.0.1:8001"
        else:
            # Auto-detect: try production first, then local
            production_url = "https://alx-project-nexus-y0c5.onrender.com"
            local_url = "http://127.0.0.1:8001"
            
            # Try production first (with longer timeout for Render wake-up)
            try:
                response = requests.get(f"{production_url}/health/", timeout=10)
                if response.status_code == 200:
                    return production_url
            except:
                pass
            
            # Fallback to local
            try:
                response = requests.get(f"{local_url}/health/", timeout=3)
                if response.status_code == 200:
                    return local_url
            except:
                pass
            
            # Default to production
            return production_url

config = Config()

# Page configuration
st.set_page_config(
    page_title="🎬 CineFlow - AI Movie Recommendations",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': 'https://github.com/your-repo/issues',
        'About': "# CineFlow\nAI-powered movie recommendations with comprehensive analytics!"
    }
)

# Enhanced Custom CSS with modern design
def load_custom_css():
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        .main {
            font-family: 'Inter', sans-serif;
        }
        
        .main-header {
            font-size: 4rem;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin-bottom: 2rem;
            text-shadow: 0 4px 8px rgba(0,0,0,0.1);
            animation: fadeInDown 1s ease-out;
        }
        
        .hero-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4rem 2rem;
            border-radius: 25px;
            text-align: center;
            margin: 2rem 0;
            box-shadow: 0 25px 50px rgba(102, 126, 234, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .hero-section::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
            animation: shimmer 4s infinite;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }
        
        .feature-card {
            background: white;
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .feature-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        }
        
        .feature-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }
        
        .movie-card {
            background: white;
            border-radius: 18px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .movie-card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }
        
        .movie-poster {
            width: 120px;
            height: 180px;
            object-fit: cover;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(79, 172, 254, 0.3);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: scale(1.05);
        }
        
        .auth-container {
            background: white;
            border-radius: 25px;
            padding: 3rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            margin: 2rem 0;
        }
        
        .progress-container {
            background: #f7fafc;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        .notification-card {
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            border-left: 5px solid #ff6b6b;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }
        
        .recommendation-card {
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        }
        
        .metric-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 6px 20px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
        }
        
        .genre-tag {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 25px;
            font-size: 0.85rem;
            font-weight: 500;
            margin: 0.3rem;
            display: inline-block;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .genre-tag:hover {
            transform: scale(1.05);
        }
        
        .connection-status {
            padding: 1rem;
            border-radius: 12px;
            margin: 0.5rem 0;
            font-weight: 600;
            text-align: center;
            font-size: 0.9rem;
        }
        
        .status-connected {
            background: linear-gradient(45deg, #4ade80, #22c55e);
            color: white;
        }
        
        .status-error {
            background: linear-gradient(45deg, #ef4444, #dc2626);
            color: white;
        }
        
        .status-checking {
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
            color: white;
        }
        
        .rating-stars {
            color: #fbbf24;
            font-size: 1.3rem;
            text-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .analytics-card {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            margin: 1rem 0;
        }
        
        /* Animations */
        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        /* Loading animations */
        .loading-spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .main-header {
                font-size: 2.5rem;
            }
            
            .hero-section {
                padding: 2rem 1rem;
            }
            
            .feature-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """
    
    st.markdown(css, unsafe_allow_html=True)


def init_session_state():
    """Initialize all session state variables with safe defaults"""
    defaults = {
        'authenticated': False,
        'token': None,
        'refresh_token': None,
        'user_info': {},  # ← Change from None to empty dict
        'user_profile': {},  # ← Change from None to empty dict
        'backend_status': None,
        'api_environment': None,
        'popular_movies': {"results": []},  # ← Change from None to empty structure
        'movie_stats': {},  # ← Change from None to empty dict
        'user_recommendations': {"results": []},  # ← Change from None to empty structure
        'user_interactions': {"results": []},  # ← Change from None to empty structure
        'notifications': {"results": []},  # ← Change from None to empty structure
        'analytics_data': {},  # ← Change from None to empty dict
        'genres': {"results": []},  # ← Change from None to empty structure
        'selected_genres': [],
        'demo_mode': False,
        'user_journey': 'first_visit',
        'onboarding_step': 0,
        'registration_progress': 0,
        'connection_attempts': 0,
        'last_api_call': None,
        'trending_movies': {"results": []},  # ← Change from None to empty structure
        'recommendation_performance': {}  # ← Change from None to empty dict
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Enhanced API Helper Functions
def make_api_request(endpoint: str, method: str = "GET", data: dict = None, 
                    auth_required: bool = True, timeout: int = 15) -> Optional[requests.Response]:
    """Enhanced API request function with comprehensive error handling"""
    headers = {"Content-Type": "application/json"}
    
    if auth_required and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    
    url = f"{config.api_base_url}{endpoint}"
    st.session_state.last_api_call = datetime.now()
    
    try:
        response = None
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=timeout)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=timeout)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=timeout)
        
        # Update connection status and environment
        if response:
            st.session_state.backend_status = "connected"
            if "render.com" in config.api_base_url:
                st.session_state.api_environment = "production"
            else:
                st.session_state.api_environment = "local"
        
        return response
        
    except requests.exceptions.ConnectionError:
        st.session_state.backend_status = "connection_error"
        st.session_state.connection_attempts += 1
        return None
    except requests.exceptions.Timeout:
        st.session_state.backend_status = "timeout"
        return None
    except requests.exceptions.RequestException as e:
        st.session_state.backend_status = "error"
        return None
    except Exception as e:
        st.session_state.backend_status = "error"
        return None

def check_backend_health() -> bool:
    """Enhanced health check with environment detection"""
    try:
        # Try the health endpoint or fallback endpoints
        health_endpoints = ["/health/", "/", "/api/health/"]
        
        for endpoint in health_endpoints:
            try:
                response = requests.get(f"{config.api_base_url}{endpoint}", timeout=8)
                if response.status_code == 200:
                    st.session_state.backend_status = "connected"
                    if "render.com" in config.api_base_url:
                        st.session_state.api_environment = "production"
                    else:
                        st.session_state.api_environment = "local"
                    return True
            except:
                continue
        
        st.session_state.backend_status = "connection_error"
        return False
    except:
        st.session_state.backend_status = "connection_error"
        return False

# Data fetching functions
def fetch_popular_movies():
    """Fetch popular movies with enhanced error handling"""
    if st.session_state.popular_movies is None:
        try:
            response = make_api_request("/movies/api/v1/movies/popular/", auth_required=False)
            if response and response.status_code == 200:
                data = response.json()
                # Ensure we have the right structure
                if isinstance(data, dict) and 'results' in data:
                    st.session_state.popular_movies = data
                elif isinstance(data, list):
                    st.session_state.popular_movies = {"results": data}
                else:
                    st.session_state.popular_movies = {"results": []}
            else:
                # Enhanced fallback data based on your seeded movies
                st.session_state.popular_movies = {
                    "results": [
                        {
                            "id": 1,
                            "title": "Spider-Man: No Way Home",
                            "tmdb_rating": 7.9,
                            "release_date": "2021-12-15",
                            "overview": "Peter Parker's secret identity is revealed to the entire world. Desperate for help, Peter turns to Doctor Strange to make the world forget that he is Spider-Man.",
                            "popularity_score": 30.58,
                            "poster_path": "/1g0dhYtq4irTY1GPXvft6k4YLjm.jpg",
                            "views": 15420,
                            "like_count": 892
                        },
                        {
                            "id": 2,
                            "title": "Inside Out 2", 
                            "tmdb_rating": 7.6,
                            "release_date": "2024-06-11",
                            "overview": "Return to the mind of newly minted teenager Riley just as headquarters is undergoing a sudden demolition to make room for something entirely unexpected: new Emotions!",
                            "popularity_score": 35.45,
                            "poster_path": "/vpnVM9B6NMmQpWeZvzLvDESb2QY.jpg",
                            "views": 12890,
                            "like_count": 734
                        },
                        {
                            "id": 3,
                            "title": "Despicable Me 4",
                            "tmdb_rating": 7.0,
                            "release_date": "2024-06-20", 
                            "overview": "Gru and Lucy and their girls—Margo, Edith and Agnes—welcome a new member to the Gru family, Gru Jr., who seems intent on tormenting his dad.",
                            "popularity_score": 37.4,
                            "poster_path": "/wWba3TaojhK7NdycRhoQpsG0FaH.jpg",
                            "views": 10234,
                            "like_count": 623
                        }
                    ]
                }
        except Exception as e:
            # Fallback to demo data on any error
            st.session_state.popular_movies = {
                "results": [
                    {
                        "id": 1,
                        "title": "Spider-Man: No Way Home",
                        "tmdb_rating": 7.9,
                        "release_date": "2021-12-15",
                        "overview": "Peter Parker's secret identity is revealed to the entire world.",
                        "popularity_score": 30.58,
                        "views": 15420,
                        "like_count": 892
                    }
                ]
            }

def fetch_movie_stats():
    """Fetch comprehensive movie statistics with error handling"""
    if st.session_state.movie_stats is None:
        try:
            response = make_api_request("/movies/api/v1/movies/stats/", auth_required=False)
            if response and response.status_code == 200:
                data = response.json()
                # Ensure we have a valid dictionary
                if isinstance(data, dict):
                    st.session_state.movie_stats = data
                else:
                    st.session_state.movie_stats = {}
            else:
                # Enhanced fallback stats
                st.session_state.movie_stats = {
                    "total_movies": 100,
                    "total_users": 1247,
                    "total_ratings": 15643,
                    "total_recommendations": 48921,
                    "genres_count": 18,
                    "avg_rating": 7.2,
                    "recent_additions": 23,
                    "popular_this_week": 45
                }
        except Exception as e:
            # Fallback stats on any error
            st.session_state.movie_stats = {
                "total_movies": 100,
                "total_users": 1247,
                "total_ratings": 15643,
                "total_recommendations": 48921,
                "genres_count": 18,
                "avg_rating": 7.2,
                "recent_additions": 23,
                "popular_this_week": 45
            }

def fetch_trending_movies():
    """Fetch trending movies from analytics with error handling"""
    if st.session_state.trending_movies is None:
        try:
            response = make_api_request("/analytics/api/v1/trending/", auth_required=False)
            if response and response.status_code == 200:
                data = response.json()
                # Ensure we have the right structure
                if isinstance(data, dict) and 'results' in data:
                    st.session_state.trending_movies = data
                elif isinstance(data, list):
                    st.session_state.trending_movies = {"results": data}
                else:
                    st.session_state.trending_movies = {"results": []}
            else:
                # Fallback trending data
                st.session_state.trending_movies = {"results": []}
        except Exception as e:
            # Silent fallback on error
            st.session_state.trending_movies = {"results": []}

def fetch_user_recommendations():
    """Fetch user's personalized recommendations with error handling"""
    if st.session_state.authenticated and st.session_state.user_recommendations is None:
        try:
            response = make_api_request("/recommendations/v1/recommendations/personalized/")
            if response and response.status_code == 200:
                st.session_state.user_recommendations = response.json()
            else:
                # Set empty structure instead of None
                st.session_state.user_recommendations = {"results": []}
        except Exception as e:
            # Fail gracefully
            st.session_state.user_recommendations = {"results": []}
def fetch_user_profile():
    """Fetch complete user profile with enhanced error handling"""
    if not st.session_state.get('authenticated'):
        return
        
    if st.session_state.get('user_profile') is None:
        try:
            response = make_api_request("/recommendations/v1/users/me/")
            if response and response.status_code == 200:
                st.session_state.user_profile = response.json()
            else:
                st.session_state.user_profile = {}
        except Exception as e:
            st.session_state.user_profile = {}

def fetch_genres():
    """Fetch available genres"""
    if st.session_state.genres is None:
        response = make_api_request("/movies/api/v1/genres/", auth_required=False)
        if response and response.status_code == 200:
            st.session_state.genres = response.json()

def fetch_user_notifications():
    """Fetch user notifications with enhanced error handling"""
    if not st.session_state.get('authenticated'):
        return
        
    if st.session_state.get('notifications') is None:
        try:
            response = make_api_request("/notifications/api/v1/inapp/recent/")
            if response and response.status_code == 200:
                st.session_state.notifications = response.json()
            else:
                st.session_state.notifications = {"results": []}
        except Exception as e:
            st.session_state.notifications = {"results": []}


def logout():
    """Enhanced logout with safe cleanup"""
    try:
        if st.session_state.get('token'):
            # Try to call logout endpoint
            make_api_request("/authentication/auth/logout/", method="POST")
    except Exception as e:
        # Continue with logout even if API call fails
        pass
    
    # Clear all user-related session state safely
    user_keys = ['authenticated', 'token', 'refresh_token', 'user_info', 'user_profile', 
                 'user_recommendations', 'user_interactions', 'notifications']
    for key in user_keys:
        if key in st.session_state:
            if key == 'authenticated':
                st.session_state[key] = False
            else:
                st.session_state[key] = None
    
    st.session_state.user_journey = 'returning_visitor'
    
    st.success("👋 Successfully logged out! See you next time!")
    time.sleep(1.5)
    st.rerun()

# Enhanced Authentication Pages
def show_authentication_page():
    """Beautiful authentication page with comprehensive functionality"""
    
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 3rem; margin-bottom: 1rem; font-weight: 800;">🎬 Welcome to CineFlow</h1>
        <p style="font-size: 1.3rem; margin-bottom: 2rem; opacity: 0.95;">Discover your next favorite movie with AI-powered recommendations</p>
        <div style="font-size: 3rem; margin: 1rem 0; opacity: 0.8;">🍿 🎭 ⭐ 🎪 🎨</div>
        <p style="font-size: 1.1rem; opacity: 0.9;">Join thousands of movie enthusiasts and unlock personalized recommendations!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced tabs with better styling
    tab1, tab2, tab3 = st.tabs(["🔐 **Sign In**", "🌟 **Join CineFlow**", "👁️ **Explore Preview**"])
    
    with tab1:
        show_enhanced_login_form()
    
    with tab2:
        show_enhanced_registration_form()
    
    with tab3:
        show_enhanced_preview_content()

def show_enhanced_login_form():
    """Enhanced login form - supports login with username OR email"""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("### 🔐 Welcome Back!")
        st.markdown("Sign in to continue your movie journey")
        
        with st.form("login_form", clear_on_submit=False):
            # Single identifier field that accepts username OR email
            identifier = st.text_input(
                "👤 Username or Email *", 
                placeholder="Enter your username or email",
                help="You can use either your username or email address to log in"
            )
            password = st.text_input(
                "🔒 Password *", 
                type="password", 
                placeholder="Enter your password"
            )
            
            col_a, col_b = st.columns([1, 1])
            with col_a:
                remember_me = st.checkbox("🔄 Remember me")
            with col_b:
                st.markdown("*[Forgot password?](#)*")
            
            submit = st.form_submit_button("🚀 **Sign In**", use_container_width=True)
        
        if submit:
            if identifier and password:
                with st.spinner("🔑 Authenticating..."):
                    # Progress bar for better UX
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.01)
                        progress_bar.progress(i + 1)
                    
                    # Determine if identifier is email or username
                    is_email = '@' in identifier
                    identifier_type = "email" if is_email else "username"
                    
                    # Prepare login data - use identifier as-is
                    login_data = {
                        "identifier": identifier.strip(),
                        "password": password
                    }
                    
                    # Debug login attempt
                    st.info(f"🔍 **Debug:** Attempting login with {identifier_type}: `{identifier}`")
                    st.info(f"🔍 **Endpoint:** `/authentication/auth/login/`")
                    with st.expander("📋 Login Data (Debug)", expanded=False):
                        safe_login_data = login_data.copy()
                        safe_login_data["password"] = "***HIDDEN***"
                        st.json(safe_login_data)
                    
                    # Use actual login endpoint
                    response = make_api_request(
                        "/authentication/auth/login/",
                        method="POST",
                        data=login_data,
                        auth_required=False
                    )
                    
                    if response and response.status_code == 200:
                        try:
                            data = response.json()
                            
                            # Handle different token response formats
                            access_token = (
                                data.get("access") or 
                                data.get("access_token") or 
                                data.get("token") or
                                data.get("key")  # Some APIs use 'key'
                            )
                            
                            refresh_token = (
                                data.get("refresh") or 
                                data.get("refresh_token")
                            )
                            
                            user_data = data.get("user", {})
                            
                            if access_token:
                                st.session_state.authenticated = True
                                st.session_state.token = access_token
                                if refresh_token:
                                    st.session_state.refresh_token = refresh_token
                                
                                # Store user info - prefer data from response
                                if user_data:
                                    st.session_state.user_info = user_data
                                else:
                                    st.session_state.user_info = {
                                        "username": identifier if not is_email else "user",
                                        "email": identifier if is_email else ""
                                    }
                                
                                st.session_state.user_journey = 'authenticated'
                                
                                # Clear cached data to fetch fresh user data
                                st.session_state.user_profile = None
                                st.session_state.user_recommendations = None
                                
                                # Show success message with user info
                                username_display = user_data.get('username', identifier)
                                st.success(f"✅ Login successful! Welcome back, {username_display}!")
                                st.balloons()
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("❌ Login response missing token")
                                st.json(data)
                                
                        except Exception as e:
                            st.error(f"❌ Error parsing login response: {str(e)}")
                            st.text(f"Raw response: {response.text}")
                            
                    else:
                        st.error("❌ Invalid credentials. Please check your login details.")
                        
                        if response:
                            st.error(f"🚨 **HTTP Status:** {response.status_code}")
                            try:
                                error_data = response.json()
                                st.error("📄 **Server Response:**")
                                st.json(error_data)
                                
                                if "detail" in error_data:
                                    st.info(f"💡 **Server message**: {error_data['detail']}")
                                elif "non_field_errors" in error_data:
                                    st.info(f"💡 **Error**: {error_data['non_field_errors'][0]}")
                                elif "identifier" in error_data:
                                    st.info(f"💡 **Identifier error**: {error_data['identifier']}")
                                elif "password" in error_data:
                                    st.info(f"💡 **Password error**: {error_data['password']}")
                                    
                            except:
                                st.error(f"📄 **Raw Response:** {response.text}")
                                
                            # Enhanced troubleshooting
                            st.markdown("""
                            ### 🔧 **Login Troubleshooting:**
                            
                            1. **Check Credentials:**
                               - Ensure username/email and password are correct
                               - Check if caps lock is on
                               - Make sure account was created successfully
                            
                            2. **Account Status:**
                               - Verify account exists in Django admin
                               - Check if account is active
                               - Ensure no typos in username/email
                            
                            3. **Alternative Login Methods:**
                            """)
                            
                            # Try alternative formats if the main one fails
                            if not is_email:
                                # If they used username, offer to try as email
                                if st.button("🔄 **Try as Email**", key="try_email"):
                                    email_login_data = {
                                        "identifier": f"{identifier}@example.com",  # Add domain if missing
                                        "password": password
                                    }
                                    
                                    st.info("🔄 Trying with email format...")
                                    email_response = make_api_request(
                                        "/authentication/auth/login/",
                                        method="POST",
                                        data=email_login_data,
                                        auth_required=False
                                    )
                                    
                                    if email_response and email_response.status_code == 200:
                                        st.success("✅ Email format worked!")
                                        # Process successful login
                                        try:
                                            data = email_response.json()
                                            access_token = (
                                                data.get("access") or 
                                                data.get("access_token") or 
                                                data.get("token")
                                            )
                                            if access_token:
                                                st.session_state.authenticated = True
                                                st.session_state.token = access_token
                                                st.session_state.user_info = data.get("user", {"username": identifier})
                                                st.rerun()
                                        except:
                                            pass
                                    else:
                                        st.error("❌ Email format also failed")
                            
                            # Suggest checking Django admin
                            st.markdown(f"""
                            ### 🔍 **Manual Verification:**
                            1. **Check Django Admin:** {config.api_base_url}/admin/auth/user/
                            2. **Look for user:** `{identifier}`
                            3. **Verify account is active and password is correct**
                            
                            ### 💡 **Common Issues:**
                            - **Case sensitivity:** Username might be case-sensitive
                            - **Account not activated:** Check if email verification is required
                            - **Wrong endpoint:** Login endpoint might be different
                            - **Password not hashed:** Registration might have failed to hash password
                            """)
                            
                        else:
                            st.error("🌐 **Connection Issue:** Cannot reach login endpoint")
                            
                            st.markdown("""
                            ### 🔧 **Connection Troubleshooting:**
                            1. **Backend Status:** Check if Render service is awake
                            2. **Network:** Verify internet connection
                            3. **Endpoint:** Confirm `/authentication/auth/login/` exists
                            4. **Wait and Retry:** Render free tier can be slow
                            """)
                            
                        st.info("💡 **Tip**: You can use either your username OR email address to log in")
            else:
                missing = []
                if not identifier: missing.append("Username/Email")
                if not password: missing.append("Password")
                st.warning(f"⚠️ Please enter: {' and '.join(missing)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Optional: Add a quick login test function
def test_login_credentials():
    """Quick test function to verify login credentials"""
    st.markdown("### 🧪 **Test Login Credentials**")
    
    with st.form("test_login_form"):
        test_identifier = st.text_input("Test Username/Email:", value="qwerty")
        test_password = st.text_input("Test Password:", type="password", value="#Cantwell")
        
        if st.form_submit_button("🔍 **Test Login**"):
            login_data = {
                "identifier": test_identifier,
                "password": test_password
            }
            
            with st.spinner("Testing login..."):
                response = make_api_request(
                    "/authentication/auth/login/",
                    method="POST",
                    data=login_data,
                    auth_required=False
                )
                
                if response:
                    st.write(f"**HTTP Status:** {response.status_code}")
                    
                    if response.status_code == 200:
                        st.success("✅ Login test successful!")
                        try:
                            response_data = response.json()
                            st.json(response_data)
                            
                            # Show what tokens are available
                            tokens = []
                            if response_data.get("access"): tokens.append("access")
                            if response_data.get("access_token"): tokens.append("access_token") 
                            if response_data.get("token"): tokens.append("token")
                            if response_data.get("key"): tokens.append("key")
                            
                            if tokens:
                                st.info(f"🔑 **Available tokens:** {', '.join(tokens)}")
                            else:
                                st.warning("⚠️ **No tokens found in response**")
                                
                        except Exception as e:
                            st.error(f"Could not parse JSON: {e}")
                            st.code(response.text)
                    else:
                        st.error("❌ Login test failed")
                        try:
                            st.json(response.json())
                        except:
                            st.code(response.text)
                else:
                    st.error("❌ No response from login endpoint")

# Enhanced authentication page that includes the test function
def show_enhanced_authentication_page():
    """Enhanced authentication page with testing capabilities"""
    
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 3rem; margin-bottom: 1rem; font-weight: 800;">🎬 Welcome to CineFlow</h1>
        <p style="font-size: 1.3rem; margin-bottom: 2rem; opacity: 0.95;">Discover your next favorite movie with AI-powered recommendations</p>
        <div style="font-size: 3rem; margin: 1rem 0; opacity: 0.8;">🍿 🎭 ⭐ 🎪 🎨</div>
        <p style="font-size: 1.1rem; opacity: 0.9;">Join thousands of movie enthusiasts and unlock personalized recommendations!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced tabs with better styling
    tab1, tab2, tab3, tab4 = st.tabs(["🔐 **Sign In**", "🌟 **Join CineFlow**", "👁️ **Explore Preview**", "🧪 **Test Login**"])
    
    with tab1:
        show_enhanced_login_form()
    
    with tab2:
        show_enhanced_registration_form()
    
    with tab3:
        show_enhanced_preview_content()
    
    with tab4:
        test_login_credentials()

def show_enhanced_registration_form():
    """Enhanced registration with actual API integration"""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("### 🌟 Join CineFlow Community!")
        st.markdown("Create your account and start discovering amazing movies")
        
        # Registration progress indicator
        progress_steps = ["Basic Info", "Movie Preferences", "Complete"]
        current_step = st.session_state.get('registration_progress', 0)
        
        # Progress visualization
        progress_html = f"""
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" style="width: {(current_step + 1) * 33.33}%"></div>
            </div>
            <p style="text-align: center; margin: 1rem 0; color: #666; font-weight: 500;">
                Step {current_step + 1} of 3: {progress_steps[current_step]}
            </p>
        </div>
        """
        st.markdown(progress_html, unsafe_allow_html=True)
        
        with st.form("register_form", clear_on_submit=False):
            if current_step == 0:
                show_basic_info_step()
            elif current_step == 1:
                show_preferences_step()
            else:
                show_completion_step()

def show_basic_info_step():
    """Registration with proper 201 handling"""
    st.markdown("#### 🔹 Create Your Account")
    
    col_a, col_b = st.columns(2)
    with col_a:
        username = st.text_input(
            "👤 Username *", 
            placeholder="Choose a unique username",
            help="This will be your unique identifier on CineFlow"
        )
        first_name = st.text_input("👤 First Name", placeholder="Your first name (optional)")
    
    with col_b:
        email = st.text_input(
            "📧 Email *", 
            placeholder="your.email@example.com",
            help="Must be unique - we'll use this for important updates"
        )
        last_name = st.text_input("👤 Last Name", placeholder="Your last name (optional)")
    
    st.markdown("#### 🔒 Security")
    col_c, col_d = st.columns(2)
    with col_c:
        password = st.text_input(
            "🔒 Password *", 
            type="password", 
            placeholder="Minimum 8 characters",
            help="Use a strong password with letters, numbers, and symbols"
        )
    with col_d:
        password_confirm = st.text_input(
            "🔒 Confirm Password *", 
            type="password", 
            placeholder="Repeat your password"
        )
    
    # Password strength indicator
    if password:
        strength = calculate_password_strength(password)
        strength_colors = ["#ef4444", "#f59e0b", "#10b981"]
        strength_texts = ["Weak", "Medium", "Strong"]
        
        color = strength_colors[min(strength, 2)]
        text = strength_texts[min(strength, 2)]
        
        st.markdown(f"""
        <div style="margin: 0.5rem 0;">
            <small>Password Strength: </small>
            <span style="color: {color}; font-weight: bold;">{text}</span>
            <div style="width: 100%; height: 6px; background: #e5e7eb; border-radius: 3px; margin-top: 6px;">
                <div style="width: {(strength + 1) * 33.33}%; height: 100%; background: {color}; border-radius: 3px; transition: width 0.3s;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    agree_terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
    
    next_button = st.form_submit_button("✅ **Create Account**", use_container_width=True)
    
    if next_button:
        if all([username, email, password, password_confirm]) and agree_terms:
            if password == password_confirm and len(password) >= 8:
                registration_data = {
                    "username": username,
                    "email": email.lower().strip(),
                    "password": password,
                    "password_confirm": password_confirm,
                }
                
                if first_name:
                    registration_data["first_name"] = first_name
                if last_name:
                    registration_data["last_name"] = last_name
                
                with st.spinner("🎬 Creating your CineFlow account..."):
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.03)  # Longer for better UX
                        progress_bar.progress(i + 1)
                    
                    st.info(f"🔍 **Sending to:** `/authentication/auth/register/`")
                    with st.expander("📋 Registration Data", expanded=False):
                        safe_data = registration_data.copy()
                        safe_data["password"] = "***HIDDEN***"
                        safe_data["password_confirm"] = "***HIDDEN***"
                        st.json(safe_data)
                    
                    # Make the request with longer timeout
                    start_time = time.time()
                    response = make_api_request(
                        "/authentication/auth/register/",
                        method="POST",
                        data=registration_data,
                        auth_required=False,
                        timeout=45  # Longer timeout for Render
                    )
                    end_time = time.time()
                    
                    duration = end_time - start_time
                    st.info(f"⏱️ **Request took:** {duration:.2f} seconds")
                    
                    if response is not None:
                        st.info(f"📊 **HTTP Status:** {response.status_code}")
                        
                        # PROPERLY HANDLE 201 CREATED (your backend's correct response)
                        if response.status_code == 201:  # ← THIS IS THE KEY FIX
                            st.success("🎉 Account created successfully!")
                            
                            try:
                                response_data = response.json()
                                st.markdown("**📄 Registration Response:**")
                                
                                # Extract user data and tokens from your Django response
                                user_data = response_data.get('user', {})
                                access_token = response_data.get('access_token')
                                refresh_token = response_data.get('refresh_token')
                                message = response_data.get('message', '')
                                
                                # Show success details
                                username_display = user_data.get('username', username)
                                email_display = user_data.get('email', email)
                                
                                st.info(f"✅ Welcome {username_display}! ({email_display})")
                                if message:
                                    st.info(f"📧 {message}")
                                
                                # Auto-login the user with tokens
                                if access_token:
                                    st.session_state.authenticated = True
                                    st.session_state.token = access_token
                                    st.session_state.refresh_token = refresh_token
                                    st.session_state.user_info = user_data
                                    
                                    st.success("🔐 **Automatically logged in!**")
                                    st.balloons()
                                    
                                    # Optional: Show what's next
                                    st.markdown("""
                                    ### 🎯 **You're all set!**
                                    - ✅ Account created
                                    - ✅ Automatically logged in  
                                    - ✅ Welcome email sent
                                    - 🎬 Ready to discover movies!
                                    """)
                                    
                                    time.sleep(3)
                                    st.rerun()
                                else:
                                    st.warning("⚠️ Account created but no tokens received. Please sign in manually.")
                                    
                            except Exception as e:
                                st.warning(f"Account created but couldn't parse response: {e}")
                                st.code(response.text)
                                st.info("✅ **Account was created successfully!** Try signing in now.")
                            
                        elif response.status_code == 200:
                            # Some backends return 200 instead of 201
                            st.success("🎉 Account created successfully!")
                            try:
                                response_data = response.json()
                                st.json(response_data)
                            except:
                                st.code(response.text)
                                
                        elif response.status_code == 400:
                            # Validation errors from your Django view
                            st.error("❌ Registration failed - Validation errors:")
                            try:
                                error_data = response.json()
                                
                                # Handle your Django error response format
                                if 'details' in error_data:
                                    # Your Django view returns errors in 'details'
                                    for field, errors in error_data['details'].items():
                                        if isinstance(errors, list):
                                            for error in errors:
                                                st.error(f"**{field}**: {error}")
                                        else:
                                            st.error(f"**{field}**: {errors}")
                                elif 'error' in error_data:
                                    st.error(f"**Error**: {error_data['error']}")
                                else:
                                    st.json(error_data)
                                    
                            except Exception as e:
                                st.error(f"Registration failed: {response.text}")
                                
                        elif response.status_code == 500:
                            st.error("❌ Server error during registration")
                            try:
                                error_data = response.json()
                                if 'error' in error_data:
                                    st.error(f"**Server Error**: {error_data['error']}")
                                else:
                                    st.json(error_data)
                            except:
                                st.error("Internal server error occurred")
                                
                        else:
                            st.warning(f"🤔 Unexpected status code: {response.status_code}")
                            st.code(response.text)
                            
                            # Check if user was created anyway
                            st.info("🔍 **User might have been created anyway. Check Django admin or try logging in.**")
                    
                    else:
                        st.error("❌ No response received from server")
                        
                        # Comprehensive troubleshooting
                        st.markdown("""
                        ### 🔧 **Troubleshooting Steps:**
                        
                        1. **Check if user was created anyway:**
                           - Visit Django admin: `{}/admin/auth/user/`
                           - Look for username: `{}`
                           - Sometimes user is created but response times out
                        
                        2. **CORS Issues:**
                           - Open browser console (F12)
                           - Look for CORS errors
                           - Check if Django CORS settings allow your domain
                        
                        3. **Network/Render Issues:**
                           - Render free tier can be slow/unreliable
                           - Try waiting and registering again
                           - First request after sleep can take 60+ seconds
                        
                        4. **Try manual verification:**
                        """.format(config.api_base_url, username))
                        
                        # Manual check button
                        if st.button("🔍 **Check if User Exists**"):
                            st.info(f"**Manual Check:**")
                            st.markdown(f"1. Visit: {config.api_base_url}/admin/auth/user/")
                            st.markdown(f"2. Search for: `{username}`")
                            st.markdown(f"3. If found, try logging in")
                        
            else:
                if password != password_confirm:
                    st.error("❌ Passwords don't match!")
                else:
                    st.error("❌ Password must be at least 8 characters long!")
        else:
            missing = []
            if not username: missing.append("Username")
            if not email: missing.append("Email") 
            if not password: missing.append("Password")
            if not password_confirm: missing.append("Password confirmation")
            if not agree_terms: missing.append("Terms agreement")
            
            st.warning(f"⚠️ Please complete: {', '.join(missing)}")

def show_preferences_step():
    """This function is no longer needed - preferences will be set in user profile later"""
    pass

def show_enhanced_registration_form():
    """Simplified registration with just authentication"""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("### 🌟 Join CineFlow Community!")
        st.markdown("Create your account and start discovering amazing movies")
        
        # Single step registration - no progress indicator needed
        with st.form("register_form", clear_on_submit=False):
            show_basic_info_step()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Add a separate function for setting up movie preferences after login
def show_profile_setup_page():
    """Show this after successful login to set up movie preferences"""
    st.markdown("### 🎭 Complete Your Movie Profile")
    st.markdown("Help us personalize your experience!")
    
    # Movie preferences
    genre_options = [
        "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", 
        "Drama", "Family", "Fantasy", "History", "Horror", "Music", 
        "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western"
    ]
    
    with st.form("profile_setup_form"):
        favorite_genres = st.multiselect(
            "🎭 What genres do you enjoy?",
            genre_options,
            help="Select your favorite movie genres"
        )
        
        preferred_language = st.selectbox("🗣️ Preferred Language", 
            options=[
                ("en", "English"),
                ("es", "Spanish"), 
                ("fr", "French"),
                ("de", "German"),
                ("zh", "Chinese"),
                ("ja", "Japanese"),
                ("ru", "Russian"),
                ("it", "Italian"),
                ("pt", "Portuguese"),
                ("hi", "Hindi"),
                ("ar", "Arabic"),
                ("ko", "Korean")
            ],
            format_func=lambda x: x[1],
            index=0
        )
        
        bio = st.text_area("📝 Tell us about your movie taste", 
                          placeholder="I love sci-fi movies, especially those with time travel themes...")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("⏭️ **Skip for Now**", use_container_width=True):
                st.info("You can set up your preferences later in your profile!")
                st.session_state.profile_setup_complete = True
                st.rerun()
        
        with col2:
            if st.form_submit_button("✅ **Save Preferences**", use_container_width=True):
                # Save preferences via profile API endpoint
                profile_data = {
                    "favorite_genres": favorite_genres,
                    "preferred_language": preferred_language[0],
                    "bio": bio
                }
                
                # Use a profile update endpoint instead of registration
                response = make_api_request("/recommendations/v1/users/me/", 
                                         method="PATCH", data=profile_data)
                
                if response and response.status_code == 200:
                    st.success("✅ Profile preferences saved!")
                    st.session_state.profile_setup_complete = True
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("⚠️ Couldn't save preferences now, but you can set them later in your profile!")


def show_completion_step():
    """Step 3: Registration completion with onboarding"""
    st.markdown("### 🎉 Welcome to CineFlow!")
    
    st.markdown("""
    <div class="notification-card">
        <h3 style="margin-bottom: 1rem;">🎬 Your account is ready!</h3>
        <p style="margin-bottom: 0;">You can now sign in and start discovering amazing movies tailored just for you.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### 🚀 What's next?")
    
    next_steps = [
        ("🔐", "**Sign in** with your new credentials"),
        ("🎯", "**Get recommendations** based on your preferences"), 
        ("⭐", "**Rate movies** you've watched to improve suggestions"),
        ("🔍", "**Discover** new movies in our extensive catalog"),
        ("📊", "**Track** your viewing patterns and analytics")
    ]
    
    for icon, step in next_steps:
        st.markdown(f"""
        <div class="feature-card" style="margin: 0.5rem 0; padding: 1rem;">
            <div style="display: flex; align-items: center;">
                <span style="font-size: 1.5rem; margin-right: 1rem;">{icon}</span>
                <span>{step}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if st.form_submit_button("🔐 **Sign In Now**", use_container_width=True):
        st.session_state.registration_progress = 0
        st.session_state.registration_data = {}
        st.info("🔄 Switching to login form...")
        time.sleep(1)
        st.rerun()

def show_enhanced_preview_content():
    """Enhanced preview with FIXED movie card display"""
    
    # Fetch all preview data safely
    fetch_popular_movies()
    fetch_movie_stats()
    fetch_trending_movies()
    
    # Platform Statistics
    st.markdown("### 📊 Platform Overview")
    stats = st.session_state.movie_stats or {}
    
    # Create beautiful metrics grid using native Streamlit
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🎬 Movies",
            value=f"{stats.get('total_movies', 100):,}",
            delta="+5 this week"
        )
    
    with col2:
        st.metric(
            label="👥 Users", 
            value=f"{stats.get('total_users', 52):,}",
            delta="+23 today"
        )
    
    with col3:
        st.metric(
            label="⭐ Ratings",
            value=f"{stats.get('total_ratings', 15643):,}",
            delta="+156 today"
        )
    
    with col4:
        st.metric(
            label="🎯 Recommendations",
            value=f"{stats.get('total_recommendations', 48921):,}",
            delta="+1.2K today"
        )
    
    # Popular Movies Showcase with FIXED display
    st.markdown("### 🔥 Popular Movies Right Now")
    
    try:
        if st.session_state.popular_movies and isinstance(st.session_state.popular_movies, dict):
            movies = st.session_state.popular_movies.get('results', [])
            
            if movies and len(movies) > 0:
                # Display movies using FIXED function
                for movie in movies[:4]:  # Show first 4 movies
                    display_enhanced_movie_card(movie, show_interactions=False)
                    st.markdown("---")  # Separator
            else:
                st.info("🎬 Loading popular movies...")
        else:
            st.info("🎬 Loading popular movies...")
    except Exception as e:
        st.error(f"Error loading movies: {e}")
        st.info("🎬 Movies coming soon...")
    
    # Feature Highlights using native Streamlit
    st.markdown("### ✨ Why Choose CineFlow?")
    
    features = [
        ("🤖", "AI-Powered Recommendations", "Advanced machine learning algorithms analyze your preferences to suggest movies you'll love"),
        ("🔍", "Smart Discovery", "Explore movies by genre, mood, decade, or even specific themes with our intelligent search"),
        ("📊", "Personal Analytics", "Track your viewing habits, discover patterns, and see how your taste evolves over time"),
        ("⭐", "Community Ratings", "Join a community of movie enthusiasts and discover hidden gems through collective wisdom"),
    ]
    
    # Display features in columns
    for i in range(0, len(features), 2):
        col_left, col_right = st.columns(2)
        
        # Left feature
        if i < len(features):
            icon, title, desc = features[i]
            with col_left:
                st.markdown(f"### {icon} {title}")
                st.write(desc)
        
        # Right feature
        if i + 1 < len(features):
            icon, title, desc = features[i + 1]
            with col_right:
                st.markdown(f"### {icon} {title}")
                st.write(desc)
    
    # Final Call to Action
    st.markdown("---")
    st.markdown("### 🚀 Ready to Start Your Movie Journey?")
    st.markdown("""
    Join thousands of movie lovers and discover your next favorite film with AI-powered recommendations!
    
    ✨ **Free to join** • 🎬 **Instant recommendations** • 🔍 **Advanced search** • 📊 **Personal analytics**
    """)

def display_enhanced_movie_card(movie, show_interactions=True):
    """Display a beautiful, interactive movie card - FIXED VERSION"""
    
    # Safely get movie data
    title = movie.get('title', 'Unknown Title')
    rating = movie.get('tmdb_rating', 0)
    release_date = movie.get('release_date', 'Unknown')
    overview = movie.get('overview', 'No description available')
    popularity_score = movie.get('popularity_score', 0)
    views = movie.get('views', 0)
    like_count = movie.get('like_count', 0)
    poster_path = movie.get('poster_path')
    
    # Create stars display
    stars_filled = int(rating) if rating else 0
    stars_display = "⭐" * min(stars_filled, 5)  # Max 5 stars for display
    
    # Create poster display
    if poster_path:
        poster_url = f"https://image.tmdb.org/t/p/w300{poster_path}"
        poster_html = f'<img src="{poster_url}" style="width: 120px; height: 180px; object-fit: cover; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'
    else:
        poster_html = '''
        <div style="width: 120px; height: 180px; background: linear-gradient(45deg, #667eea, #764ba2); 
                    border-radius: 12px; display: flex; align-items: center; justify-content: center; 
                    color: white; font-size: 2.5rem;">🎬</div>
        '''
    
    # Truncate overview
    overview_truncated = overview[:150] + "..." if len(overview) > 150 else overview
    
    # Create the movie card using st.container and st.columns for better layout
    with st.container():
        # Use native Streamlit components instead of raw HTML
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Display poster using HTML component
            st.markdown(poster_html, unsafe_allow_html=True)
        
        with col2:
            # Use Streamlit native components for text
            st.markdown(f"### {title}")
            
            # Rating display
            rating_col1, rating_col2 = st.columns([1, 2])
            with rating_col1:
                st.markdown(f"**{stars_display}**")
            with rating_col2:
                st.markdown(f"**{rating}/10**")
            
            # Movie info
            info_text = f"""
            📅 **Release:** {release_date}  
            🔥 **Popularity:** {popularity_score:.1f}  
            👁️ **Views:** {views:,}  
            ❤️ **Likes:** {like_count:,}
            """
            st.markdown(info_text)
            
            # Overview
            st.markdown(f"**📝 Overview:**")
            st.write(overview_truncated)
            
            # Genres (if available)
            genres = movie.get('genres', [])
            if genres:
                genre_tags = " ".join([f"`{genre}`" for genre in genres[:3]])
                st.markdown(f"**🎭 Genres:** {genre_tags}")
        
        # Interactive buttons for authenticated users
        if show_interactions and st.session_state.get('authenticated', False):
            st.markdown("---")
            button_cols = st.columns(4)
            
            movie_id = movie.get('id')
            
            with button_cols[0]:
                if st.button("⭐ Rate", key=f"rate_{movie_id}", help="Rate this movie"):
                    show_rating_modal(movie)
            
            with button_cols[1]:
                if st.button("👁️ View", key=f"view_{movie_id}", help="Mark as viewed"):
                    increment_movie_views(movie_id)
            
            with button_cols[2]:
                if st.button("❤️ Like", key=f"like_{movie_id}", help="Like this movie"):
                    increment_movie_likes(movie_id)
            
            with button_cols[3]:
                if st.button("ℹ️ Details", key=f"details_{movie_id}", help="View full details"):
                    show_movie_details(movie)
        
        # Add some spacing
        st.markdown("<br>", unsafe_allow_html=True)

def calculate_password_strength(password):
    """Calculate password strength (0-2)"""
    score = 0
    if len(password) >= 8:
        score += 1
    if any(c.isdigit() for c in password) and any(c.isalpha() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1
    return min(score, 2)

# Enhanced Sidebar
def show_enhanced_sidebar():
    """Enhanced sidebar with guaranteed string return"""
    with st.sidebar:
        # Beautiful header
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0 1rem 0;">
            <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">🎬</div>
            <h2 style="margin: 0; color: #2d3748; font-weight: 800;">CineFlow</h2>
            <p style="margin: 0.3rem 0 0 0; color: #667eea; font-size: 0.9rem; font-weight: 500;">AI Movie Companion</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Enhanced connection status
        show_enhanced_connection_status()
        
        st.markdown("---")
        
        # User section or preview
        if st.session_state.get('authenticated', False):
            return show_authenticated_sidebar()
        else:
            show_preview_sidebar()
            return "🔐 Authentication"  # Always return a string


def show_enhanced_connection_status():
    """Enhanced connection status with detailed information"""
    status = st.session_state.get('backend_status', 'checking')
    env = st.session_state.get('api_environment', 'unknown')
    
    if status == "connected":
        env_info = {
            "production": ("🌐", "Production", "Render Cloud"),
            "local": ("🛠️", "Local", "Docker Container")
        }
        icon, env_type, desc = env_info.get(env, ("❓", "Unknown", "Unknown"))
        
        st.markdown(f"""
        <div class="connection-status status-connected">
            <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                <span>{icon}</span>
                <div>
                    <div style="font-weight: bold;">✅ Connected</div>
                    <div style="font-size: 0.8rem; opacity: 0.9;">{env_type} • {desc}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show API endpoint
        st.markdown(f"**Endpoint:** `{config.api_base_url}`", help="Current backend URL")
        
    elif status == "connection_error":
        st.markdown(f"""
        <div class="connection-status status-error">
            <div style="font-weight: bold;">❌ Connection Failed</div>
            <div style="font-size: 0.8rem; opacity: 0.9;">Backend unreachable</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 **Retry Connection**", use_container_width=True):
            st.session_state.backend_status = None
            with st.spinner("Reconnecting..."):
                time.sleep(1)
                check_backend_health()
            st.rerun()
            
        if st.button("🎭 **Demo Mode**", use_container_width=True):
            st.session_state.demo_mode = True
            st.session_state.backend_status = "demo"
            st.rerun()
            
    else:
        st.markdown(f"""
        <div class="connection-status status-checking">
            <div style="font-weight: bold;">🔍 Checking Connection...</div>
            <div style="font-size: 0.8rem; opacity: 0.9;">Please wait</div>
        </div>
        """, unsafe_allow_html=True)

def show_authenticated_sidebar():
    """Enhanced sidebar for authenticated users - FIXED VERSION"""
    
    try:
        # Fetch user profile safely
        fetch_user_profile()
        fetch_user_notifications()
        
        # Safe access to user info
        user_info = st.session_state.get('user_info', {})
        user = user_info.get('username', 'User') if user_info else 'User'
        profile = st.session_state.get('user_profile', {}) or {}
        
        # User welcome card
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 15px; text-align: center; margin-bottom: 1rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">👤</div>
            <div style="font-weight: bold; font-size: 1.1rem; margin-bottom: 0.3rem;">Welcome back!</div>
            <div style="opacity: 0.9;">{user}</div>
            <div style="font-size: 0.8rem; opacity: 0.8; margin-top: 0.5rem;">
                🎬 {profile.get('movies_rated', 0)} rated • 🎯 {profile.get('recommendations_received', 0)} recommendations
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick stats
        if profile:
            st.markdown("**🔥 Your Activity**")
            activity_data = [
                ("⭐", "Movies Rated", profile.get('movies_rated', 0)),
                ("👁️", "Movies Viewed", profile.get('movies_viewed', 0)),
                ("🎯", "Recommendations", profile.get('recommendations_received', 0))
            ]
            
            for icon, label, value in activity_data:
                st.markdown(f"""
                <div style="display: flex; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #e2e8f0;">
                    <span style="font-size: 1.3rem; margin-right: 0.8rem;">{icon}</span>
                    <div style="flex: 1;">
                        <div style="font-size: 0.8rem; color: #666;">{label}</div>
                        <div style="font-weight: bold; color: #2d3748;">{value}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # FIXED: Safe notifications handling
        notifications_data = st.session_state.get('notifications')
        if notifications_data and isinstance(notifications_data, dict):
            notifications = notifications_data.get('results', [])
            if notifications and len(notifications) > 0:
                st.markdown("**🔔 Recent Notifications**")
                for notif in notifications[:2]:
                    title = notif.get('title', 'Notification')
                    created_at = notif.get('created_at', '')[:10]
                    st.markdown(f"""
                    <div style="background: #fef3c7; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0; border-left: 3px solid #f59e0b;">
                        <div style="font-size: 0.85rem; font-weight: 500;">{title}</div>
                        <div style="font-size: 0.75rem; color: #666; margin-top: 0.2rem;">{created_at}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Logout button
        st.markdown("---")
        if st.button("🚪 **Sign Out**", use_container_width=True):
            logout()
        
        st.markdown("---")
        
        # Navigation menu with default selection
        nav_options = [
            ("🏠", "Dashboard"),
            ("🎬", "Movies"),
            ("🎯", "Recommendations"),
            ("📊", "Analytics"),
            ("👤", "Profile"),
            ("🔔", "Notifications")
        ]
        
        # FIXED: Always provide a default and ensure string return
        selected = st.selectbox(
            "📍 **Navigate to:**",
            [f"{icon} {label}" for icon, label in nav_options],
            index=0,  # Default to first option (Dashboard)
            format_func=lambda x: x
        )
        
        # Ensure we always return a string
        return selected if selected else "🏠 Dashboard"
        
    except Exception as e:
        # If anything fails in the sidebar, return a safe default
        st.error(f"Sidebar error: {str(e)}")
        return "🏠 Dashboard"
    

def show_preview_sidebar():
    """Enhanced sidebar preview for anonymous users"""
    # Platform stats
    fetch_movie_stats()
    stats = st.session_state.movie_stats or {}
    
    st.markdown("### 📊 **Live Stats**")
    
    stats_to_show = [
        ("🎬", "Movies", stats.get('total_movies', 100)),
        ("👥", "Users", stats.get('total_users', 1247)),
        ("⭐", "Ratings", stats.get('total_ratings', 15643)),
        ("🎯", "AI Recommendations", stats.get('total_recommendations', 48921))
    ]
    
    for icon, label, value in stats_to_show:
        st.markdown(f"""
        <div class="metric-card" style="margin: 0.5rem 0; padding: 1rem;">
            <div style="font-size: 1.8rem; margin-bottom: 0.3rem;">{icon}</div>
            <div style="font-weight: bold; color: #667eea; font-size: 1.2rem;">{value:,}</div>
            <div style="font-size: 0.8rem; color: #666;">{label}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Latest movie preview with null check
    fetch_popular_movies()
    if st.session_state.popular_movies and isinstance(st.session_state.popular_movies, dict):
        movies = st.session_state.popular_movies.get('results', [])
        if movies and len(movies) > 0:
            latest = movies[0]
            st.markdown("### 🔥 **Trending Now**")
            st.markdown(f"""
            <div style="background: white; padding: 1rem; border-radius: 12px; border: 1px solid #e2e8f0;">
                <div style="font-weight: bold; margin-bottom: 0.5rem; color: #2d3748;">{latest.get('title', 'Unknown')}</div>
                <div style="font-size: 0.8rem; color: #666; margin-bottom: 0.3rem;">⭐ {latest.get('tmdb_rating', 0)}/10</div>
                <div style="font-size: 0.8rem; color: #666;">📅 {latest.get('release_date', 'Unknown')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("### 🔥 **Featured**")
            st.markdown("""
            <div style="background: white; padding: 1rem; border-radius: 12px; border: 1px solid #e2e8f0;">
                <div style="font-weight: bold; margin-bottom: 0.5rem; color: #2d3748;">Spider-Man: No Way Home</div>
                <div style="font-size: 0.8rem; color: #666; margin-bottom: 0.3rem;">⭐ 7.9/10</div>
                <div style="font-size: 0.8rem; color: #666;">📅 2021</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("### 🔥 **Featured**")
        st.markdown("""
        <div style="background: white; padding: 1rem; border-radius: 12px; border: 1px solid #e2e8f0;">
            <div style="font-weight: bold; margin-bottom: 0.5rem; color: #2d3748;">Welcome to CineFlow</div>
            <div style="font-size: 0.8rem; color: #666;">🎬 Discover amazing movies</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Call to action
    st.markdown("""
    <div class="hero-section" style="padding: 1.5rem; margin: 1rem 0; font-size: 0.9rem;">
        <div style="font-weight: bold; margin-bottom: 0.8rem;">🚀 Join CineFlow</div>
        <div style="opacity: 0.9; line-height: 1.4;">Unlock AI-powered recommendations, track your viewing history, and discover your next favorite movie!</div>
    </div>
    """, unsafe_allow_html=True)

# Enhanced Main Pages
def show_enhanced_dashboard():
    """Comprehensive dashboard with all API integrations"""
    st.markdown('<h2 style="color: #2d3748; font-weight: 700; font-size: 2.5rem; margin-bottom: 2rem;">🏠 Your CineFlow Dashboard</h2>', unsafe_allow_html=True)
    
    # Fetch all dashboard data
    fetch_user_profile()
    fetch_user_recommendations()
    fetch_user_notifications()
    
    user = st.session_state.user_info.get('username', 'User')
    profile = st.session_state.user_profile or {}
    
    # Welcome section
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
        <h3 style="margin-bottom: 1rem; font-size: 2rem;">Welcome back, {user}! 🎬</h3>
        <p style="opacity: 0.95; font-size: 1.1rem;">Ready to discover your next favorite movie?</p>
    </div>
    """, unsafe_allow_html=True)
    
    # User metrics
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = [
        ("🎬", "Movies Rated", profile.get('movies_rated', 0), "+2"),
        ("👁️", "Movies Viewed", profile.get('movies_viewed', 0), "+5"),
        ("🎯", "Recommendations", profile.get('recommendations_received', 0), "+12"),
        ("⭐", "Avg Rating", f"{profile.get('average_rating', 7.2):.1f}", "")
    ]
    
    for i, (icon, label, value, delta) in enumerate(metrics):
        with [col1, col2, col3, col4][i]:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 2.5rem; margin-bottom: 0.8rem;">{icon}</div>
                <div style="font-size: 2rem; font-weight: bold; color: #667eea; margin-bottom: 0.3rem;">{value}</div>
                <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;">{label}</div>
                {f'<div style="font-size: 0.8rem; color: #10b981; font-weight: 500;">📈 {delta}</div>' if delta else ''}
            </div>
            """, unsafe_allow_html=True)
    
    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    
    action_cols = st.columns(3)
    
    with action_cols[0]:
        if st.button("🎯 **Get Fresh Recommendations**", use_container_width=True, help="Generate new personalized recommendations"):
            with st.spinner("🤖 AI is analyzing your preferences..."):
                response = make_api_request("/recommendations/v1/utils/generate_recommendations/", method="POST")
                if response and response.status_code == 200:
                    st.success("✅ Fresh recommendations generated!")
                    st.session_state.user_recommendations = None  # Clear cache
                    st.balloons()
                else:
                    st.error("❌ Failed to generate recommendations")
    
    with action_cols[1]:
        if st.button("🔍 **Discover Movies**", use_container_width=True, help="Explore our movie catalog"):
            st.session_state.page_redirect = "🎬 Movies"
            st.info("🔄 Redirecting to movie discovery...")
            time.sleep(1)
            st.rerun()
            
    with action_cols[2]:
        if st.button("📊 **View Analytics**", use_container_width=True, help="See your viewing patterns"):
            st.session_state.page_redirect = "📊 Analytics"
            st.info("🔄 Loading your analytics...")
            time.sleep(1)
            st.rerun()
    
    # Personalized Recommendations Section
    st.markdown("### 🎯 Your Personalized Recommendations")
    
    if st.session_state.user_recommendations:
        recommendations = st.session_state.user_recommendations.get('results', [])
        if recommendations:
            for rec in recommendations[:3]:
                movie = rec.get('movie', {})
                score = rec.get('recommendation_score', 0)
                
                st.markdown(f"""
                <div class="recommendation-card">
                    <h4 style="margin-bottom: 0.8rem;">🎬 {movie.get('title', 'Unknown Movie')}</h4>
                    <div style="margin-bottom: 0.5rem;">
                        <span style="background: #667eea; color: white; padding: 0.2rem 0.8rem; border-radius: 15px; font-size: 0.8rem;">
                            🎯 Match: {score*100:.0f}%
                        </span>
                    </div>
                    <p style="margin: 0.8rem 0; color: #666; line-height: 1.4;">
                        {movie.get('overview', 'No description available')[:120]}...
                    </p>
                    <div style="font-size: 0.85rem; color: #666;">
                        ⭐ {movie.get('tmdb_rating', 0)}/10 • 📅 {movie.get('release_date', 'Unknown')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("🎯 No recommendations yet. Rate some movies to get personalized suggestions!")
    else:
        st.info("🎯 Loading your recommendations...")
    
    # Recent Activity Chart
    st.markdown("### 📈 Your Activity Trends")
    
    # Mock activity data - replace with real API data
    activity_data = pd.DataFrame({
        'Date': pd.date_range('2024-01-01', periods=30, freq='D'),
        'Movies Rated': [max(0, int(2 + 1.5 * (i % 7 - 3.5) + (i % 3))) for i in range(30)],
        'Time Spent (minutes)': [max(0, int(45 + 30 * (i % 5 - 2) + (i % 4))) for i in range(30)]
    })
    
    # Create interactive Plotly chart
    fig = px.line(activity_data, x='Date', y=['Movies Rated', 'Time Spent (minutes)'], 
                  title="Your Movie Activity Over Time",
                  color_discrete_map={'Movies Rated': '#667eea', 'Time Spent (minutes)': '#764ba2'})
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title_font_color='#2d3748',
        title_font_size=16,
        title_font_family='Inter'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent Notifications
    if st.session_state.notifications:
        notifications = st.session_state.notifications.get('results', [])
        if notifications:
            st.markdown("### 🔔 Recent Notifications")
            
            for notif in notifications[:3]:
                st.markdown(f"""
                <div class="notification-card">
                    <h5 style="margin-bottom: 0.5rem;">{notif.get('title', 'Notification')}</h5>
                    <p style="margin: 0; color: #666; font-size: 0.9rem;">{notif.get('message', 'No message')}</p>
                    <div style="font-size: 0.75rem; color: #999; margin-top: 0.5rem;">
                        📅 {notif.get('created_at', '')[:10]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

# Movie interaction functions
def increment_movie_views(movie_id):
    """Increment movie views using API"""
    response = make_api_request(f"/movies/api/v1/movies/{movie_id}/increment_views/", method="POST")
    if response and response.status_code == 200:
        st.success("👁️ Marked as viewed!")
    else:
        st.error("❌ Failed to update views")

def increment_movie_likes(movie_id):
    """Increment movie likes using API"""
    response = make_api_request(f"/movies/api/v1/movies/{movie_id}/increment_likes/", method="POST")
    if response and response.status_code == 200:
        st.success("❤️ Liked!")
    else:
        st.error("❌ Failed to update likes")

def show_rating_modal(movie):
    """Show rating interface"""
    st.markdown(f"### ⭐ Rate: {movie.get('title')}")
    rating = st.slider("Your rating", 1, 10, 5)
    if st.button(f"Submit Rating: {rating}/10"):
        # Create interaction using API
        interaction_data = {
            "movie": movie.get('id'),
            "interaction_type": "rating",
            "rating": rating
        }
        response = make_api_request("/recommendations/v1/interactions/", method="POST", data=interaction_data)
        if response and response.status_code in [200, 201]:
            st.success(f"✅ Rated {movie.get('title')} {rating}/10!")
        else:
            st.error("❌ Failed to submit rating")

def show_movie_details(movie):
    """Show detailed movie information"""
    st.markdown(f"### 🎬 {movie.get('title')}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if movie.get('poster_path'):
            st.image(f"https://image.tmdb.org/t/p/w500{movie['poster_path']}")
        else:
            st.markdown("🎬 No poster available")
    
    with col2:
        st.markdown(f"**⭐ Rating:** {movie.get('tmdb_rating', 'N/A')}/10")
        st.markdown(f"**📅 Release Date:** {movie.get('release_date', 'Unknown')}")
        st.markdown(f"**🔥 Popularity:** {movie.get('popularity_score', 'N/A')}")
        st.markdown(f"**👁️ Views:** {movie.get('views', 0):,}")
        st.markdown(f"**❤️ Likes:** {movie.get('like_count', 0):,}")
        
        if movie.get('overview'):
            st.markdown("**📝 Overview:**")
            st.write(movie['overview'])

# Main Application Flow
def main():
    """Enhanced main application entry point - FIXED VERSION"""
    # Initialize everything
    init_session_state()
    load_custom_css()
    
    # Check for page redirects
    page = None
    if hasattr(st.session_state, 'page_redirect'):
        page = st.session_state.page_redirect
        del st.session_state.page_redirect
    
    # Beautiful main header
    env_indicator = ""
    if st.session_state.get('api_environment') == "production":
        env_indicator = " 🌐"
    elif st.session_state.get('api_environment') == "local":
        env_indicator = " 🛠️"
    
    st.markdown(f'<h1 class="main-header">🎬 CineFlow{env_indicator}</h1>', unsafe_allow_html=True)
    
    # Check backend connectivity
    if not st.session_state.get('backend_status'):
        with st.spinner("🔍 Connecting to CineFlow servers..."):
            check_backend_health()
    
    # Show sidebar and get navigation choice
    if not page:
        try:
            page = show_enhanced_sidebar()
        except Exception as e:
            st.error(f"Sidebar error: {str(e)}")
            page = "🏠 Dashboard"  # Safe fallback
    
    # Handle demo mode or connection issues
    if st.session_state.get('backend_status') == "connection_error" and not st.session_state.get('demo_mode'):
        show_enhanced_connection_error()
        return
    
    # Route to appropriate page
    if not st.session_state.get('authenticated', False):
        show_authentication_page()
    else:
        # FIXED: Always pass a valid string to route_authenticated_pages
        if not page or not isinstance(page, str):
            page = "🏠 Dashboard"
        route_authenticated_pages(page)

def show_enhanced_connection_error():
    """Enhanced connection error page with better UX"""
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <div style="font-size: 5rem; margin-bottom: 2rem;">🔌</div>
        <h2 style="color: #ef4444; margin-bottom: 1rem; font-weight: 700;">Connection Issues</h2>
        <p style="color: #666; font-size: 1.2rem; margin-bottom: 3rem; line-height: 1.5;">
            We're having trouble connecting to the CineFlow servers.<br>
            This might be due to network issues or server maintenance.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🔧 **Detailed Troubleshooting**", expanded=True):
        st.markdown(f"""
        **🌐 Current Backend:** `{config.api_base_url}`
        
        **🔍 Environment:** {config.environment}
        
        **📋 Possible Solutions:**
        
        ### 🌐 Production (Render) Issues:
        - **Service Wake-up**: Render services sleep after inactivity and may take 30-60 seconds to wake up
        - **URL Check**: Verify `https://alx-project-nexus-y0c5.onrender.com` is accessible
        - **Status Page**: Check Render's status page for outages
        
        ### 🛠️ Local Docker Issues:
        - **Container Status**: `docker-compose ps` - check if containers are running
        - **Container Logs**: `docker-compose logs backend` - check for errors
        - **Port Access**: `curl http://127.0.0.1:8001/health/` - test direct access
        - **Service Restart**: `docker-compose restart backend`
        
        ### 🔄 General Troubleshooting:
        1. **Wait**: Give Render services time to wake up (30-60 seconds)
        2. **Refresh**: Try refreshing this page
        3. **Network**: Check your internet connection
        4. **Browser**: Try clearing browser cache
        """)
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 **Retry Connection**", use_container_width=True):
            st.session_state.backend_status = None
            st.session_state.connection_attempts = 0
            with st.spinner("🔍 Reconnecting..."):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.03)  # Longer for Render wake-up
                    progress_bar.progress(i + 1)
                check_backend_health()
            st.rerun()
    
    with col2:
        if st.button("🎭 **Demo Mode**", use_container_width=True):
            st.session_state.demo_mode = True
            st.session_state.backend_status = "demo"
            st.success("🎭 Demo mode activated! Exploring with sample data.")
            time.sleep(1)
            st.rerun()
    
    with col3:
        if st.button("🌐 **Force Production**", use_container_width=True):
            config.environment = "production"
            st.session_state.backend_status = None
            st.info("🌐 Forcing production mode...")
            time.sleep(1)
            st.rerun()


def route_authenticated_pages(page: str):
    """Route to appropriate authenticated pages - FIXED VERSION"""
    
    # Handle case where page might be None or not a string
    if not page or not isinstance(page, str):
        # Default to Dashboard if page is invalid
        page = "🏠 Dashboard"
    
    if "Dashboard" in page:
        show_enhanced_dashboard()
    elif "Movies" in page:
        show_movies_management_page()
    elif "Recommendations" in page:
        show_recommendations_page()
    elif "Analytics" in page:
        show_analytics_page()
    elif "Profile" in page:
        show_profile_page()
    elif "Notifications" in page:
        show_notifications_page()
    else:
        # Fallback to dashboard for any unrecognized page
        show_enhanced_dashboard()

# Additional page implementations
def show_movies_management_page():
    """Comprehensive movie management with all API features"""
    st.markdown('<h2 style="color: #2d3748; font-weight: 700; font-size: 2.5rem; margin-bottom: 2rem;">🎬 Movie Discovery & Management</h2>', unsafe_allow_html=True)
    
    # Tab navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 **Discover**", "📋 **All Movies**", "⭐ **My Ratings**", "🔥 **Trending**", "➕ **Add Movie**"])
    
    with tab1:
        show_movie_discovery()
    
    with tab2:
        show_all_movies()
    
    with tab3:
        show_my_ratings()
    
    with tab4:
        show_trending_movies()
    
    with tab5:
        show_add_movie_form()

def show_movie_discovery():
    """Advanced movie discovery with filters"""
    st.markdown("### 🔍 Discover Your Next Favorite Movie")
    
    # Advanced filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_query = st.text_input("🔍 Search movies...", placeholder="Enter title, actor, director...")
    
    with col2:
        # Fetch genres for filter
        fetch_genres()
        if st.session_state.genres:
            genre_options = ["All Genres"] + [genre.get('name') for genre in st.session_state.genres.get('results', [])]
        else:
            genre_options = ["All Genres", "Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance"]
        
        selected_genre = st.selectbox("🎭 Genre", genre_options)
    
    with col3:
        year_range = st.selectbox("📅 Year", ["All Years", "2024", "2023", "2022", "2021", "2020", "2010s", "2000s", "1990s", "Classic"])
    
    # Additional filters
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        min_rating = st.slider("⭐ Min Rating", 0.0, 10.0, 0.0, 0.1)
    
    with filter_col2:
        sort_by = st.selectbox("📊 Sort by", ["Popularity", "Rating", "Release Date", "Title", "Views"])
    
    with filter_col3:
        content_type = st.selectbox("🎬 Type", ["All", "Movies", "Popular", "Top Rated", "Recent"])
    
    with filter_col4:
        per_page = st.selectbox("📄 Per page", [12, 24, 48])
    
    # Search button
    if st.button("🔍 **Search Movies**", use_container_width=True) or search_query:
        # Build API endpoint based on filters
        if content_type == "Popular":
            endpoint = "/movies/api/v1/movies/popular/"
        elif content_type == "Top Rated":
            endpoint = "/movies/api/v1/movies/top_rated/"
        elif content_type == "Recent":
            endpoint = "/movies/api/v1/movies/recent/"
        else:
            endpoint = "/movies/api/v1/movies/"
        
        # Add query parameters
        params = []
        if search_query:
            endpoint = "/movies/api/v1/search/"
            params.append(f"q={search_query}")
        if selected_genre != "All Genres":
            params.append(f"genre={selected_genre}")
        if min_rating > 0:
            params.append(f"min_rating={min_rating}")
        
        query_string = "&".join(params)
        if query_string:
            endpoint += f"?{query_string}&limit={per_page}"
        else:
            endpoint += f"?limit={per_page}"
        
        with st.spinner("🔍 Searching movies..."):
            response = make_api_request(endpoint, auth_required=False)
            if response and response.status_code == 200:
                movies_data = response.json()
                movies = movies_data.get('results', [])
                total_count = movies_data.get('count', len(movies))
                
                if movies:
                    st.success(f"🎬 Found {total_count} movies")
                    
                    # Display movies in grid
                    for i in range(0, len(movies), 2):
                        cols = st.columns(2)
                        for j, col in enumerate(cols):
                            if i + j < len(movies):
                                movie = movies[i + j]
                                with col:
                                    display_enhanced_movie_card(movie, show_interactions=True)
                else:
                    st.info("🔍 No movies found matching your criteria. Try adjusting your filters.")
            else:
                st.error("❌ Failed to search movies. Please try again.")

def show_all_movies():
    """Display all movies with pagination"""
    st.markdown("### 📋 Complete Movie Collection")
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input("📄 Page", min_value=1, value=1)
        per_page = st.selectbox("Movies per page", [12, 24, 48], index=1)
    
    # Fetch movies
    with st.spinner("📚 Loading movies..."):
        response = make_api_request(f"/movies/api/v1/movies/?page={page}&limit={per_page}")
        if response and response.status_code == 200:
            data = response.json()
            movies = data.get('results', [])
            total_count = data.get('count', 0)
            total_pages = (total_count + per_page - 1) // per_page
            
            if movies:
                st.info(f"📊 Page {page} of {total_pages} • {total_count:,} total movies")
                
                # Display movies
                for i in range(0, len(movies), 2):
                    cols = st.columns(2)
                    for j, col in enumerate(cols):
                        if i + j < len(movies):
                            movie = movies[i + j]
                            with col:
                                display_enhanced_movie_card(movie, show_interactions=True)
            else:
                st.info("📭 No movies found.")
        else:
            st.error("❌ Failed to load movies.")

def show_my_ratings():
    """Show user's movie ratings"""
    st.markdown("### ⭐ Your Movie Ratings")
    
    # Fetch user interactions
    response = make_api_request("/recommendations/v1/interactions/my_interactions/")
    if response and response.status_code == 200:
        interactions_data = response.json()
        ratings = [i for i in interactions_data.get('results', []) if i.get('interaction_type') == 'rating']
        
        if ratings:
            st.success(f"⭐ You've rated {len(ratings)} movies")
            
            # Sort options
            sort_by = st.selectbox("📊 Sort by", ["Most Recent", "Highest Rated", "Lowest Rated", "Movie Title"])
            
            # Sort ratings
            if sort_by == "Most Recent":
                ratings.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            elif sort_by == "Highest Rated":
                ratings.sort(key=lambda x: x.get('rating', 0), reverse=True)
            elif sort_by == "Lowest Rated":
                ratings.sort(key=lambda x: x.get('rating', 0))
            elif sort_by == "Movie Title":
                ratings.sort(key=lambda x: x.get('movie', {}).get('title', ''))
            
            # Display ratings
            for rating in ratings:
                movie = rating.get('movie', {})
                user_rating = rating.get('rating', 0)
                created_at = rating.get('created_at', '')
                
                st.markdown(f"""
                <div class="movie-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin-bottom: 0.5rem;">{movie.get('title', 'Unknown Movie')}</h4>
                            <div style="margin-bottom: 0.5rem;">
                                <span class="rating-stars">{'⭐' * user_rating}{'☆' * (10 - user_rating)}</span>
                                <span style="margin-left: 0.5rem; font-weight: bold; color: #667eea;">{user_rating}/10</span>
                            </div>
                            <div style="font-size: 0.85rem; color: #666;">
                                📅 Rated on {created_at[:10]} • 🎬 TMDB: {movie.get('tmdb_rating', 'N/A')}/10
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <button style="background: #ef4444; color: white; border: none; padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer;">
                                🗑️ Remove
                            </button>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("⭐ You haven't rated any movies yet. Start rating to get better recommendations!")
            
            # Suggest popular movies to rate
            st.markdown("### 🎬 Popular movies to rate:")
            fetch_popular_movies()
            if st.session_state.popular_movies:
                movies = st.session_state.popular_movies.get('results', [])[:3]
                for movie in movies:
                    display_enhanced_movie_card(movie, show_interactions=True)
    else:
        st.error("❌ Failed to load your ratings.")

def show_trending_movies():
    """Show trending movies from analytics"""
    st.markdown("### 🔥 Trending Movies")
    
    # Fetch trending movies
    response = make_api_request("/analytics/api/v1/trending/", auth_required=False)
    if response and response.status_code == 200:
        trending_data = response.json()
        trending_movies = trending_data.get('results', [])
        
        if trending_movies:
            st.success(f"🔥 {len(trending_movies)} movies trending this week")
            
            # Display trending movies
            for i, movie in enumerate(trending_movies, 1):
                st.markdown(f"""
                <div class="recommendation-card">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <div style="font-size: 2rem; font-weight: bold; color: #667eea; min-width: 3rem;">#{i}</div>
                        <div style="flex: 1;">
                            <h4 style="margin-bottom: 0.5rem;">{movie.get('title', 'Unknown Movie')}</h4>
                            <div style="margin-bottom: 0.5rem;">
                                <span style="background: #ff6b6b; color: white; padding: 0.2rem 0.8rem; border-radius: 15px; font-size: 0.8rem;">
                                    🔥 Trending Score: {movie.get('trending_score', 0):.1f}
                                </span>
                            </div>
                            <div style="font-size: 0.85rem; color: #666;">
                                ⭐ {movie.get('tmdb_rating', 0)}/10 • 👁️ {movie.get('views', 0):,} views
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📊 No trending data available yet.")
    else:
        # Fallback to popular movies
        st.info("📊 Loading popular movies as trending fallback...")
        fetch_popular_movies()
        if st.session_state.popular_movies:
            movies = st.session_state.popular_movies.get('results', [])
            for movie in movies[:5]:
                display_enhanced_movie_card(movie, show_interactions=True)

def show_add_movie_form():
    """Add new movie using actual API"""
    st.markdown("### ➕ Add New Movie to Collection")
    
    with st.form("add_movie_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("🎬 Movie Title *", placeholder="Enter movie title")
            original_title = st.text_input("🎬 Original Title", placeholder="Original title (if different)")
            overview = st.text_area("📝 Overview *", placeholder="Movie description/plot summary", height=100)
            tagline = st.text_input("💭 Tagline", placeholder="Movie tagline or slogan")
            director = st.text_input("🎬 Director", placeholder="Director name")
        
        with col2:
            release_date = st.date_input("📅 Release Date *")
            tmdb_rating = st.number_input("⭐ TMDB Rating", 0.0, 10.0, 5.0, 0.1)
            popularity_score = st.number_input("📊 Popularity Score", 0.0, 100.0, 1.0, 0.1)
            original_language = st.selectbox("🌍 Language", ["en", "es", "fr", "de", "it", "ja", "ko", "zh"])
            adult = st.checkbox("🔞 Adult Content")
        
        # Additional fields
        st.markdown("**🎭 Additional Information**")
        main_cast = st.text_area("👥 Main Cast", placeholder="Enter main cast members, separated by commas")
        poster_path = st.text_input("🖼️ Poster URL", placeholder="URL to movie poster image")
        backdrop_path = st.text_input("🖼️ Backdrop URL", placeholder="URL to backdrop image")
        
        # Genre selection
        fetch_genres()
        if st.session_state.genres:
            available_genres = st.session_state.genres.get('results', [])
            genre_options = [f"{genre.get('name')}" for genre in available_genres]
            selected_genres = st.multiselect("🎭 Genres", genre_options)
        
        submitted = st.form_submit_button("➕ **Add Movie**", use_container_width=True)
        
        if submitted:
            if title and overview and release_date:
                movie_data = {
                    "title": title,
                    "original_title": original_title or title,
                    "overview": overview,
                    "tagline": tagline,
                    "release_date": release_date.isoformat(),
                    "director": director,
                    "main_cast": [name.strip() for name in main_cast.split(",") if name.strip()],
                    "tmdb_rating": tmdb_rating,
                    "popularity_score": popularity_score,
                    "poster_path": poster_path,
                    "backdrop_path": backdrop_path,
                    "adult": adult,
                    "original_language": original_language,
                    "views": 0,
                    "like_count": 0
                }
                
                with st.spinner("🎬 Adding movie to collection..."):
                    response = make_api_request("/movies/api/v1/movies/", method="POST", data=movie_data)
                    if response and response.status_code in [200, 201]:
                        st.success("✅ Movie added successfully!")
                        st.balloons()
                        
                        # Add genres if selected
                        if selected_genres and response.json().get('id'):
                            movie_id = response.json()['id']
                            for genre_name in selected_genres:
                                # This would require additional API endpoint for genre assignment
                                pass
                        
                    else:
                        st.error("❌ Failed to add movie. Please check your data.")
                        if response:
                            try:
                                error_data = response.json()
                                st.error(f"Error details: {error_data}")
                            except:
                                pass
            else:
                st.warning("⚠️ Please fill in all required fields (marked with *).")

def show_recommendations_page():
    """Comprehensive recommendations page with AI insights"""
    st.markdown('<h2 style="color: #2d3748; font-weight: 700; font-size: 2.5rem; margin-bottom: 2rem;">🎯 Your AI Recommendations</h2>', unsafe_allow_html=True)
    
    # Fetch user recommendations
    fetch_user_recommendations()
    
    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 **For You**", "🔮 **Generate New**", "📊 **Performance**", "⚙️ **Preferences**"])
    
    with tab1:
        show_personalized_recommendations()
    
    with tab2:
        show_recommendation_generator()
    
    with tab3:
        show_recommendation_performance()
    
    with tab4:
        show_recommendation_preferences()

def show_personalized_recommendations():
    """Show user's personalized recommendations"""
    st.markdown("### 🎯 Movies Picked Just For You")
    
    if st.session_state.user_recommendations:
        recommendations = st.session_state.user_recommendations.get('results', [])
        
        if recommendations:
            st.success(f"🎯 {len(recommendations)} personalized recommendations ready!")
            
            # Recommendation filters
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                min_score = st.slider("🎯 Minimum Match Score", 0.0, 1.0, 0.5, 0.1)
            with filter_col2:
                recommendation_type = st.selectbox("📊 Type", ["All", "Highly Recommended", "Similar to Liked", "New Discoveries"])
            
            # Filter recommendations
            filtered_recs = [r for r in recommendations if r.get('recommendation_score', 0) >= min_score]
            
            if filtered_recs:
                for rec in filtered_recs:
                    movie = rec.get('movie', {})
                    score = rec.get('recommendation_score', 0)
                    explanation = rec.get('explanation', 'Based on your viewing history and preferences')
                    
                    st.markdown(f"""
                    <div class="recommendation-card">
                        <div style="display: flex; gap: 1.5rem;">
                            <div style="flex-shrink: 0;">
                                {f'<img src="https://image.tmdb.org/t/p/w200{movie.get("poster_path")}" style="width: 100px; height: 150px; object-fit: cover; border-radius: 12px;">' if movie.get('poster_path') else '<div style="width: 100px; height: 150px; background: linear-gradient(45deg, #667eea, #764ba2); border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; font-size: 2rem;">🎬</div>'}
                            </div>
                            <div style="flex: 1;">
                                <h4 style="margin-bottom: 0.8rem; color: #2d3748;">{movie.get('title', 'Unknown Movie')}</h4>
                                <div style="margin-bottom: 0.8rem;">
                                    <span style="background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.9rem; font-weight: 600;">
                                        🎯 {score*100:.0f}% Match
                                    </span>
                                </div>
                                <p style="margin: 0.8rem 0; color: #666; line-height: 1.5;">
                                    {movie.get('overview', 'No description available')[:200]}{'...' if len(movie.get('overview', '')) > 200 else ''}
                                </p>
                                <div style="margin: 0.8rem 0; padding: 0.8rem; background: #f8fafc; border-radius: 8px; border-left: 4px solid #667eea;">
                                    <strong style="color: #667eea;">💡 Why we recommend this:</strong><br>
                                    <span style="color: #666; font-size: 0.9rem;">{explanation}</span>
                                </div>
                                <div style="font-size: 0.85rem; color: #666; margin-bottom: 1rem;">
                                    ⭐ {movie.get('tmdb_rating', 0)}/10 • 📅 {movie.get('release_date', 'Unknown')} • 🔥 {movie.get('popularity_score', 0):.1f}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Action buttons
                    button_cols = st.columns(4)
                    with button_cols[0]:
                        if st.button("⭐ Rate", key=f"rec_rate_{rec.get('id')}", help="Rate this movie"):
                            show_rating_modal(movie)
                    with button_cols[1]:
                        if st.button("👁️ Watch", key=f"rec_watch_{rec.get('id')}", help="Mark as watched"):
                            mark_recommendation_clicked(rec.get('id'))
                            increment_movie_views(movie.get('id'))
                    with button_cols[2]:
                        if st.button("👍 Like", key=f"rec_like_{rec.get('id')}", help="Like this recommendation"):
                            mark_recommendation_clicked(rec.get('id'))
                    with button_cols[3]:
                        if st.button("👎 Not Interested", key=f"rec_dislike_{rec.get('id')}", help="Hide similar recommendations"):
                            provide_recommendation_feedback(rec.get('id'), 'negative')
            else:
                st.info("🎯 No recommendations match your current filters. Try adjusting the match score.")
        else:
            st.info("🎯 No recommendations available yet. Rate some movies to get personalized suggestions!")
    else:
        with st.spinner("🎯 Loading your personalized recommendations..."):
            fetch_user_recommendations()
            if st.session_state.user_recommendations:
                st.rerun()
            else:
                st.info("🎯 No recommendations found. Try rating some movies first!")

def show_recommendation_generator():
    """Generate new recommendations"""
    st.markdown("### 🔮 Generate Fresh Recommendations")
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 2rem; border-radius: 15px; margin: 1rem 0;">
        <h4 style="margin-bottom: 1rem;">🤖 AI Recommendation Engine</h4>
        <p style="margin: 0; color: #666; line-height: 1.5;">
            Our AI analyzes your viewing history, ratings, and preferences to find movies you'll love.
            Generate fresh recommendations based on your latest activity!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Generation options
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🎛️ Recommendation Settings**")
        recommendation_count = st.slider("📊 Number of recommendations", 5, 50, 10)
        include_genres = st.multiselect("🎭 Focus on genres", 
            ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller", "Animation"])
        
    with col2:
        st.markdown("**🔧 Advanced Options**")
        min_year = st.number_input("📅 Minimum year", 1950, 2024, 2000)
        min_rating = st.slider("⭐ Minimum TMDB rating", 0.0, 10.0, 6.0, 0.1)
        include_unrated = st.checkbox("📋 Include movies I haven't rated", value=True)
    
    # Generate button
    if st.button("🚀 **Generate Recommendations**", use_container_width=True):
        with st.spinner("🤖 AI is analyzing your preferences and finding perfect matches..."):
            # Create progress bar for better UX
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            steps = [
                "🧠 Analyzing your viewing history...",
                "🎭 Processing genre preferences...", 
                "⭐ Evaluating rating patterns...",
                "🔍 Scanning movie database...",
                "🎯 Calculating match scores...",
                "✨ Finalizing recommendations..."
            ]
            
            for i, step in enumerate(steps):
                progress_text.text(step)
                time.sleep(0.5)
                progress_bar.progress((i + 1) * 16)
            
            # Call recommendation generation API
            generation_data = {
                "count": recommendation_count,
                "genres": include_genres,
                "min_year": min_year,
                "min_rating": min_rating,
                "include_unrated": include_unrated
            }
            
            response = make_api_request("/recommendations/v1/utils/generate_recommendations/", 
                                     method="POST", data=generation_data)
            
            if response and response.status_code == 200:
                st.success("✅ Fresh recommendations generated successfully!")
                st.balloons()
                
                # Clear cached recommendations to fetch new ones
                st.session_state.user_recommendations = None
                
                # Show generation results
                result = response.json()
                st.markdown(f"""
                <div class="notification-card">
                    <h4>🎯 Generation Complete!</h4>
                    <p>Generated {result.get('count', recommendation_count)} new recommendations based on your preferences.</p>
                    <p><strong>Processing time:</strong> {result.get('processing_time', 'N/A')} seconds</p>
                </div>
                """, unsafe_allow_html=True)
                
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ Failed to generate recommendations. Please try again.")

def show_recommendation_performance():
    """Show recommendation performance analytics"""
    st.markdown("### 📊 Recommendation Performance")
    
    # Fetch performance data
    response = make_api_request("/recommendations/v1/recommendations/performance/")
    if response and response.status_code == 200:
        performance_data = response.json()
        
        # Performance metrics
        col1, col2, col3, col4 = st.columns(4)
        
        metrics = [
            ("🎯", "Accuracy", f"{performance_data.get('accuracy', 85):.1f}%"),
            ("👍", "Like Rate", f"{performance_data.get('like_rate', 78):.1f}%"),
            ("👁️", "Click Rate", f"{performance_data.get('click_rate', 65):.1f}%"),
            ("⭐", "Avg Rating", f"{performance_data.get('avg_rating', 7.2):.1f}/10")
        ]
        
        for i, (icon, label, value) in enumerate(metrics):
            with [col1, col2, col3, col4][i]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #667eea;">{value}</div>
                    <div style="color: #666; font-size: 0.9rem;">{label}</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Performance chart
        st.markdown("### 📈 Performance Trends")
        
        # Create mock performance data (replace with real API data)
        performance_df = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'Accuracy': [85 + (i % 7 - 3) for i in range(30)],
            'Click Rate': [65 + (i % 5 - 2) for i in range(30)],
            'Like Rate': [78 + (i % 6 - 3) for i in range(30)]
        })
        
        fig = px.line(performance_df, x='Date', y=['Accuracy', 'Click Rate', 'Like Rate'],
                     title="Recommendation Performance Over Time",
                     color_discrete_map={'Accuracy': '#667eea', 'Click Rate': '#764ba2', 'Like Rate': '#fa709a'})
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            title_font_color='#2d3748'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent feedback
        if performance_data.get('recent_feedback'):
            st.markdown("### 💬 Recent Feedback")
            for feedback in performance_data['recent_feedback'][:5]:
                feedback_icon = "👍" if feedback.get('positive') else "👎"
                st.markdown(f"""
                <div style="padding: 1rem; background: white; border-radius: 10px; border-left: 4px solid {'#10b981' if feedback.get('positive') else '#ef4444'}; margin: 0.5rem 0;">
                    <strong>{feedback_icon} {feedback.get('movie_title', 'Unknown Movie')}</strong><br>
                    <span style="color: #666; font-size: 0.9rem;">{feedback.get('comment', 'No comment')}</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("📊 Performance data will be available after you interact with more recommendations.")

def show_recommendation_preferences():
    """Manage recommendation preferences"""
    st.markdown("### ⚙️ Recommendation Preferences")
    
    # Fetch user profile
    fetch_user_profile()
    profile = st.session_state.user_profile or {}
    
    with st.form("preferences_form"):
        st.markdown("**🎭 Genre Preferences**")
        
        # Fetch available genres
        fetch_genres()
        if st.session_state.genres:
            available_genres = [genre.get('name') for genre in st.session_state.genres.get('results', [])]
        else:
            available_genres = ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller", "Animation"]
        
        current_genres = profile.get('favorite_genres', [])
        selected_genres = st.multiselect("🎬 Favorite genres", available_genres, default=current_genres)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔧 Algorithm Settings**")
            diversity = st.slider("🌈 Recommendation diversity", 0.0, 1.0, 
                                profile.get('diversity_preference', 0.5), 0.1,
                                help="Higher values = more variety in recommendations")
            
            novelty = st.slider("🆕 Novelty preference", 0.0, 1.0, 
                               profile.get('novelty_preference', 0.7), 0.1,
                               help="Higher values = more unknown/new movies")
            
            exploration = st.slider("🔍 Exploration vs Exploitation", 0.0, 1.0, 
                                   profile.get('exploration_preference', 0.6), 0.1,
                                   help="Higher values = more experimental recommendations")
        
        with col2:
            st.markdown("**📊 Content Filters**")
            min_year = st.number_input("📅 Minimum year", 1950, 2024, 
                                     profile.get('min_year', 1990))
            
            max_year = st.number_input("📅 Maximum year", 1950, 2024, 
                                     profile.get('max_year', 2024))
            
            min_rating = st.slider("⭐ Minimum rating", 0.0, 10.0, 
                                 profile.get('min_rating', 5.0), 0.1)
            
            include_adult = st.checkbox("🔞 Include adult content", 
                                       profile.get('include_adult', False))
        
        st.markdown("**🎯 Recommendation Frequency**")
        notification_frequency = st.selectbox("🔔 Get new recommendations", 
            ["Daily", "Weekly", "Bi-weekly", "Monthly", "Manual only"],
            index=["Daily", "Weekly", "Bi-weekly", "Monthly", "Manual only"].index(
                profile.get('notification_frequency', 'Weekly')))
        
        max_recommendations = st.slider("📊 Max recommendations per batch", 5, 50, 
                                       profile.get('max_recommendations', 10))
        
        # Submit preferences
        if st.form_submit_button("💾 **Save Preferences**", use_container_width=True):
            preferences_data = {
                "favorite_genres": selected_genres,
                "diversity_preference": diversity,
                "novelty_preference": novelty,
                "exploration_preference": exploration,
                "min_year": min_year,
                "max_year": max_year,
                "min_rating": min_rating,
                "include_adult": include_adult,
                "notification_frequency": notification_frequency,
                "max_recommendations": max_recommendations
            }
            
            with st.spinner("💾 Saving your preferences..."):
                response = make_api_request("/recommendations/v1/users/update_preferences/", 
                                         method="PATCH", data=preferences_data)
                
                if response and response.status_code == 200:
                    st.success("✅ Preferences saved successfully!")
                    st.session_state.user_profile = None  # Clear cache
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to save preferences. Please try again.")

def show_analytics_page():
    """Comprehensive analytics dashboard"""
    st.markdown('<h2 style="color: #2d3748; font-weight: 700; font-size: 2.5rem; margin-bottom: 2rem;">📊 Your Movie Analytics</h2>', unsafe_allow_html=True)
    
    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs(["📈 **Overview**", "🎬 **Movie Stats**", "🎯 **Recommendations**", "📱 **Activity**"])
    
    with tab1:
        show_analytics_overview()
    
    with tab2:
        show_movie_analytics()
    
    with tab3:
        show_recommendation_analytics()
    
    with tab4:
        show_activity_analytics()

def show_analytics_overview():
    """Show overall analytics overview"""
    st.markdown("### 📊 Your CineFlow Journey")
    
    # Fetch analytics data
    response = make_api_request("/analytics/api/v1/activity-logs/analytics_summary/")
    if response and response.status_code == 200:
        analytics_data = response.json()
    else:
        # Mock analytics data
        analytics_data = {
            "total_movies_rated": 45,
            "total_watch_time": 8640,  # minutes
            "favorite_genres": ["Sci-Fi", "Drama", "Action"],
            "average_rating": 7.2,
            "recommendations_clicked": 23,
            "active_days": 45,
            "longest_streak": 12
        }
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = [
        ("🎬", "Movies Rated", analytics_data.get('total_movies_rated', 0)),
        ("⏱️", "Hours Watched", f"{analytics_data.get('total_watch_time', 0) // 60:.0f}h"),
        ("🎯", "Recommendations Used", analytics_data.get('recommendations_clicked', 0)),
        ("📅", "Active Days", analytics_data.get('active_days', 0))
    ]
    
    for i, (icon, label, value) in enumerate(metrics):
        with [col1, col2, col3, col4][i]:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 2.5rem; margin-bottom: 0.8rem;">{icon}</div>
                <div style="font-size: 2rem; font-weight: bold; color: #667eea;">{value}</div>
                <div style="color: #666; font-size: 0.9rem;">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Genre distribution
    st.markdown("### 🎭 Your Genre Preferences")
    
    favorite_genres = analytics_data.get('favorite_genres', [])
    if favorite_genres:
        # Create genre distribution chart
        genre_data = pd.DataFrame({
            'Genre': favorite_genres[:5],
            'Count': [20, 15, 12, 8, 5]  # Mock data - replace with real API data
        })
        
        fig = px.pie(genre_data, values='Count', names='Genre', 
                    title="Your Top 5 Genres",
                    color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            title_font_color='#2d3748'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Rating distribution
    st.markdown("### ⭐ Your Rating Patterns")
    
    # Mock rating distribution
    rating_data = pd.DataFrame({
        'Rating': list(range(1, 11)),
        'Count': [1, 2, 3, 5, 8, 12, 15, 18, 22, 14]  # Mock data
    })
    
    fig = px.bar(rating_data, x='Rating', y='Count',
                title="How You Rate Movies",
                color='Count',
                color_continuous_scale='Viridis')
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title_font_color='#2d3748',
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Insights
    avg_rating = analytics_data.get('average_rating', 7.2)
    st.markdown("### 💡 Personal Insights")
    
    insights = [
        f"🎯 Your average rating is {avg_rating:.1f}/10 - you're {'generous' if avg_rating > 7 else 'critical' if avg_rating < 6 else 'balanced'} with ratings!",
        f"🎭 You prefer {', '.join(favorite_genres[:2])} movies the most",
        f"📈 You've been active for {analytics_data.get('active_days', 0)} days with a {analytics_data.get('longest_streak', 0)}-day longest streak",
        f"🔍 You've clicked on {analytics_data.get('recommendations_clicked', 0)} recommendations - our AI is learning your taste!"
    ]
    
    for insight in insights:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); padding: 1rem; border-radius: 10px; margin: 0.5rem 0; border-left: 4px solid #ff6b6b;">
            {insight}
        </div>
        """, unsafe_allow_html=True)

def show_movie_analytics():
    """Show detailed movie analytics"""
    st.markdown("### 🎬 Movie Collection Analytics")
    
    # Fetch movie analytics
    response = make_api_request("/movies/api/v1/analytics/")
    if response and response.status_code == 200:
        movie_analytics = response.json()
    else:
        # Mock data
        movie_analytics = {
            "total_movies": 100,
            "genres_distribution": {"Action": 25, "Drama": 20, "Comedy": 18, "Sci-Fi": 15, "Horror": 12, "Romance": 10},
            "decade_distribution": {"2020s": 30, "2010s": 35, "2000s": 20, "1990s": 10, "1980s": 5},
            "rating_distribution": {"9-10": 15, "8-9": 25, "7-8": 30, "6-7": 20, "Below 6": 10},
            "top_rated_movies": [
                {"title": "The Dark Knight", "rating": 9.0},
                {"title": "Inception", "rating": 8.8},
                {"title": "Pulp Fiction", "rating": 8.9}
            ]
        }
    
    # Collection overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 Collection Size**")
        st.metric("Total Movies", movie_analytics.get('total_movies', 0))
        
    with col2:
        st.markdown("**🏆 Highest Rated**")
        top_movie = movie_analytics.get('top_rated_movies', [{}])[0]
        st.metric("Top Movie", top_movie.get('title', 'N/A')[:15] + "...", 
                 f"⭐ {top_movie.get('rating', 0)}")
    
    with col3:
        st.markdown("**🎭 Dominant Genre**")
        genres = movie_analytics.get('genres_distribution', {})
        top_genre = max(genres.keys(), key=lambda k: genres[k]) if genres else "N/A"
        st.metric("Top Genre", top_genre, f"{genres.get(top_genre, 0)} movies")
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Genre distribution
        if movie_analytics.get('genres_distribution'):
            genre_df = pd.DataFrame(list(movie_analytics['genres_distribution'].items()), 
                                  columns=['Genre', 'Count'])
            fig = px.bar(genre_df, x='Genre', y='Count', 
                        title="Movies by Genre",
                        color='Count',
                        color_continuous_scale='Blues')
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        # Decade distribution
        if movie_analytics.get('decade_distribution'):
            decade_df = pd.DataFrame(list(movie_analytics['decade_distribution'].items()), 
                                   columns=['Decade', 'Count'])
            fig = px.pie(decade_df, values='Count', names='Decade', 
                        title="Movies by Decade")
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

def show_recommendation_analytics():
    """Show recommendation-specific analytics"""
    st.markdown("### 🎯 Recommendation Analytics")
    
    # Fetch recommendation analytics
    response = make_api_request("/recommendations/v1/analytics/dashboard/")
    if response and response.status_code == 200:
        rec_analytics = response.json()
    else:
        # Mock data
        rec_analytics = {
            "total_recommendations": 150,
            "clicked_recommendations": 45,
            "accuracy_rate": 78.5,
            "user_satisfaction": 8.2,
            "algorithm_performance": {
                "collaborative_filtering": 82,
                "content_based": 75,
                "hybrid": 88
            }
        }
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    rec_metrics = [
        ("🎯", "Total Recommendations", rec_analytics.get('total_recommendations', 0)),
        ("👆", "Clicked", rec_analytics.get('clicked_recommendations', 0)),
        ("🎪", "Accuracy", f"{rec_analytics.get('accuracy_rate', 0):.1f}%"),
        ("😊", "Satisfaction", f"{rec_analytics.get('user_satisfaction', 0):.1f}/10")
    ]
    
    for i, (icon, label, value) in enumerate(rec_metrics):
        with [col1, col2, col3, col4][i]:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: #667eea;">{value}</div>
                <div style="color: #666; font-size: 0.85rem;">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Algorithm performance
    st.markdown("### 🤖 Algorithm Performance")
    
    if rec_analytics.get('algorithm_performance'):
        algo_data = rec_analytics['algorithm_performance']
        algo_df = pd.DataFrame(list(algo_data.items()), columns=['Algorithm', 'Performance'])
        
        fig = px.bar(algo_df, x='Algorithm', y='Performance',
                    title="Recommendation Algorithm Performance",
                    color='Performance',
                    color_continuous_scale='Viridis')
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            title_font_color='#2d3748'
        )
        st.plotly_chart(fig, use_container_width=True)

def show_activity_analytics():
    """Show user activity analytics"""
    st.markdown("### 📱 Activity Analytics")
    
    # Fetch activity logs
    response = make_api_request("/analytics/api/v1/activity-logs/sessions/")
    if response and response.status_code == 200:
        activity_data = response.json()
    else:
        # Mock activity data
        activity_data = {
            "daily_activity": [
                {"date": "2024-01-01", "sessions": 3, "duration": 45},
                {"date": "2024-01-02", "sessions": 2, "duration": 30},
                # ... more mock data
            ],
            "peak_hours": {"morning": 20, "afternoon": 45, "evening": 60, "night": 15},
            "device_usage": {"desktop": 70, "mobile": 25, "tablet": 5}
        }
    
    # Activity timeline
    st.markdown("### 📅 Activity Timeline")
    
    # Create mock activity timeline
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    activity_df = pd.DataFrame({
        'Date': dates,
        'Sessions': [2 + (i % 7) for i in range(30)],
        'Duration (minutes)': [30 + (i % 10) * 5 for i in range(30)]
    })
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(x=activity_df['Date'], y=activity_df['Sessions'], name="Sessions"),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(x=activity_df['Date'], y=activity_df['Duration (minutes)'], name="Duration"),
        secondary_y=True,
    )
    
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Sessions", secondary_y=False)
    fig.update_yaxes(title_text="Duration (minutes)", secondary_y=True)
    fig.update_layout(title_text="Daily Activity Over Time")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Usage patterns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🕐 Peak Usage Hours")
        if activity_data.get('peak_hours'):
            hours_df = pd.DataFrame(list(activity_data['peak_hours'].items()), 
                                  columns=['Time', 'Usage %'])
            fig = px.bar(hours_df, x='Time', y='Usage %',
                        title="When You Use CineFlow Most",
                        color='Usage %',
                        color_continuous_scale='Blues')
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📱 Device Usage")
        if activity_data.get('device_usage'):
            device_df = pd.DataFrame(list(activity_data['device_usage'].items()), 
                                   columns=['Device', 'Usage %'])
            fig = px.pie(device_df, values='Usage %', names='Device',
                        title="Your Preferred Devices")
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

def show_profile_page():
    """User profile management page"""
    st.markdown('<h2 style="color: #2d3748; font-weight: 700; font-size: 2.5rem; margin-bottom: 2rem;">👤 Your Profile</h2>', unsafe_allow_html=True)
    
    # Fetch user profile
    fetch_user_profile()
    profile = st.session_state.user_profile or {}
    
    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs(["👤 **Basic Info**", "🎭 **Preferences**", "🔒 **Security**", "📊 **Statistics**"])
    
    with tab1:
        show_basic_profile()
    
    with tab2:
        show_profile_preferences()
    
    with tab3:
        show_security_settings()
    
    with tab4:
        show_profile_statistics()

def show_basic_profile():
    """Show and edit basic profile information"""
    st.markdown("### 👤 Basic Information")
    
    profile = st.session_state.user_profile or {}
    user_info = st.session_state.user_info or {}
    
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("👤 Username", value=user_info.get('username', ''), disabled=True)
            first_name = st.text_input("👨 First Name", value=profile.get('first_name', ''))
            email = st.text_input("📧 Email", value=profile.get('email', ''))
            
        with col2:
            last_name = st.text_input("👩 Last Name", value=profile.get('last_name', ''))
            bio = st.text_area("📝 Bio", value=profile.get('bio', ''), 
                              placeholder="Tell us about your movie preferences...")
            location = st.text_input("📍 Location", value=profile.get('location', ''))
        
        # Profile preferences
        st.markdown("**🎬 Movie Preferences**")
        col3, col4 = st.columns(2)
        
        with col3:
            favorite_actor = st.text_input("⭐ Favorite Actor", value=profile.get('favorite_actor', ''))
            favorite_director = st.text_input("🎬 Favorite Director", value=profile.get('favorite_director', ''))
            
        with col4:
            favorite_decade = st.selectbox("📅 Favorite Decade", 
                ["2020s", "2010s", "2000s", "1990s", "1980s", "1970s", "1960s", "Classic"],
                index=0 if not profile.get('favorite_decade') else 
                ["2020s", "2010s", "2000s", "1990s", "1980s", "1970s", "1960s", "Classic"].index(profile.get('favorite_decade')))
            
            movie_mood = st.selectbox("🎭 Typical Movie Mood",
                ["Adventurous", "Relaxed", "Thoughtful", "Excited", "Romantic", "Thrilled"],
                index=0 if not profile.get('movie_mood') else 
                ["Adventurous", "Relaxed", "Thoughtful", "Excited", "Romantic", "Thrilled"].index(profile.get('movie_mood')))
        
        if st.form_submit_button("💾 **Update Profile**", use_container_width=True):
            profile_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "bio": bio,
                "location": location,
                "favorite_actor": favorite_actor,
                "favorite_director": favorite_director,
                "favorite_decade": favorite_decade,
                "movie_mood": movie_mood
            }
            
            with st.spinner("💾 Updating your profile..."):
                response = make_api_request("/recommendations/v1/users/me/", 
                                         method="PATCH", data=profile_data)
                
                if response and response.status_code == 200:
                    st.success("✅ Profile updated successfully!")
                    st.session_state.user_profile = None  # Clear cache
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to update profile. Please try again.")

def show_profile_preferences():
    """Show profile preferences"""
    st.markdown("### 🎭 Viewing Preferences")
    
    profile = st.session_state.user_profile or {}
    
    # This would integrate with the recommendation preferences
    st.info("🔗 Your viewing preferences are managed in the Recommendations section.")
    
    if st.button("🎯 **Go to Recommendation Preferences**", use_container_width=True):
        st.session_state.page_redirect = "🎯 Recommendations"
        st.rerun()

def show_security_settings():
    """Show security settings"""
    st.markdown("### 🔒 Security Settings")
    
    # Change password
    with st.form("change_password_form"):
        st.markdown("**🔐 Change Password**")
        
        current_password = st.text_input("🔒 Current Password", type="password")
        new_password = st.text_input("🔐 New Password", type="password")
        confirm_password = st.text_input("🔐 Confirm New Password", type="password")
        
        if st.form_submit_button("🔄 **Change Password**", use_container_width=True):
            if new_password == confirm_password and len(new_password) >= 8:
                password_data = {
                    "old_password": current_password,
                    "new_password": new_password
                }
                
                with st.spinner("🔐 Updating password..."):
                    # Note: This endpoint might need to be created in your backend
                    response = make_api_request("/authentication/auth/change-password/", 
                                             method="POST", data=password_data)
                    
                    if response and response.status_code == 200:
                        st.success("✅ Password changed successfully!")
                    else:
                        st.error("❌ Failed to change password. Check your current password.")
            else:
                if new_password != confirm_password:
                    st.error("❌ New passwords don't match!")
                else:
                    st.error("❌ Password must be at least 8 characters long!")
    
    # Account settings
    st.markdown("### ⚙️ Account Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 **Download My Data**", use_container_width=True):
            st.info("📊 Data export functionality coming soon!")
    
    with col2:
        if st.button("🗑️ **Delete Account**", use_container_width=True):
            st.warning("⚠️ Account deletion functionality available on request.")

def show_profile_statistics():
    """Show profile statistics"""
    st.markdown("### 📊 Your CineFlow Statistics")
    
    profile = st.session_state.user_profile or {}
    
    # User stats overview
    stats = [
        ("🎬", "Movies Rated", profile.get('movies_rated', 0)),
        ("👁️", "Movies Viewed", profile.get('movies_viewed', 0)),
        ("🎯", "Recommendations Received", profile.get('recommendations_received', 0)),
        ("📅", "Days Active", profile.get('days_active', 0)),
        ("⭐", "Average Rating Given", f"{profile.get('average_rating', 7.0):.1f}"),
        ("🏆", "Highest Rated Movie", profile.get('highest_rated_movie', 'N/A'))
    ]
    
    # Display stats in grid
    for i in range(0, len(stats), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(stats):
                icon, label, value = stats[i + j]
                with col:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                        <div style="font-size: 1.3rem; font-weight: bold; color: #667eea;">{value}</div>
                        <div style="color: #666; font-size: 0.85rem;">{label}</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Achievement badges (mock)
    st.markdown("### 🏆 Achievements")
    
    achievements = [
        ("🎬", "Movie Buff", "Rated 50+ movies"),
        ("⭐", "Critic", "Average rating precision"),
        ("🔍", "Explorer", "Tried diverse genres"),
        ("🎯", "Recommendation Master", "High recommendation accuracy"),
        ("📅", "Consistent Viewer", "30+ day streak")
    ]
    
    achievement_cols = st.columns(len(achievements))
    for i, (icon, title, desc) in enumerate(achievements):
        with achievement_cols[i]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%); padding: 1rem; border-radius: 15px; text-align: center; color: #333;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                <div style="font-weight: bold; margin-bottom: 0.3rem;">{title}</div>
                <div style="font-size: 0.8rem;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

def show_notifications_page():
    """Comprehensive notifications management"""
    st.markdown('<h2 style="color: #2d3748; font-weight: 700; font-size: 2.5rem; margin-bottom: 2rem;">🔔 Notifications</h2>', unsafe_allow_html=True)
    
    # Tab navigation
    tab1, tab2, tab3 = st.tabs(["📬 **Inbox**", "⚙️ **Preferences**", "📊 **History**"])
    
    with tab1:
        show_notification_inbox()
    
    with tab2:
        show_notification_preferences()
    
    with tab3:
        show_notification_history()

def show_notification_inbox():
    """Show notification inbox"""
    st.markdown("### 📬 Your Notifications")
    
    # Fetch notifications
    fetch_user_notifications()
    
    if st.session_state.notifications:
        notifications = st.session_state.notifications.get('results', [])
        
        if notifications:
            # Notification controls
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ **Mark All Read**", use_container_width=True):
                    response = make_api_request("/notifications/api/v1/inapp/mark_all_read/", method="POST")
                    if response and response.status_code == 200:
                        st.success("✅ All notifications marked as read!")
                        st.session_state.notifications = None
                        st.rerun()
            
            with col2:
                unread_count_response = make_api_request("/notifications/api/v1/inapp/unread_count/")
                if unread_count_response and unread_count_response.status_code == 200:
                    unread_count = unread_count_response.json().get('count', 0)
                    st.metric("📭 Unread", unread_count)
            
            with col3:
                if st.button("🗑️ **Clear Archive**", use_container_width=True):
                    response = make_api_request("/notifications/api/v1/inapp/clear_all/", method="DELETE")
                    if response and response.status_code == 200:
                        st.success("🗑️ Archive cleared!")
            
            # Display notifications
            for notif in notifications:
                is_read = notif.get('is_read', False)
                priority = notif.get('priority', 'normal')
                
                # Determine notification style based on priority and read status
                bg_color = "#f8fafc" if is_read else "#fff"
                border_color = {"high": "#ef4444", "medium": "#f59e0b", "normal": "#10b981"}.get(priority, "#10b981")
                
                st.markdown(f"""
                <div style="background: {bg_color}; padding: 1.5rem; border-radius: 12px; border-left: 4px solid {border_color}; margin: 1rem 0; {'opacity: 0.7;' if is_read else ''}">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                        <h4 style="margin: 0; color: #2d3748;">{notif.get('title', 'Notification')}</h4>
                        <span style="background: {border_color}; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem;">
                            {priority.upper()}
                        </span>
                    </div>
                    <p style="margin: 0.5rem 0; color: #666; line-height: 1.5;">{notif.get('message', 'No message')}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                        <small style="color: #999;">📅 {notif.get('created_at', '')[:16]}</small>
                        <div>
                            {'<span style="color: #10b981; font-weight: bold;">✅ Read</span>' if is_read else '<span style="color: #3b82f6; font-weight: bold;">📬 Unread</span>'}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Action buttons for unread notifications
                if not is_read:
                    button_cols = st.columns([1, 1, 4])
                    with button_cols[0]:
                        if st.button("✅ Read", key=f"read_{notif.get('id')}", help="Mark as read"):
                            response = make_api_request(f"/notifications/api/v1/inapp/{notif.get('id')}/mark_read/", method="POST")
                            if response and response.status_code == 200:
                                st.success("✅ Marked as read!")
                                st.rerun()
                    
                    with button_cols[1]:
                        if st.button("📁 Archive", key=f"archive_{notif.get('id')}", help="Archive notification"):
                            response = make_api_request(f"/notifications/api/v1/inapp/{notif.get('id')}/archive/", method="POST")
                            if response and response.status_code == 200:
                                st.success("📁 Archived!")
                                st.rerun()
        else:
            st.info("📭 No notifications yet. You'll receive updates about new recommendations, movie suggestions, and platform updates here!")
    else:
        st.info("📡 Loading notifications...")

def show_notification_preferences():
    """Show notification preferences"""
    st.markdown("### ⚙️ Notification Preferences")
    
    # Fetch current preferences
    response = make_api_request("/notifications/api/v1/preferences/my_preferences/")
    if response and response.status_code == 200:
        preferences = response.json()
    else:
        # Default preferences
        preferences = {
            "email_notifications": True,
            "push_notifications": True,
            "recommendation_notifications": True,
            "movie_update_notifications": True,
            "weekly_digest": True,
            "marketing_notifications": False
        }
    
    with st.form("notification_preferences_form"):
        st.markdown("**📧 Email Notifications**")
        
        email_enabled = st.checkbox("📧 Enable email notifications", 
                                   value=preferences.get('email_notifications', True))
        
        if email_enabled:
            email_options = [
                ("🎯", "New recommendations", "recommendation_notifications"),
                ("🎬", "Movie updates", "movie_update_notifications"),
                ("📊", "Weekly digest", "weekly_digest"),
                ("🛍️", "Promotional content", "marketing_notifications")
            ]
            
            email_prefs = {}
            for icon, label, key in email_options:
                email_prefs[key] = st.checkbox(f"{icon} {label}", 
                                             value=preferences.get(key, True))
        
        st.markdown("**📱 Push Notifications**")
        
        push_enabled = st.checkbox("📱 Enable push notifications", 
                                  value=preferences.get('push_notifications', True))
        
        if push_enabled:
            push_frequency = st.selectbox("🕐 Push frequency", 
                ["Immediate", "Hourly digest", "Daily digest", "Weekly digest"],
                index=0)
        
        st.markdown("**🔔 Notification Categories**")
        
        categories = st.multiselect("📂 Notification categories to receive",
            ["Recommendations", "Movie Updates", "System Updates", "Social Features", "Promotions"],
            default=["Recommendations", "Movie Updates", "System Updates"])
        
        if st.form_submit_button("💾 **Save Preferences**", use_container_width=True):
            preference_data = {
                "email_notifications": email_enabled,
                "push_notifications": push_enabled,
                "categories": categories
            }
            
            if email_enabled:
                preference_data.update(email_prefs)
            
            if push_enabled:
                preference_data["push_frequency"] = push_frequency
            
            with st.spinner("💾 Saving notification preferences..."):
                response = make_api_request("/notifications/api/v1/preferences/", 
                                         method="PATCH", data=preference_data)
                
                if response and response.status_code == 200:
                    st.success("✅ Notification preferences saved!")
                else:
                    st.error("❌ Failed to save preferences. Please try again.")

def show_notification_history():
    """Show notification history and analytics"""
    st.markdown("### 📊 Notification History")
    
    # Fetch notification logs
    response = make_api_request("/notifications/api/v1/logs/my_logs/")
    if response and response.status_code == 200:
        logs = response.json().get('results', [])
        
        if logs:
            # Statistics
            st.markdown("### 📈 Notification Statistics")
            
            total_sent = len(logs)
            delivered = len([log for log in logs if log.get('status') == 'delivered'])
            opened = len([log for log in logs if log.get('opened_at')])
            clicked = len([log for log in logs if log.get('clicked_at')])
            
            col1, col2, col3, col4 = st.columns(4)
            
            stats = [
                ("📤", "Sent", total_sent),
                ("✅", "Delivered", delivered),
                ("👁️", "Opened", opened),
                ("👆", "Clicked", clicked)
            ]
            
            for i, (icon, label, value) in enumerate(stats):
                with [col1, col2, col3, col4][i]:
                    percentage = (value / total_sent * 100) if total_sent > 0 else 0
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #667eea;">{value}</div>
                        <div style="color: #666; font-size: 0.85rem;">{label}</div>
                        <div style="color: #10b981; font-size: 0.75rem;">{percentage:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Recent notifications log
            st.markdown("### 📜 Recent Notification Log")
            
            for log in logs[:10]:
                status_color = {"sent": "#3b82f6", "delivered": "#10b981", "failed": "#ef4444"}.get(log.get('status'), "#6b7280")
                
                st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 8px; border-left: 4px solid {status_color}; margin: 0.5rem 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>{log.get('notification_type', 'Unknown').replace('_', ' ').title()}</strong><br>
                            <span style="color: #666; font-size: 0.9rem;">{log.get('message', 'No message')[:50]}...</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: {status_color}; font-weight: bold; text-transform: uppercase; font-size: 0.8rem;">
                                {log.get('status', 'unknown')}
                            </div>
                            <div style="color: #999; font-size: 0.75rem;">
                                {log.get('created_at', '')[:16]}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📜 No notification history available yet.")
    else:
        st.error("❌ Failed to load notification history.")

# Helper functions for interactions
def mark_recommendation_clicked(recommendation_id):
    """Mark recommendation as clicked"""
    response = make_api_request(f"/recommendations/v1/recommendations/{recommendation_id}/click/", method="POST")
    if response and response.status_code == 200:
        st.success("🎯 Recommendation feedback recorded!")
    return response

def provide_recommendation_feedback(recommendation_id, feedback_type):
    """Provide feedback on recommendation"""
    feedback_data = {
        "feedback_type": feedback_type,
        "recommendation_id": recommendation_id
    }
    
    response = make_api_request(f"/recommendations/v1/interactions/{recommendation_id}/update_feedback/", 
                               method="PATCH", data=feedback_data)
    if response and response.status_code == 200:
        if feedback_type == 'negative':
            st.success("👎 Feedback recorded - we'll avoid similar recommendations!")
        else:
            st.success("👍 Feedback recorded - we'll find more like this!")
    return response

if __name__ == "__main__":
    main()