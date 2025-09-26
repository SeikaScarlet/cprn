# -*- coding : utf-8 -*-
# create date : Sept26'25
# last update : Sept26'25
# author : seika<seika@live.ca>

# cprn/data/postgis.py

from taisl_lib.data.connectionmanager import PullData
from taisl_sop.data.base.sql_builder import SqlClauseBuilder
import geopandas as gpd
from typing import List

class CprnPostgisRetriever:
    def __init__(self, engine_pg):
        self.engine_pg = engine_pg
    
    def get_edges_by_codes(self, tb_name: str, edge_codes: List[str]) -> gpd.GeoDataFrame:
        """根据边代码列表查询边几何数据"""
        if not edge_codes:
            return gpd.GeoDataFrame()
            
        # 使用 SqlClauseBuilder 构建 IN 子句
        edge_condition = SqlClauseBuilder._build_clause_in(edge_codes, 'edge_code')
        
        sql = f"""
        SELECT edge_code, src_vtx, tgt_vtx, rcode, mdir, weight, 
               cls, knd, rtype, lane, con_type, geom
        FROM cprn."{tb_name}"
        WHERE {edge_condition}
        """
    
        return PullData.read_postgis(sql, self.engine_pg, 'geom')