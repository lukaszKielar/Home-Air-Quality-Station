1. Type

```
python manage.py createsuperuser
django-admin startproject webapp
```

2. Change webapp/settings.py

```
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'haqs',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'leaflet',
    'webapp',
    'stations',
]
```

3. Create new app

```python manage.py startapp stations```

4. Check if there is connection with postgreSQL

```python manage.py runserver```

5. If your DB already exists and you have data in it you can automatically create models.py

```python manage.py inspectdb > models.py```

6. Migrate data


```python manage.py makemigrations```

```python manage.py migrate```


7. Add urls to webapp/urls.py

```
from django.contrib import admin
from django.conf.urls import url, include

urlpatterns = [
    url('admin/', admin.site.urls),
    url(r'^stations/', include('stations.urls')),
]
```

8. Create stations/urls.py

```
from django.conf.urls import url, include
from . import views

app_name = 'stations'

urlpatterns = [
    url(r'^station/(?P<pk>[0-9]+)$', views.StationsDetailView.as_view(), station_id='station-id'),
]
```
    
9. Create stations/views.py

```
from django.shortcuts import render
from django.views.generic import DetailView
from .models import Stations

class StationsDetailView(DetailView):
    template_name = 'stations/station-detail.html'
    model = Stations
```

10. Create HTML template under stations/templates/stations/station-detail.html
