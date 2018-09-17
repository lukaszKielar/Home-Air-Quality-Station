from django.contrib.gis.db import models


class Stations(models.Model):
    station_id = models.IntegerField(primary_key=True)
    geom = models.PointField(srid=4326, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Station"
        managed = False
        db_table = 'stations'
