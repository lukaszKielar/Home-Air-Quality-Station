from django.conf.urls import url, include
from . import views


app_name = 'stations'

urlpatterns = [
    # city detail view
    url(r'^$', views.HomePageView.as_view(), name='home'),
    url(r'^stations_data/', views.stations_dataset, name='stations')
]