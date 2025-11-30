# -*- coding : utf-8 -*-
# create date : Nov 24th, 25
# last update : Nov 24th, 25
# author : seika<seika@live.ca>

"""
topic : Edge code query module for CPRN
ver : v4.1.7.1
description : Query edge records from database by edge_code list(s)
"""

from typing import List, Dict, Union, Optional, Any
import sqlite3
import geopandas as gpd
import pandas as pd

from loguru import logger as log

try:
    from taisl_lib.data.connectionmanager import PullData
    from taisl_sop.data.base.sql_builder import SqlClauseBuilder
    from taisl_sop.data.base.spatialite import SpatialitePuller
except ImportError as e:
    log.error(f"Failed to import dependencies: {e}")
    raise


class EdgeCodeQuery:
    """
    Edge code query module for CPRN
    
    Support querying edge records from PostGIS or SQLite/Spatialite databases
    based on edge_code list(s). Support nested and non-nested query modes.
    
    Example:
        >>> # PostGIS
        >>> query = EdgeCodeQuery(
        ...     db_config={'type': 'postgis', 'engine': engine_pg},
        ...     table_name='cprn_dg_short_edges_geom_V417_jiangsu',
        ...     schema='cprn'
        ... )
        >>> result = query.query(['edge_code_1', 'edge_code_2'])
        >>> gdf = query.to_geodataframe(result)
        
        >>> # SQLite
        >>> query = EdgeCodeQuery(
        ...     db_config='/path/to/database.sqlite',
        ...     table_name='cprn_dg_short_edges_geom_V417_jiangsu',
        ...     spatialite_ext_path='/path/to/mod_spatialite.dylib'
        ... )
        >>> result = query.query([['edge_code_1', 'edge_code_2'], ['edge_code_3']])
        >>> gdf_list = query.to_geodataframe(result)
    """
    
    def __init__(
        self,
        db_config: Union[Dict[str, Any], str],
        table_name: str,
        columns: Optional[List[str]] = None,
        spatialite_ext_path: Optional[str] = None,
        schema: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Initialize EdgeCodeQuery
        
        Args:
            db_config: Database configuration
                - PostGIS: dict with keys 'type'='postgis' and 'engine' (SQLAlchemy engine)
                - SQLite: str path to SQLite database file
            table_name: Name of the table to query from
            columns: Optional list of column names to query. If None, query all columns.
            spatialite_ext_path: Path to Spatialite extension (required for SQLite)
            schema: Schema name for PostGIS (default: 'cprn')
            verbose: Whether to print verbose output
        """
        self.table_name = table_name
        self.columns = columns
        self.schema = schema or 'cprn'
        self.verbose = verbose
        
        # Determine database type and initialize connection
        if isinstance(db_config, dict) and db_config.get('type') == 'postgis':
            self.db_type = 'postgis'
            self.engine_pg = db_config.get('engine')
            if self.engine_pg is None:
                raise ValueError("PostGIS engine is required when db_config type is 'postgis'")
            if self.verbose:
                log.info(f"Initialized EdgeCodeQuery with PostGIS, table: {self.table_name}")
        elif isinstance(db_config, str):
            self.db_type = 'sqlite'
            self.path_sqlite = db_config
            if spatialite_ext_path is None:
                raise ValueError("spatialite_ext_path is required for SQLite database")
            self.spatialite_ext_path = spatialite_ext_path
            self._spatialite_puller = None  # Lazy initialization
            if self.verbose:
                log.info(f"Initialized EdgeCodeQuery with SQLite: {self.path_sqlite}, table: {self.table_name}")
        else:
            raise ValueError(
                "db_config must be either a dict with type='postgis' and engine, "
                "or a string path to SQLite database"
            )
    
    def _get_spatialite_puller(self) -> SpatialitePuller:
        """Get or create SpatialitePuller instance (lazy initialization)"""
        if self._spatialite_puller is None:
            self._spatialite_puller = SpatialitePuller(
                path_sqlite=self.path_sqlite,
                path_spatialite_ext=self.spatialite_ext_path,
                driver='sqlite',
                set_precision=False,
                verbose=self.verbose
            )
        return self._spatialite_puller
    
    def _is_nested(self, edge_codes: Union[List[str], List[List[str]]]) -> bool:
        """
        Check if edge_codes is nested (list of lists) or flat (list of strings)
        
        Args:
            edge_codes: Input edge codes
            
        Returns:
            True if nested, False if flat
        """
        if not edge_codes:
            return False
        return isinstance(edge_codes[0], list)
    
    def _build_select_clause(self) -> str:
        """
        Build SELECT clause for SQL query
        
        Returns:
            SELECT clause string
        """
        if self.columns is None:
            # Query all columns
            if self.db_type == 'postgis':
                return "*"
            else:
                # For SQLite, we need to explicitly list columns to handle geometry
                # This will be handled in the actual query method
                return "*"
        else:
            return ", ".join(self.columns)
    
    def _query_single_postgis(self, edge_codes: List[str]) -> List[Dict[str, Any]]:
        """
        Query single batch of edge codes from PostGIS
        
        Args:
            edge_codes: List of edge codes to query
            
        Returns:
            List of dictionaries, each representing a record
        """
        if not edge_codes:
            return []
        
        # Build WHERE clause
        edge_condition = SqlClauseBuilder._build_clause_in(edge_codes, 'edge_code')
        
        # Build SELECT clause
        select_clause = self._build_select_clause()
        
        # Build SQL query
        if self.columns is None:
            sql = f"""
            SELECT *
            FROM {self.schema}."{self.table_name}"
            WHERE {edge_condition}
            """
        else:
            sql = f"""
            SELECT {select_clause}
            FROM {self.schema}."{self.table_name}"
            WHERE {edge_condition}
            """
        
        if self.verbose:
            log.debug(f"PostGIS SQL: {sql}")
        
        # Execute query and get GeoDataFrame
        gdf = PullData.read_postgis(sql, self.engine_pg, 'geom')
        
        # Convert GeoDataFrame to list of dicts
        # Convert geometry to WKT for consistency
        result = []
        for idx, row in gdf.iterrows():
            record = row.to_dict()
            # Keep geometry as shapely object or convert based on need
            result.append(record)
        
        return result
    
    def _query_single_sqlite(self, edge_codes: List[str]) -> List[Dict[str, Any]]:
        """
        Query single batch of edge codes from SQLite
        
        Args:
            edge_codes: List of edge codes to query
            
        Returns:
            List of dictionaries, each representing a record
        """
        if not edge_codes:
            return []
        
        # Build WHERE clause
        edge_condition = SqlClauseBuilder._build_clause_in(edge_codes, 'edge_code')
        
        # Build SELECT clause - for SQLite, convert geometry to WKT
        # SpatialitePuller handles geometry conversion, so we use AsWKT
        if self.columns is None:
            # Get all column names first, then exclude geometry column and add WKT version
            # Query table info to get column names
            with sqlite3.connect(self.path_sqlite) as conn:
                cursor = conn.execute(f"PRAGMA table_info({self.table_name})")
                all_columns = [row[1] for row in cursor.fetchall()]
            
            # Separate geometry and non-geometry columns
            geom_cols = [col for col in all_columns if col.lower() in ['geom', 'geometry']]
            non_geom_cols = [col for col in all_columns if col.lower() not in ['geom', 'geometry']]
            
            # Build SELECT clause: non-geometry columns + geometry as WKT
            select_parts = non_geom_cols.copy()
            if geom_cols:
                # Use first geometry column found
                geom_col = geom_cols[0]
                select_parts.append(f"AsWKT({geom_col}, 16) AS geom")
                col_geom = 'geom'
            else:
                col_geom = None
            
            select_clause = ", ".join(select_parts)
            sql = f"""
            SELECT {select_clause}
            FROM {self.table_name}
            WHERE {edge_condition}
            """
        else:
            # Check if geometry column is in the requested columns
            select_parts = []
            geom_col_name = None
            
            for col in self.columns:
                if col.lower() in ['geom', 'geometry']:
                    # Use AsWKT for geometry column
                    select_parts.append(f"AsWKT({col}, 16) AS {col}")
                    geom_col_name = col
                else:
                    select_parts.append(col)
            
            select_clause = ", ".join(select_parts)
            sql = f"""
            SELECT {select_clause}
            FROM {self.table_name}
            WHERE {edge_condition}
            """
            col_geom = geom_col_name if geom_col_name else None
        
        if self.verbose:
            log.debug(f"SQLite SQL: {sql}")
        
        # Use SpatialitePuller to query - it handles geometry conversion
        puller = self._get_spatialite_puller()
        
        # Query as GeoDataFrame first, then convert to list of dicts
        # col_geom can be None if no geometry column found
        if col_geom:
            gdf = puller.query_sql_gdf(sql, col_geom=col_geom)
        else:
            # No geometry column, query as regular DataFrame then convert
            df = puller.query_sql_df(sql)
            gdf = gpd.GeoDataFrame(df)
        
        # Convert GeoDataFrame to list of dicts
        # Preserve geometry as shapely object (already in GeoDataFrame)
        result = []
        for idx, row in gdf.iterrows():
            record = row.to_dict()
            result.append(record)
        
        return result
    
    def _query_single(self, edge_codes: List[str]) -> List[Dict[str, Any]]:
        """
        Query single batch of edge codes
        
        Args:
            edge_codes: List of edge codes to query
            
        Returns:
            List of dictionaries, each representing a record
        """
        if self.db_type == 'postgis':
            return self._query_single_postgis(edge_codes)
        elif self.db_type == 'sqlite':
            return self._query_single_sqlite(edge_codes)
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def query(
        self, 
        edge_codes: Union[List[str], List[List[str]]]
    ) -> Union[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        """
        Query edge records by edge_code list(s)
        
        Args:
            edge_codes: 
                - list[str]: Non-nested, returns list[dict]
                - list[list[str]]: Nested, returns list[list[dict]]
        
        Returns:
            - list[dict]: Each dict is a record (non-nested input)
            - list[list[dict]]: Outer list corresponds to input sub-lists (nested input)
        """
        if not edge_codes:
            return []
        
        is_nested = self._is_nested(edge_codes)
        
        if is_nested:
            # Nested query: process each sub-list
            result = []
            for sub_list in edge_codes:
                if sub_list:  # Skip empty sub-lists
                    sub_result = self._query_single(sub_list)
                    result.append(sub_result)
                else:
                    result.append([])
            
            if self.verbose:
                log.info(f"Queried {len(result)} nested batches, "
                        f"total records: {sum(len(r) for r in result)}")
            
            return result
        else:
            # Non-nested query: single batch
            result = self._query_single(edge_codes)
            
            if self.verbose:
                log.info(f"Queried {len(edge_codes)} edge codes, got {len(result)} records")
            
            return result
    
    def to_geodataframe(
        self, 
        result: Union[List[Dict[str, Any]], List[List[Dict[str, Any]]]],
        geometry_column: str = 'geom'
    ) -> Union[gpd.GeoDataFrame, List[gpd.GeoDataFrame]]:
        """
        Convert query result to GeoDataFrame(s)
        
        Args:
            result: Result from query() method
            geometry_column: Name of geometry column (default: 'geom')
        
        Returns:
            - gpd.GeoDataFrame: Non-nested result
            - list[gpd.GeoDataFrame]: Nested result
        """
        if not result:
            return gpd.GeoDataFrame()
        
        # Check if result is nested
        is_nested = isinstance(result[0], list)
        
        if is_nested:
            # Process nested results
            gdf_list = []
            for sub_result in result:
                if sub_result:
                    gdf = self._dict_list_to_gdf(sub_result, geometry_column)
                    gdf_list.append(gdf)
                else:
                    gdf_list.append(gpd.GeoDataFrame())
            
            if self.verbose:
                log.info(f"Converted {len(gdf_list)} nested results to GeoDataFrames")
            
            return gdf_list
        else:
            # Process non-nested result
            gdf = self._dict_list_to_gdf(result, geometry_column)
            
            if self.verbose:
                log.info(f"Converted {len(result)} records to GeoDataFrame")
            
            return gdf
    
    def _dict_list_to_gdf(
        self, 
        dict_list: List[Dict[str, Any]], 
        geometry_column: str
    ) -> gpd.GeoDataFrame:
        """
        Convert list of dicts to GeoDataFrame
        
        Args:
            dict_list: List of dictionaries
            geometry_column: Name of geometry column
        
        Returns:
            GeoDataFrame
        """
        if not dict_list:
            return gpd.GeoDataFrame()
        
        # Convert to DataFrame first
        df = pd.DataFrame(dict_list)
        
        # Handle geometry column
        # Check for common geometry column names
        geom_cols = [col for col in df.columns 
                    if col.lower() in [geometry_column.lower(), 'geom', 'geometry', 'geom_wkt']]
        
        if not geom_cols:
            # No geometry column found, return regular DataFrame as GeoDataFrame
            log.warning(f"No geometry column found matching '{geometry_column}', "
                       f"returning DataFrame without geometry")
            return gpd.GeoDataFrame(df)
        
        # Use the first matching geometry column
        geom_col = geom_cols[0]
        
        # Check if DataFrame is empty
        if len(df) == 0:
            return gpd.GeoDataFrame(df)
        
        # Check if geometry is already a shapely object
        if hasattr(df[geom_col].iloc[0], '__geo_interface__'):
            # Already a geometry object
            gdf = gpd.GeoDataFrame(df, geometry=geom_col)
        else:
            # Try to convert from WKT
            try:
                from shapely import wkt
                df[geom_col] = df[geom_col].apply(lambda x: wkt.loads(x) if isinstance(x, str) else x)
                gdf = gpd.GeoDataFrame(df, geometry=geom_col)
            except Exception as e:
                log.warning(f"Failed to parse geometry from column '{geom_col}': {e}")
                # Return as regular DataFrame
                gdf = gpd.GeoDataFrame(df)
        
        # Set CRS if available in the data or use default
        if gdf.crs is None:
            # Try to infer from geometry or use default
            gdf.set_crs('epsg:4326', allow_override=True)
        
        return gdf

