from django.contrib.gis.db import models


class Stations(models.Model):
    station_id = models.IntegerField(primary_key=True)
    geom = models.PointField(srid=4326, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Station"
        managed = False
        db_table = 'stations'


class Sensors(models.Model):
    sensor_id = models.IntegerField(primary_key=True)
    sensor_parameter = models.CharField(max_length=10)
    station = models.ForeignKey('Stations', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Sensor"
        managed = False
        db_table = 'sensors'


class Readings(models.Model):
    sensor = models.ForeignKey('Sensors', models.DO_NOTHING, blank=True, null=True)
    date = models.CharField(max_length=19)
    reading = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Reading"
        managed = False
        db_table = 'readings'
