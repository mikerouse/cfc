from django.shortcuts import render

def index(request):
    return render(request, 'react_frontend/index.html')
