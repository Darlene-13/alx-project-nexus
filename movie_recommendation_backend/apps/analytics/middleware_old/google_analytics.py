import asyncio
import logging
import aiohttp
import json
from urllib.parse import urlencode
from django.http import HttpResponse
from django.conf import settings

logger = logging.getLogger(__name__)

class GoogleAnalyticsMiddleware:
    """
    True async middleware for Google Analytics with server-side tracking
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Detect if get_response is async
        if asyncio.iscoroutinefunction(self.get_response):
            self.async_mode = True
        else:
            self.async_mode = False
        
        self.ga_tracking_id = getattr(settings, 'GOOGLE_ANALYTICS_TRACKING_ID', None)
        self.ga_measurement_url = 'https://www.google-analytics.com/collect'
    
    def __call__(self, request):
        if self.async_mode:
            return self.__acall__(request)
        else:
            return self._sync_call(request)
    
    async def __acall__(self, request):
        """Async version of middleware"""
        # Process request asynchronously
        await self.process_request_async(request)
        
        # Get response from view
        response = await self.get_response(request)
        
        # Process response asynchronously  
        response = await self.process_response_async(request, response)
        
        return response
    
    def _sync_call(self, request):
        """Synchronous fallback"""
        # Sync version for compatibility
        response = self.get_response(request)
        return self.process_response_sync(request, response)
    
    async def process_request_async(self, request):
        """Async request processing"""
        # Skip for static files
        if any(request.path.startswith(path) for path in ['/static/', '/media/', '/admin/', '/favicon.ico']):
            return
        
        # Non-blocking GA server-side tracking
        if self.ga_tracking_id:
            # Fire and forget - send to GA servers asynchronously
            asyncio.create_task(self._send_ga_pageview(request))
            logger.debug(f"Async GA tracking queued for {request.path}")
    
    async def process_response_async(self, request, response):
        """Async response processing"""
        # Skip non-HTML responses
        content_type = response.get('Content-Type', '')
        if not content_type.startswith('text/html'):
            return response
        
        # Skip static files
        if any(request.path.startswith(path) for path in ['/static/', '/media/', '/admin/', '/favicon.ico']):
            return response
        
        # Async GA script injection
        if self.ga_tracking_id and hasattr(response, 'content'):
            await self._inject_ga_script_async(response)
        
        return response
    
    async def _send_ga_pageview(self, request):
        """Send pageview to Google Analytics servers asynchronously"""
        try:
            if not self.ga_tracking_id:
                return
            
            # Generate client ID (you might want to store this in session)
            client_id = f"{request.META.get('REMOTE_ADDR', '0.0.0.0')}.{hash(request.META.get('HTTP_USER_AGENT', ''))}"
            
            # Prepare GA Measurement Protocol data
            ga_data = {
                'v': '1',  # Version
                'tid': self.ga_tracking_id,  # Tracking ID
                'cid': client_id,  # Client ID
                't': 'pageview',  # Hit Type
                'dp': request.path,  # Document Path
                'dt': f'Page {request.path}',  # Document Title
                'uip': request.META.get('REMOTE_ADDR'),  # User IP
                'ua': request.META.get('HTTP_USER_AGENT', ''),  # User Agent
                'dr': request.META.get('HTTP_REFERER', ''),  # Document Referrer
            }
            
            # Remove empty values
            ga_data = {k: v for k, v in ga_data.items() if v}
            
            # Send to GA asynchronously (fire and forget)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.ga_measurement_url,
                    data=urlencode(ga_data),
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=aiohttp.ClientTimeout(total=5)  # 5 second timeout
                ) as response:
                    if response.status == 200:
                        logger.debug(f"GA pageview sent successfully for {request.path}")
                    else:
                        logger.warning(f"GA pageview failed with status {response.status}")
                        
        except asyncio.TimeoutError:
            logger.warning(f"GA pageview timeout for {request.path}")
        except Exception as e:
            logger.error(f"Error sending GA pageview for {request.path}: {e}")
    
    async def _inject_ga_script_async(self, response):
        """Inject GA script asynchronously"""
        try:
            if b'</head>' in response.content:
                ga_script = f'''
    <!-- Google Analytics (Async Injected) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={self.ga_tracking_id}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{self.ga_tracking_id}');
    </script>
    '''
                # Yield control during processing (allows other async operations)
                await asyncio.sleep(0)
                
                response.content = response.content.replace(
                    b'</head>', 
                    ga_script.encode('utf-8') + b'</head>'
                )
                
                if response.get('Content-Length'):
                    response['Content-Length'] = len(response.content)
                    
        except Exception as e:
            logger.error(f"Error in async GA script injection: {e}")
    
    def process_response_sync(self, request, response):
        """Sync fallback for response processing"""
        # Basic sync processing - just return response unchanged
        return response