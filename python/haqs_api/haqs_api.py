import requests
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import HeatMap
from fiona.crs import from_epsg
import matplotlib as mpl
import matplotlib.pyplot as plt
import bokeh
from bokeh import plotting
from bokeh.models import GeoJSONDataSource, HoverTool
from bokeh.plotting import figure, show, ColumnDataSource
from bokeh.tile_providers import CARTODBPOSITRON
import psycopg2

NoneType = type(None)
coord_system = from_epsg(4326)  # lon, lat WGS84

stations_request = "http://api.gios.gov.pl/pjp-api/rest/station/findAll"
sensors_request = "http://api.gios.gov.pl/pjp-api/rest/station/sensors/"  # {stationId} needed
data_request = "http://api.gios.gov.pl/pjp-api/rest/data/getData/"  # {sensorId} needed
aq_index_request = "http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/"  # {stationId} needed


def get_stations():
    """
    Function returns station JSON file requested from GIOS API
    """
    return requests.get(stations_request).json()


stations = get_stations()


def create_stations_gdf(map=False):
    """
    Function returns stations GeoDataFrame.
    Function has been deprecated since PostgreSQL Database
    was added to the project.
    """
    stations_dict = {}
    station_ids = []
    station_name = []
    station_lon = []
    station_lat = []
    station_geometries = []
    
    if map:
        for station in stations:

            station_ids.append(station["id"])
            station_name.append(station["stationName"])
            station_lon.append(float(station["gegrLon"]))
            station_lat.append(float(station["gegrLat"]))
            station_geometries.append(Point(float(station["gegrLon"]), 
                                            float(station["gegrLat"])))

        stations_dict["station_id"] = station_ids
        stations_dict["station_name"] = station_name
        stations_dict["latitude"] = station_lat
        stations_dict["longitude"] = station_lon
        stations_dict["geometry"] = station_geometries
        
    else:
        for station in stations:

            station_ids.append(station["id"])
            station_geometries.append(Point(float(station["gegrLon"]), 
                                            float(station["gegrLat"])))

        stations_dict["station_id"] = station_ids
        stations_dict["geometry"] = station_geometries

    stations_df = gpd.GeoDataFrame(stations_dict)
    stations_df.crs = coord_system

    return stations_df


stations_df = create_stations_gdf()


def create_stations_map():
    """
    Function returns folium map with GIOS stations in Poland
    """
    stations_map = folium.Map([52, 19], zoom_start=6, tiles='Stamen Terrain')
    
    stations_df = create_stations_gdf(map=True)
    
    locations = stations_df[["latitude", "longitude"]]
    locations_list = locations.values.tolist()
    
    for point in range(len(stations_df)):
        folium.Marker(locations_list[point], 
                      popup=stations_df['station_name'][point]).add_to(stations_map)
    
    """FIRST VERSION (without pin description)"""
    # points = folium.features.GeoJson(stations_df.to_json())
    # stations_map.add_child(points)
    # stations_map.add_child(HeatMap([[row["lat"], row["lon"]] for name, row in stations_df.iterrows()]))
    
    return stations_map


def create_sensors_df():
    """
    Function returns sensors DataFrame.
    Function has been deprecated since PostgreSQL Database
    was added to the project.
    """
    sensors_dict = {}
    stations_ids = []
    sensors_ids = []
    sensors_param = []

    for station in stations:

        station_id = station["id"]
        sensors = requests.get(sensors_request + str(station_id)).json()

        for sensor in sensors:

            stations_ids.append(sensor["stationId"])
            sensors_ids.append(sensor["id"])
            sensors_param.append(sensor["param"]["paramCode"])

    sensors_dict["station_id"] = stations_ids
    sensors_dict["sensor_id"] = sensors_ids
    sensors_dict["parameter"] = sensors_param

    sensors_df = pd.DataFrame(sensors_dict)

    return sensors_df


sensors_df = create_sensors_df()
available_parameters = list(sensors_df.parameter.unique())


def get_sensor_readings(row):
    """
    Function is used as apply function on sensors_df DataFrame.
    Reqested reading (latest) is added to each row.
    """
    sensor_id = row["sensor_id"]
    data_json = requests.get(data_request + str(sensor_id)).json()
    count = 0
    try:
        data = data_json["values"][count]["value"]
        while isinstance(data, NoneType):
            data = data_json["values"][count]["value"]
            count += 1 
        return data
    except:
        return np.NaN
    

def get_latest_sensors_readings():
    """
    Function returns latest available reading for each sensor.
    It uses get_sensor_readings() function.
    """
    sensors_df['data'] = sensors_df.apply(get_sensor_readings, axis=1)
    return sensors_df


