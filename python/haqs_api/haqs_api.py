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
from bokeh.tile_providers import CARTODBPOSITRON, STAMEN_TERRAIN, STAMEN_TONER
import psycopg2

NoneType = type(None)

stations_request = "http://api.gios.gov.pl/pjp-api/rest/station/findAll"
sensors_request = "http://api.gios.gov.pl/pjp-api/rest/station/sensors/"  # {stationId} needed
data_request = "http://api.gios.gov.pl/pjp-api/rest/data/getData/"  # {sensorId} needed
aq_index_request = "http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/"  # {stationId} needed


def get_stations():
    """
    Function returns station JSON file requested from GIOS API
    """
    return requests.get(stations_request).json()


def create_stations_gdf(stations_json, map=False):
    """
    Function returns stations GeoDataFrame.
    Function has been deprecated since PostgreSQL Database
    was added to the project.

    params
    -------------
        stations (dict):
            JSON object requested from GIOŚ API

        map (bool):
            boolean used for additional output
            necessary for folium map

    returns
    -------------
        stations_df (gpd.GeoDataFrame):
            geopandas GeoDataFrame with all
            available air monitoring stations
    """
    stations_dict = {}
    station_ids = []
    station_name = []
    station_lon = []
    station_lat = []
    station_geometries = []

    if map:
        for station in stations_json:

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
        for station in stations_json:

            station_ids.append(station["id"])
            station_geometries.append(Point(float(station["gegrLon"]),
                                            float(station["gegrLat"])))

        stations_dict["station_id"] = station_ids
        stations_dict["geometry"] = station_geometries

    stations_df = gpd.GeoDataFrame(stations_dict)
    stations_df.crs = from_epsg(4326)

    return stations_df


def create_stations_map(stations_json):
    """
    Function returns folium map with GIOS
    air monitoring stations in Poland
    """
    stations_map = folium.Map([52, 19], zoom_start=6, tiles='Stamen Terrain')

    stations_df = create_stations_gdf(stations_json, map=True)

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


def create_sensors_df(stations_json):
    """
    Function returns sensors DataFrame.
    Function has been deprecated since PostgreSQL Database
    was added to the project.
    """
    sensors_dict = {}
    stations_ids = []
    sensors_ids = []
    sensors_param = []

    for station in stations_json:

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


def get_available_parameters(sensors_df):
    return list(sensors_df.parameter.unique())


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


def get_latest_sensors_readings(sensors_df):
    """
    Function returns latest available reading for each sensor.
    It uses get_sensor_readings() function.
    """
    sensors_df['data'] = sensors_df.apply(get_sensor_readings, axis=1)
    return sensors_df


def get_param_df(stations_df, sensors_df, parameter):
    """
    Function returns pandas DataFrame with latest
    readings for parsed parameter
    """

    param_df = sensors_df[sensors_df["parameter"] == "{}".format(parameter)]
    param_df = gpd.GeoDataFrame(pd.merge(param_df, stations_df, on='station_id'))
    param_df.dropna(inplace=True)
    param_df.crs = from_epsg(4326)

    return param_df


def show_readings_map(param_df, tile=CARTODBPOSITRON):

    # conversion to World Mercator needed
    param_df = param_df.to_crs(epsg=3395)

    # normalize data column
    param_df["data"] = (param_df['data']-param_df['data'].mean())/param_df['data'].std()
    param_df["data"] = (param_df['data']-param_df['data'].min())/(param_df['data'].max()-param_df['data'].min())

    plotting.output_notebook()

    # reduce differences between readings
    size = param_df["data"] * 50
    # get data resolution
    radii = np.array(size)
    # create colors list
    colors = ["#%02x%02x%02x" % (int(r), int(g), int(b)) for r, g, b, _ in 255*mpl.cm.RdYlGn(1-mpl.colors.Normalize()(radii))]

    p = plotting.figure(toolbar_location="left",
                        plot_width=900,
                        plot_height=700,
                        x_axis_type="mercator",
                        y_axis_type="mercator")

    p.circle(param_df['geometry'].x, param_df['geometry'].y, size=size,
             fill_color=colors, fill_alpha=0.8, line_color=None)

    p.add_tile(tile)

    plotting.show(p)


"""POSTGRESQL PART"""


def connect_with_db():
    """
    Function connects with PostgreSQL DataBase
    and returns connection object if connection
    was succesfully established
    """
    try:
        conn = psycopg2.connect("dbname='haqs' user='postgres' host='localhost' password='postgres'")
        print("Successfully connected with DataBase!")
        return conn
    except Exception as e:
        print(e)
        print("Unable to connect to the DataBase!")
        conn.close()


def close_db_connection(conn):
    conn.close()
    print("Connection has been closed!")


def create_postgis_extension(conn):
    sql = "CREATE EXTENSION postgis;"
    execute_sql(conn, sql)


def execute_sql(conn, sql, *args):
    """
    Function helps to deal with DataBase errors
    which occurs during sql statements execution.
    It rolls back to savepoint created before
    statement run.
    """
    cur = conn.cursor()
    cur.execute('SAVEPOINT sp1;')  # create database savepoint
    # print("SAVEPOINT created!")
    try:
        cur.execute(sql, tuple(args))
        conn.commit()
        #print("SQL was successfully executed!")
    except Exception as e:
        print(e)
        cur.execute('ROLLBACK TO SAVEPOINT sp1;')  # rollback to savepoint
        # print("Rollback to SAVEPOINT!")
    """
    else:
        cur.execute('RELEASE SAVEPOINT sp1;')  # release savepoint
        print("SAVEPOINT released!")
    """


def show_database_tables(conn):
    sql = "SELECT * FROM pg_catalog.pg_tables;"
    execute_sql(conn, sql)


def create_stations_table(conn):
    sql =   """
                CREATE TABLE public.stations
                (
                    station_id INTEGER PRIMARY KEY,
                    geom geometry(Point, 4326)
                );
            """
    # To add geometry column to Table following command is needed
    # SELECT AddGeometryColumn('stations', 'geom', '4326', 'POINT', 2);
    execute_sql(conn, sql)


def db_insert_station(conn, *args):
    """
    Function inserts stations with its coordinates to Stations Table
    """
    sql =   """
                INSERT INTO public.stations (station_id, geom)
                VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326));
            """
    execute_sql(conn, sql, *args)


def show_insertions(conn, table="stations"):
    sql = "SELECT * FROM public.{};".format(table)

    cur = conn.cursor()
    cur.execute('SAVEPOINT sp1;')  # create database savepoint
    print("SAVEPOINT created!")
    try:
        cur.execute(sql)
        conn.commit()
        print("SQL was successfully executed!")
        columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columns)
        return df
    except Exception as e:
        print(e)
        cur.execute('ROLLBACK TO SAVEPOINT sp1;')  # rollback to savepoint
        print("Rollback to SAVEPOINT!")
    else:
        cur.execute('RELEASE SAVEPOINT sp1;')  # release savepoint
        print("SAVEPOINT released!")


def return_stations_gdf(conn):
    sql = "SELECT * FROM public.stations;"
    try:
        return gpd.read_postgis(sql, conn, geom_col='geom')
    except Exception as e:
        print(e)


def create_sensors_table(conn):
    sql =   """
                CREATE TABLE public.sensors
                (
                    sensor_id INTEGER PRIMARY KEY,
                    sensor_parameter VARCHAR(10) NOT NULL,
                    station_id INTEGER REFERENCES stations (station_id)
                );
            """
    execute_sql(conn, sql)


def db_insert_sensor(conn, *args):
    """
    Function inserts sensors with its coordinates to Sensor Table
    """
    sql =   """
                INSERT INTO public.sensors (sensor_id, sensor_parameter, station_id)
                VALUES (%s, %s, %s);
            """
    execute_sql(conn, sql, *args)


def return_sensors_df(conn):
    sql = "SELECT * FROM public.sensors"
    sensors_df = pd.read_sql_query(sql, con=conn)
    return sensors_df


def create_readings_table(conn):
    sql =   """
                CREATE TABLE public.readings 
                (
                    sensor_id INTEGER REFERENCES sensors (sensor_id),
                    date VARCHAR(19) NOT NULL,
                    reading FLOAT(4)
                );
            """
    execute_sql(conn, sql)


def return_sensors_ids(conn):
    sql = "SELECT sensor_id FROM sensors;"
    cur = conn.cursor()
    cur.execute(sql)
    sensors_ids = [values[0] for values in cur.fetchall()]
    return sensors_ids


def db_insert_sensor_readings(conn, *args):
    """
    Function inserts multiple readings for sensor
    """
    sql =   """
                INSERT INTO readings (sensor_id, date, reading)
                SELECT %s, %s, %s
                WHERE
                    NOT EXISTS
                    (
                        SELECT * FROM readings WHERE date = %s AND sensor_id = %s
                    )
            """
    execute_sql(conn, sql, *args)


def return_readings_df(conn):
    sql = "SELECT * FROM public.readings"
    readings_df = pd.read_sql_query(sql, con=conn)
    return readings_df