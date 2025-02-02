from datetime import datetime
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
    Function returns list of dictionaries
    with requested air quality stations.

    Notice:
        Function has been deprecated since PostgreSQL
        Database was added to the project.

    Args:
        None

    Returns:
        stations_json (list):
            list of GIOŚ air quality stations
            represented as dictionaries

    Example:
        In [1]: stations_json = get_stations()
                stations_json[0]
        Out[1]: {'id': 114,
                'stationName': 'Wrocław - Bartnicza',
                'gegrLat': '51.115933',
                'gegrLon': '17.141125',
                'city': {'id': 1064,
                        'name': 'Wrocław',
                        'commune': {'communeName': 'Wrocław',
                                    'districtName': 'Wrocław',
                                    'provinceName': 'DOLNOŚLĄSKIE'}},
                'addressStreet': 'ul. Bartnicza'}
    """
    return requests.get(stations_request).json()


def create_stations_gdf(stations_json, map=False):
    """
    Function returns GeoDataFrame of air quality stations.

    Notice:
        Function has been deprecated since PostgreSQL
        Database was added to the project.

    Args:
        stations_json (list):
            list of GIOŚ air quality stations
            represented as dictionaries

        map (bool) - default False:
            boolean used for additional output
            necessary for folium map

    Returns:
        stations_df (gpd.GeoDataFrame):
            geopandas GeoDataFrame with all
            available air monitoring stations

    Example:
        In [1]: stations_json = get_stations()
                stations_df = create_stations_gdf(stations_json)
                stations_df.head()
        Out[1]: 	station_id	  geometry
                0   114           POINT (17.141125 51.115933)
                1	117           POINT (17.02925 51.129378)
                2	129	          POINT (17.012689 51.086225)
                3   52            POINT (16.180513 51.204503)
                4	109	          POINT (16.269677 50.768729)
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

    Args:
        stations_json (list):
            list of GIOŚ air quality stations
            represented as dictionaries

    Returns:
        stations_map (folium.Map):
            folium map with requested air quality stations

    Example:
        In [1]: stations_json = get_stations()
                create_stations_map(stations_json)
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
    Function returns DataFrame of sensors requested from GIOS API.

    Notice:
        Function has been deprecated since PostgreSQL
        Database was added to the project.

    Args:
        stations_json (list):
            list of GIOŚ air quality stations
            represented as dictionaries

    Returns:
        sensors_df (pd.DataFrame):
            pandas DataFrame with all available sensors.
            Most of air monitoring stations has multiple sensors.

    Example:
        In [1]: stations_json = get_stations()
                sensors_df = create_sensors_df(stations_json)
                sensors_df.head()
        Out[1]: 	station_id	sensor_id	parameter
                0	114	        642	        NO2
                1	114	        644	        O3
                2	117	        660	        CO
                3	117	        14395	    PM10
                4	117	        658	        C6H6
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
    """
    Function returns list of measured air parameters.

    Notice:
        Function has been deprecated since PostgreSQL
        Database was added to the project.

    Args:
        stations_json (list):
            list of GIOŚ air quality stations
            represented as dictionaries

    Returns:
        sensors_df (pd.DataFrame):
            pandas DataFrame with all available sensors.
            Most of air monitoring stations has multiple sensors.

    Example:
        In [1]: stations_json = get_stations()
                sensors_df = create_sensors_df(stations_json)
                available_parameters = get_available_parameters(sensors_df)
                available_parameters
        Out[1]: ['NO2', 'O3', 'CO', 'PM10', 'C6H6', 'PM2.5', 'SO2']
    """
    return list(sensors_df.parameter.unique())


def request_sensor_data(row):
    """
    Function is used as an apply function on sensors_df DataFrame.
    Function returns latest reading.

    Args:
        row (DataFrame row)

    Returns:
        reading_value (float):
            if requested data has proper format
            function returns float value of readings
        np.NaN:
            function returns np.NaN when reading is
            unavailable or when unexpected error occurs

    Example:
        In [1]: sensors_df['value'] = sensors_df.apply(request_sensor_data, axis=1)
    """
    sensor_id = row["sensor_id"]
    reading_json = requests.get(data_request + str(sensor_id)).json()
    count = 0
    try:
        reading_value = reading_json["values"][count]["value"]
        while isinstance(reading_value, NoneType):  # if fails try to get next reading
            reading_value = reading_json["values"][count]["value"]
            count += 1
        return reading_value
    except:
        return np.NaN


def get_latest_sensors_readings(sensors_df):
    """
    Function gets readings for each row in sensors_df DataFrame.
    Function modifies DataFrame inplace.

    Args:
        sensors_df (pd.DataFrame):
            pandas DataFrame with all available sensors.
            Most of air monitoring stations has multiple sensors.

    Returns:
        sensors_df (pd.DataFrame)

    Example:
        In [1]: sensors_df = get_latest_sensors_readings(sensors_df)
                sensors_df.head()
        Out[1]:     station_id  sensor_id   parameter   data
                0	114         642	        NO2	        24.16710
                1	114	        644	        O3	        56.47060
                2	117	        660	        CO	        508.12400
                3	117	        14395	    PM10	    22.14980
                4	117	        658	        C6H6	    0.26215
    """
    sensors_df['value'] = sensors_df.apply(request_sensor_data, axis=1)

    return sensors_df


def get_param_df(stations_df, sensors_df, parameter):
    """
    Function returns geopandas GeoDataFrame with
    latest readings for selected parameter.
    Function automatically merges stations and sensors
    DataFrames in order to create GeoDataFrame.

    Args:
        stations_df (gpd.GeoDataFrame):
            geopandas GeoDataFrame with all
            available air monitoring stations.

        sensors_df (pd.DataFrame):
            pandas DataFrame with all available sensors.
            Most of air monitoring stations has multiple sensors.

        parameter (string):
            one of available air quality parameters should be passed.
            Full list of parameters could be called using
            get_available_parameters() function.

    Returns:
        param_df (gpd.GeoDataFrame):
            geopandas GeoDataFrame with all
            available air monitoring stations
            and its latests readings.

    Example:
        In [1]: params_df = get_param_df(stations_df, sensors_df, 'PM10')
                param_df.head()
        Out[1]: 	station_id	 sensor_id	 parameter    value	     geometry
                0	117	         14395       PM10	      42.9630    POINT (17.02925 51.129378)
                1	52	         14397	     PM10	      53.9311	 POINT (16.180513 51.204503)
                2	109	         618	     PM10	      28.3311	 POINT (16.269677 50.768729)
                3	14	         92	         PM10	      64.2775	 POINT (14.941319 50.972167)
                4	16	         101	     PM10	      38.4400	 POINT (16.64805 50.732817)
    """

    param_df = sensors_df[sensors_df["parameter"] == "{}".format(parameter)]
    param_df = gpd.GeoDataFrame(pd.merge(param_df, stations_df, on='station_id'))
    param_df.dropna(inplace=True)
    param_df.crs = from_epsg(4326)

    return param_df


def show_readings_map(param_df, tile=CARTODBPOSITRON):
    """
    Function visualizes GeoDataFrame with
    latest readings for selected parameter.

    Args:
        param_df (gpd.GeoDataFrame):
            geopandas GeoDataFrame with all
            available air monitoring stations
            and its latests readings.

        tile (bokeh.tile_providers) - default CARTODBPOSITRON:
            one of available Bokeh tile providers
            [CARTODBPOSITRON, STAMEN_TERRAIN, STAMEN_TONER]

    Example:
        In [1]: params_df = get_param_df(stations_df, sensors_df, 'PM10')
                show_readings_map(params_df)
    """
    # conversion to World Mercator needed
    param_df = param_df.to_crs(epsg=3395)

    # normalize data column
    param_df["value"] = (param_df['value']-param_df['value'].mean())/param_df['value'].std()
    param_df["value"] = (param_df['value']-param_df['value'].min())/(param_df['value'].max()-param_df['value'].min())

    plotting.output_notebook()

    # reduce differences between readings
    size = param_df["value"] * 50
    # get data resolution
    radii = np.array(size)
    # create colors palette
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

    Returns:
        conn (psycopg2.connection):
            connection object for DataBase session.

    Example:
        In [1]: conn = connect_with_db()
    """
    try:
        conn = psycopg2.connect("dbname='haqs' user='postgres' host='localhost' password='postgres'")
        print("Successfully connected with DataBase!")
        return conn
    except Exception as e:
        print(e)
        print("Unable to connect to the DataBase!")


def close_db_connection(conn):
    """
    Function closes connection for DataBase session.

    Args:
        conn (psycopg2.connection):
            connection object for DataBase session.

    Example:
        In [1]: close_db_connection(conn)
    """
    try:
        conn.close()
        print("Connection has been closed!")
    except AttributeError:  # conn is NoneType object
        print("There is nothing to close!")
        print("Check your DataBase connection!")



def create_postgis_extension(conn):
    """
    Function creates PostGIS extension to PostgreSQL DataBase.

    Args:
        conn (psycopg2.connection):
            connection object for DataBase session.

    Example:
        In [1]: create_postgis_extension(conn)
    """
    try:
        sql = "CREATE EXTENSION postgis;"
        execute_sql(conn, sql)
    except AttributeError:  # conn is NoneType object
        print("Unable to create postgis extension!")
        print("Check your DataBase connection!")


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
        # print("SQL was successfully executed!")
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
    # print("SAVEPOINT created!")
    try:
        cur.execute(sql)
        conn.commit()
        # print("SQL was successfully executed!")
        columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columns)
        return df
    except Exception as e:
        print(e)
        cur.execute('ROLLBACK TO SAVEPOINT sp1;')  # rollback to savepoint
        # print("Rollback to SAVEPOINT!")
    """
    else:
        cur.execute('RELEASE SAVEPOINT sp1;')  # release savepoint
        print("SAVEPOINT released!")
    """


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


def return_sensors_gdf(conn):
    sql =   """
                SELECT sensors.sensor_id, sensors.sensor_parameter, sensors.station_id, stations.geom
                FROM sensors, stations
                WHERE sensors.station_id = stations.station_id;
            """
    try:
        return gpd.read_postgis(sql, conn, geom_col='geom')
    except Exception as e:
        print(e)


def create_readings_table(conn):
    sql =   """
                CREATE TABLE public.readings
                (
                    id INTEGER PRIMARY KEY,
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


def return_readings_gdf(conn, limit=100):
    sql =   """
                SELECT readings.sensor_id, readings.date, readings.reading,
                    sensors.sensor_parameter, sensors.station_id, stations.geom
                FROM readings
                INNER JOIN sensors on readings.sensor_id = sensors.sensor_id
                INNER JOIN stations on sensors.station_id = stations.station_id
                ORDER BY date DESC
                LIMIT {};
            """.format(limit)
    try:
        return gpd.read_postgis(sql, conn, geom_col='geom')
    except Exception as e:
        print(e)


def return_parameter_gdf(conn, parameter='PM10'):
    """
    Available parameters:
        NO2, O3, CO, PM2.5, PM10, C6H6, SO2
    Returns readings from last hour
    """
    # create string used for query
    now = datetime.now().strftime("%Y-%m-%d {}:00:00".format(int(datetime.now().strftime("%H"))-1))
    sql =   """
                SELECT readings.sensor_id, readings.date, readings.reading,
                    sensors.sensor_parameter, sensors.station_id, stations.geom
                FROM readings
                INNER JOIN sensors on readings.sensor_id = sensors.sensor_id
                INNER JOIN stations on sensors.station_id = stations.station_id
                WHERE sensors.sensor_parameter = '{}'
                    AND readings.date = '{}'
                ORDER BY date DESC
                ;
            """.format(parameter, now)
    try:
        return gpd.read_postgis(sql, conn, geom_col='geom')
    except Exception as e:
        print(e)
