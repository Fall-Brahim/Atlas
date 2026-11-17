from django.http import HttpResponse


def home(request):
    return HttpResponse('Your Django application is running.')
