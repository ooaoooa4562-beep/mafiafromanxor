from django.conf import settings
from django.http import FileResponse, Http404


def _frontend_file(name):
    path = settings.BASE_DIR.parent / 'frontend' / name
    if not path.is_file():
        raise Http404('Frontend page not found')
    return FileResponse(path.open('rb'))


def lobby(request):
    return _frontend_file('index.html')


def play(request):
    return _frontend_file('play.html')
