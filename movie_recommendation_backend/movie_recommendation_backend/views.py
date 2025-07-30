from django.shortcuts import render

def landing_page(request):
    """
    A simple landing page view.
    """
    return render(request, 'landing_page.html')