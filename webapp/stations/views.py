from django.views.generic import TemplateView
from django.shortcuts import render
from django.core.serializers import serialize
from django.http import HttpResponse
from .models import Stations


class HomePageView(TemplateView):
    template_name = 'stations/index.html'


def stations_dataset(request):
    stations = serialize('geojson', Stations.objects.all())
    return HttpResponse(stations, content_type='json')
