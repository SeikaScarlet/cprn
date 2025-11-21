# -*- coding : utf-8 -*-
# create date : Aug 15, 24
# last update :  Nov 20, 25

# author : seika
# general geohash processer 


import array
import pandas as pd
import geopandas as gpd

from geohash import encode as gh_encode, decode as gh_decode, neighbors as gh_neighbors
from shapely.geometry import Point, LineString



class Geohash:

    @staticmethod
    def tuple_encode(tup : tuple, precision : int = 12, upper : bool = False) -> str:
        """ encode a tuple (x, y) to geohash
        """
        if upper:
            return gh_encode(tup[1], tup[0], precision).upper()
        else:
            return gh_encode(tup[1], tup[0], precision)
        
    @staticmethod
    def tuple_decode(tup : tuple[str]) -> tuple:
        """ decode a tuple of geohash(str) into tuple of (lat, lon) 
        """
        return tuple(gh_decode(gh) for gh in tup)
    
    @staticmethod
    def z_encode(z : float, precision_z : int = 2, digital_z : int = 6) -> str:
        """Convert a Z coordinate value to a fixed-length string for GeoHashZ encoding.
    
        This method encodes a floating-point Z coordinate value into a fixed-length
        string of digits. The encoding process involves:
        1. Scaling the value by 10^precision_z to preserve decimal precision
        2. Rounding to the nearest integer
        3. Padding with leading zeros to ensure a fixed length of digital_z digits
        
        The maximum encodable value is determined by digital_z and precision_z:
        max_value = 10^(digital_z - precision_z). Values exceeding this limit will
        be clamped to the maximum and a warning will be printed.
        
        Parameters
        ----------
        z : float
            The Z coordinate value to encode. Can be any floating-point number.
            Values exceeding the maximum encodable value will be clamped.
        precision_z : int, default=2
            The number of decimal places to preserve in the encoding.
            Determines the scaling factor: value is multiplied by 10^precision_z
            before rounding. Must be less than or equal to digital_z.
            Example: precision_z=2 means values like 123.45 are encoded as "12345".
        digital_z : int, default=6
            The total number of digits in the output string. The string will be
            zero-padded to this length. Must be greater than or equal to precision_z.
            Example: digital_z=6 means output will always be 6 characters (e.g., "012345").
        
        Returns
        -------
        str
            A fixed-length string representation of the encoded Z value.
            Length is always equal to digital_z, padded with leading zeros if necessary.
            Example: For z=123.45, precision_z=2, digital_z=6, returns "012345".
        
        Examples
        --------
        >>> Geohash.z_encode(123.45, precision_z=2, digital_z=6)
        '012345'
        
        >>> Geohash.z_encode(10.66, precision_z=2, digital_z=6)
        '001066'
        
        >>> Geohash.z_encode(9999.99, precision_z=2, digital_z=6)
        '999999'
        
        >>> # Value exceeding maximum will be clamped
        >>> Geohash.z_encode(10000.0, precision_z=2, digital_z=6)
        Warning: the Point has z value greater than 10000, set to 10000
        '100000'
        
        Notes
        -----
        - The maximum encodable value is: 10^(digital_z - precision_z) - 1/10^precision_z
        - For default parameters (precision_z=2, digital_z=6), max value is 9999.99
        - This method is typically used in conjunction with GeoHash encoding to create
          GeoHashZ strings that include elevation or height information.
        - The encoding is lossy: values are rounded to the nearest representable value
          based on precision_z.
      """ 

        z_top = 10**(digital_z - precision_z)
        if z > z_top:
            z = z_top
            print(f"Warning: the Point has z value greater than {z_top}, set to {z_top}")
        z_code = str(int(round(z * 10**precision_z))).zfill(digital_z)
        return z_code
    
    @staticmethod
    def z_decode(z_code : str, precision_z : int = 2, digital_z : int = 6) -> float:
        """ decode a z value from str (of int) to float for geometry use
        """
        if len(z_code) != digital_z:
            raise ValueError(f"The length of z_code must be {digital_z}, but got {len(z_code)}")
        z_val = int(z_code) / 10**precision_z
        return z_val
    
    @staticmethod
    def pt_encode(pt : Point , precision : int = 12, upper : bool = False) -> str:
        """ encode a point geom to geohash
        """
        if upper:
            return gh_encode(pt.y , pt.x, precision).upper()
        else:
            return gh_encode(pt.y , pt.x, precision)
    
    @staticmethod
    def ptz_encode(ptz : Point, precision : int = 12, 
                   precision_z : int = 2, digital_z : int = 6, 
                   sep : str = '', upper : bool = False) -> str:
        """ encode a point with z to geohashZ (ghz)
        """
        if ptz.has_z:
            z_val = ptz.z
        else:
            z_val = 0
            print("Warning: the Point has no z value, set to 0")

        z_code = Geohash.z_encode(z_val, precision_z, digital_z,)
        if upper:
            return gh_encode(ptz.y, ptz.x, precision).upper()+ sep +z_code
        else:
            return gh_encode(ptz.y, ptz.x, precision)+ sep + z_code
        
    @staticmethod
    def ghz_decode(ghz : str, precision_z : int = 2, digital_z : int = 6) -> tuple:
        """Decode a GeoHashZ (`str`) into a `tuple` of (lon, lat, z).

        This method decodes a GeoHashZ string that combines a GeoHash (encoding X,Y coordinates) 
        with a Z value encoded as a fixed-length string of digits. The Z value is appended 
        to the GeoHash without any separator.

        Parameters
        ----------
        ghz : str
            The GeoHashZ string to decode. Format: "<geohash><z_code>"
            where <z_code> is a fixed-length string of digits representing the Z value.
            Example: "wtm7c3s9g123456" where "wtm7c3s9g" is the GeoHash and "123456" is the Z code.

        precision_z : int, default=2
            The decimal precision of the Z value. This determines how the Z code
            will be converted back to a float value.
            Example: if precision_z=2, then z_code "123456" represents 1234.56

        digital_z : int, default=6
            The number of digits used to encode the Z value in the GeoHashZ string.
            This must match the length of the Z code portion in the input string.

        Returns
        -------
        tuple
            A tuple of (lon, lat, z-value).

        Examples
        --------
        >>> from taisl_sop.model.geohash import Geohash
        >>> # Decode a GeoHashZ with default parameters
        >>> tuple_point = Geohash.ghz_decode("WTUY399447X6001066")
        >>> tuple_point
        (31.123456, 120.123456, 10.66)
        
        Raises
        ------
        ValueError
            If the length of the Z code portion (determined by digital_z) 
            doesn't match the expected length.

        Notes
        -----
        - The GeoHash portion is decoded using the `geohash.decode()` function
        - The Z code is converted to a float by dividing by 10^precision_z
        - The resulting Point uses the EPSG:4326 coordinate system (WGS84)
        """
        gh, z = ghz[:-digital_z], ghz[-digital_z:]
        lat, lon = gh_decode(gh)
        z_val = Geohash.z_decode(z, precision_z, digital_z)
        return (lon, lat, z_val)

    @staticmethod
    def line_encode(geom_ln, precision : int = 12, upper : bool = False) -> tuple:
        """ Encode a line geometry to geohash tuple.

        Parameters:
        -----------
        geom_ln : shapely.geometry.LineString
            The input line geometry to be encoded.
        precision : int, optional
            The precision level of the geohash encoding. Default is 12.
        upper : bool, optional
            Whether to return the geohash in uppercase. Default is False.

        Returns:
        --------
        tuple
            A tuple containing the geohash encodings for each coordinate pair of the line geometry.

        Example:
        ---------
        >>> from taisl_sop.model.geohash import Geohash
        >>> from shapely.geometry import LineString
        >>> line = LineString([(30.0, 10.0), (30.1, 10.1), (30.2, 10.2)])
        >>> tup_gh = Geohash.line_encode(line, precision=5)
        >>> print(tup_gh)
        ('gcpuv', 'gcpuw', 'gcpuw')
        """
        cords = geom_ln.xy
        lat, lon = cords[1], cords[0]
        if upper:
            return tuple(gh_encode(lat, lon, precision=precision).upper() for lat, lon in zip(lat, lon))
        else:
            return tuple(gh_encode(lat, lon, precision=precision) for lat, lon in zip(lat, lon))
        
    @staticmethod
    def line_decode(tup : tuple) -> tuple:
        """ decode a tuple of geohash(str) and construct a  line geometry
        """
        return LineString([(lon, lat) for lat, lon in (gh_decode(gh) for gh in tup)])
    
    @staticmethod
    def linez_encode(geom_ln, precision : int = 12, upper : bool = False, **kwargs) -> tuple:
        """ encode a line geometry with zm to geohash
        """
        coords = geom_ln.coords
        lat, lon = coords[1], coords[0]
        lst_z_str = [Geohash.z_encode(point[2], **kwargs) for point in geom_ln.coords]
        
        if upper:
            tup_xy = Geohash.line_encode(geom_ln, precision, upper=True)
        else:
            tup_xy = Geohash.line_encode(geom_ln, precision, upper=False)
        tup_xyz = tuple(tup_xy + z_str for tup_xy, z_str in zip(tup_xy, lst_z_str))
        return tup_xyz
    
    @staticmethod
    def linez_decode(tup : tuple) -> LineString:
        """ decode a tuple of geohashZ (str) and construct a line geometry
        """
        return LineString([(lon, lat, z) for lat, lon, z in (Geohash.ghz_decode(ghz) for ghz in tup)])

    @staticmethod
    def gdf_pt_encode(gdf, encode_col : None , geohash_col : str = 'geohash', 
                      precision : int = 12) -> gpd.GeoDataFrame:
        """ encode a point column of a geodataframe to geohash column
        """
        gdf_ = gdf.copy()
        if encode_col is None:
            ghash = gdf_.geometry.apply(
                lambda x: Geohash.pt_encode(x, precision, upper=True))
        else:
            ghash = gdf_.apply(
                lambda x: Geohash.pt_encode(x[encode_col], 
                                            precision, upper=True), axis = 1)
        gdf_[geohash_col] = ghash
        return gdf_
    
    @staticmethod
    def gdf_pt_decode(gdf : gpd.GeoDataFrame, 
                      colname_geohash : str, 
                      decode_z : bool = False,
                      precision_z : int = 2,
                      digital_z : int = 6,
                      inplace : bool = False,
                      ) -> gpd.GeoDataFrame:
        """ decode geohash column of given geodataframe into column of geom (Point)
        """
        pass
    
    @staticmethod
    def gdf_tuple_encode(gdf, encode_col, geohash_col : str = 'geohash', 
                         precision : int = 12) -> gpd.GeoDataFrame:
        """ encode a tuple col (x, y, z) of a geodataframe to geohash column
        """
        gdf_ = gdf.copy()
        ghash = gdf_.apply(lambda x: Geohash.tuple_encode(x[encode_col], precision), axis = 1)
        gdf_[geohash_col] = ghash
        return gdf_
    
    @staticmethod
    def gdf_line_decode(gdf, cols_gh : list[str], ):
        """ decode geohash columns of given geodataframe and construct a line geometry
        """
        gdf_ = gdf.copy()
        gdf_['geom'] = gdf_.apply(
            lambda row: Geohash.line_decode(row[cols_gh]), axis=1)
        return gdf_

    @staticmethod
    def decode_srctgt_df_gdf(df_srctgt : pd.DataFrame, 
                             colname_srctgt : tuple = ('source', 'target'), 
                             ) -> gpd.GeoDataFrame:
        """ decode df with src and tgt geohash to gdf (of LineString)
        """
        from shapely.geometry import LineString
        df_ = df_srctgt.copy()
        df_['lat_src'], df_['lon_src'] = zip(*df_[colname_srctgt[0]].apply(gh_decode))
        df_['lat_tgt'], df_['lon_tgt'] = zip(*df_[colname_srctgt[1]].apply(gh_decode))

        df_['geom'] = df_.apply(
            lambda x: LineString(
                [(x['lon_src'], x['lat_src']), (x['lon_tgt'], x['lat_tgt'])]), axis=1)
        gdf_ = gpd.GeoDataFrame(
            df_, geometry='geom').set_crs(epsg=4326).drop(
                columns=['lat_src', 'lon_src', 'lat_tgt', 'lon_tgt'])
        return gdf_

    @staticmethod
    def decode_gh_df_gdf(df_srctgt : pd.DataFrame, 
                             colname_srctgt : tuple = ('source', 'target'),
                             decode_z : bool = False,
                             precision_z : int = 2,
                             digital_z : int = 6,
                             ) -> gpd.GeoDataFrame:
        """ decode df with src and tgt geohash to gdf (of LineString) , use to replace `decode_srctgt_df_gdf` but support 3D geohash
        
        Parameters:
        -----------
        df_srctgt : pd.DataFrame
            DataFrame containing source and target geohash columns
        colname_srctgt : tuple, default=('source', 'target')
            Column names for source and target geohash
        decode_z : bool, default=False
            Whether to decode Z coordinates (for geohashZ)
        precision_z : int, default=2
            Decimal precision for Z value (used when decode_z=True)
        digital_z : int, default=6
            Number of digits for Z encoding (used when decode_z=True)
        
        Returns:
        --------
        gpd.GeoDataFrame
            GeoDataFrame with LineString geometry
        
        Examples:
        ---------
        >>> # For 2D geohash (existing functionality)
        >>> df_2d = pd.DataFrame({'source': ['ezs42'], 'target': ['ezs48']})
        >>> gdf_2d = Geohash.decode_srctgt_df_gdf(df_2d)
        
        >>> # For 3D geohash (new functionality)
        >>> df_3d = pd.DataFrame({'source': ['WTUY399447X6001066'], 'target': ['WTUY399447X6001067']})
        >>> gdf_3d = Geohash.decode_srctgt_df_gdf(df_3d, decode_z=True)
        """
        from shapely.geometry import LineString
        
        df_ = df_srctgt.copy()
        
        if decode_z:
            # Handle 3D geohash (geohashZ)
            def decode_ghz(ghz_str):
                return Geohash.ghz_decode(ghz_str, precision_z, digital_z)
            
            # Decode source and target coordinates with Z
            df_['coords_src'] = df_[colname_srctgt[0]].apply(decode_ghz)
            df_['coords_tgt'] = df_[colname_srctgt[1]].apply(decode_ghz)
            
            # Extract coordinates
            df_['lon_src'], df_['lat_src'], df_['z_src'] = zip(*df_['coords_src'])
            df_['lon_tgt'], df_['lat_tgt'], df_['z_tgt'] = zip(*df_['coords_tgt'])
            
            # Create LineString with Z coordinates
            df_['geom'] = df_.apply(
                lambda x: LineString([(x['lon_src'], x['lat_src'], x['z_src']), 
                                     (x['lon_tgt'], x['lat_tgt'], x['z_tgt'])]), axis=1)
            
            # Clean up temporary columns
            df_ = df_.drop(columns=['coords_src', 'coords_tgt', 'lon_src', 'lat_src', 'z_src', 
                                   'lon_tgt', 'lat_tgt', 'z_tgt'])
            
        else:
            # Handle 2D geohash (existing functionality)
            df_['lat_src'], df_['lon_src'] = zip(*df_[colname_srctgt[0]].apply(gh_decode))
            df_['lat_tgt'], df_['lon_tgt'] = zip(*df_[colname_srctgt[1]].apply(gh_decode))
    
            df_['geom'] = df_.apply(
                lambda x: LineString(
                    [(x['lon_src'], x['lat_src']), (x['lon_tgt'], x['lat_tgt'])]), axis=1)
            
            # Clean up temporary columns
            df_ = df_.drop(columns=['lat_src', 'lon_src', 'lat_tgt', 'lon_tgt'])
    
        # Create GeoDataFrame
        gdf_ = gpd.GeoDataFrame(df_, geometry='geom').set_crs(epsg=4326)
        return gdf_
    
    @staticmethod
    def decode_df_gdf(df : pd.DataFrame,
                      colname_geohash : str,
                      decode_z : bool = False,
                      ) -> gpd.GeoDataFrame:
        """ decode geohash column from a dataframe to a geodataframe (of Point)
        """
        df_ = df.copy()
        
        if decode_z:
            df_['gh'] = df_[colname_geohash].str[:-6]
            df_['zstr'] = df_[colname_geohash].str[-6:]
            df_['z_val'] = df_['zstr'].apply(lambda x: int(x) / 10**2)
            df_['lat'], df_['lon'] = zip(*df_['gh'].apply(gh_decode))

            gdf_ = gpd.GeoDataFrame(
                df_, geometry=gpd.points_from_xy(
                    x=df_.lon, y=df_.lat, z=df_.z_val, crs='epsg:4326'))
            return gdf_.drop(columns=['lon', 'lat', 'z_val', 'zstr', 'gh'])

        else :
            df_['lat'], df_['lon'] = zip(*df_[colname_geohash].apply(gh_decode))
            gdf_ = gpd.GeoDataFrame(
                df_, geometry=gpd.points_from_xy(df_.lon, df_.lat)).set_crs(epsg=4326)  
            return gdf_.drop(columns=['lon', 'lat'])
    



class GeohashAnalysis:
    """ general analysis method related to geohash
    """

    @staticmethod
    def get_neighbors_geohash(obj_geohash: str, precision: int = 5, 
                              radius: int = 1, upper = False) -> tuple[str]:
        """
        Get all geohashes within a given radius of the obj_geohash.
        
        Parameters:
        obj_geohash (str): The geohash of the reference point.
        precision (int): The precision of the geohash.
        radius (int): The radius to search within.
        
        Returns:
        list[str]: The list of geohashes within the given radius.
        
        Example:
        >>> GeohashAnalysis.get_neighbors_geohash('ezs42', precision=5, radius=1)
        ['ezs42', 'ezs43', 'ezs48', 'ezs49', 'ezs4d', 'ezs4e', 'ezs4f', 'ezs4g', 'ezs4h']
        """
        if radius < 1:
            raise ValueError("Radius must be at least 1.")
        
        def neighbor_recursive_search(
                gh: str, current_radius: int, max_radius: int, seen: set[str]
                ) -> set[str]:
            if current_radius > max_radius:
                return seen
            neighbors = set(gh_neighbors(gh[:precision]))
            neighbors.add(gh[:precision])
            new_neighbors = neighbors - seen
            seen.update(neighbors)
            for neighbor in new_neighbors:
                neighbor_recursive_search(neighbor, current_radius+1, max_radius, seen)
            return seen
        
        set_gh_neib = neighbor_recursive_search(obj_geohash, 0, radius -1, set())
        
        if upper:
            final_set_gh_neib = set(i.upper() for i in set_gh_neib)
        else:
            final_set_gh_neib = set(i.lower() for i in set_gh_neib)

        return tuple(final_set_gh_neib)


    @staticmethod
    def filter_geohash(base_geohash: str, lst_geohash: list[str], 
                           precision: int = 5) -> list[str]:
        """
        filter geohsh from given list of geohash based on the base_geohash using precision
        
        Parameters:
        geohash_str (str): The geohash of the reference point.
        lst_geohash (list[str]): The list of geohashes to compare against.
        precision (int): The length of the prefix to compare.
        
        Returns:
        list[str]: The narrowed down list of geohashes.
        """
        if isinstance(base_geohash, str):
            base_geohash = [base_geohash]

        for gh in base_geohash:
            if len(gh) < precision:
                raise ValueError("The precision must be less than the length of the geohash.")

        prefixes = {gh[:precision] for gh in base_geohash}
        return [gh for gh in lst_geohash if gh[:precision] in prefixes]


    @staticmethod
    def nearest_geohash(obj_geohash:str, lst_geohash: list[str],
                        time_track : bool = False,
                        ) -> tuple[str, float]:
        """ Find the nearest geohash in list `lst_geohash` to geohash `a` and calculate the distance in meters.    
        
        Parameters:
        geohash (str): The geohash of the reference point.
        lst_geohash (list[str]): The list of geohashes to compare against.
    
        Returns:
        tuple: The nearest geohash and the distance in meters.

        Example:
        >>> nearest_geohash('9q8yy', ['9q8yv', '9q8yt', '9q8yq'])
        ('9q8yv', 1105.0)
        """
        if time_track:
            import time
            start_time = time.time()

        # TODO: Implement multiprocess
        
        from scipy.spatial import KDTree
        from geopy.distance import geodesic
        # Decode the reference geohash
        lat_gh, lon_gh = gh_decode(obj_geohash)
        tup_loc_obj = (lat_gh, lon_gh)

        # Decode all geohashes in the list `b`
        lst_tup_loc_ref = [gh_decode(gh) for gh in lst_geohash]

        ts1 = time.time() if time_track else None
        
        # Build a k-d tree from the list of points
        tree = KDTree(lst_tup_loc_ref)

        ts2 = time.time() if time_track else None

        # Query the k-d tree to find the nearest neighbor
        distance_, index = tree.query(tup_loc_obj)

        ts3 = time.time() if time_track else None

        # Get the nearest geohash and calculate the distance in meters
        nearest_geohash = lst_geohash[index]
        nearest_point = lst_tup_loc_ref[index]
        distance_in_meters = geodesic(tup_loc_obj, nearest_point).meters

        ts4 = time.time() if time_track else None

        if time_track:
            print(f"Time to decode all geohashes: {ts1 - start_time}")
            print(f"Time to build the k-d tree: {ts2 - ts1}")
            print(f"Time to query the k-d tree: {ts3 - ts2}")
            print(f"Time to calculate the distance: {ts4 - ts3}")
            print(f"Ovarall time cost: {ts4 - start_time}")

        return nearest_geohash, distance_in_meters
    
    @staticmethod
    def nearest_geohashs(obj_gh:str, lst_gh: list[str],
                         search_radius:int = 1, precision:int = 6) -> tuple[str, float]:
        """ Find the nearest geohash in list `lst_gh` to `obj_gh` in economic way
        """
        obj_gh_range = GeohashAnalysis.get_neighbors_geohash(
            obj_gh, precision=precision, radius=search_radius, upper=True)
        ref_gh_flt = GeohashAnalysis.filter_geohash(
            obj_gh_range, lst_gh, precision=precision)
        return GeohashAnalysis.nearest_geohash(obj_gh, ref_gh_flt)
    

class GeohashProcess:
    """
    """
    @staticmethod
    def create_gdf_linestring_from_geohash(
            df : pd.DataFrame, 
            colnames_geohash : tuple = ('source', 'target'),
            ) -> gpd.GeoDataFrame:
        """ create a geodataframe with linestring geometry from 
        two geohash columns (source, target)

        This function decodes the geohash values in the specified columns of the input DataFrame,
        constructs LineString geometries from the decoded latitude and longitude pairs, and 
        returns a GeoDataFrame containing these geometries.

        Parameters:
        -----------
        df : pd.DataFrame
            The input DataFrame containing geohash columns. It must have at least two columns 
            specified in `colnames_geohash` that contain geohash strings.

        colnames_geohash : tuple, optional
            A tuple of two strings representing the names of the columns in `df` that contain 
            the source and target geohashes, respectively. Default is ('source', 'target').

        Returns:
        --------
        gpd.GeoDataFrame
            A GeoDataFrame containing the LineString geometries created from the decoded 
            geohash coordinates. The GeoDataFrame will have a geometry column named 'geom' 
            and will be set to the EPSG:4326 coordinate reference system.

        Example:
        ---------
        >>> import pandas as pd
        >>> from taisl_sop.model.geohash import GeohashProcess
        >>> data = {
        ...     'source': ['ezs42', 'ezs43'],
        ...     'target': ['ezs48', 'ezs49']
        ... }
        >>> df = pd.DataFrame(data)
        >>> gdf_linestring = GeohashProcess.create_gdf_linestring_from_geohash(df)
        >>> print(gdf_linestring)

        """
        df_ = df.copy()
        df_['lat_src'], df_['lon_src'] = zip(*df_[colnames_geohash[0]].apply(gh_decode))
        df_['lat_tgt'], df_['lon_tgt'] = zip(*df_[colnames_geohash[1]].apply(gh_decode))
        
        df_['geom'] = df_.apply(
            lambda x: LineString(
                [(x['lon_src'], x['lat_src']), (x['lon_tgt'], x['lat_tgt'])]), axis=1)
        
        gdf_ = gpd.GeoDataFrame(df_, geometry='geom').set_crs(
            epsg=4326).drop(columns=['lat_src', 'lon_src', 'lat_tgt', 'lon_tgt'])
        return gdf_