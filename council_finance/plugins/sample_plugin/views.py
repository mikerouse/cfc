from django.http import HttpResponse

def sample_home(request):
    return HttpResponse("Hello from Sample Plugin!")
