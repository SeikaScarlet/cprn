# -*- coding : utf-8 -*-
# create date : Apr 15th, 25
# last update : Aug 12th, 25
# author : seika<seika@live.ca>

"""
topic : topology search using preprocessed roadrefline network (cprn)
ver : mk2 / adapt from `hdmap.topology.py`
moved from `taisl_sop`
"""


import pandas as pd
import networkx as nx

from loguru import logger as log

from cprn.data.pickle import PickleIO
from cprn.model.dict_query import DictQuery as dq

class CprnTopoSearch:
        """  Roadrefline Network Analyzer
        """
        @staticmethod
        def load_cprn(filepath: str) -> nx.DiGraph:
            """ load preprocessed road refline network (facility may embedded, 
            network is shortened)
            """
            return PickleIO.load_from_pickle(filepath)
        
        @staticmethod
        def list_vtx_fac_df (DG: nx.DiGraph) -> pd.DataFrame:
            """ list vertices of facility in dg as dataframe 
            """
            dct_nodes = dict(DG.nodes(data=True))
            dct_nodes_fac = {k: v for k, v in dct_nodes.items() if v}

            df_fac = pd.DataFrame()
            for fac_vtx, attr in dct_nodes_fac.items():
                df_fac = pd.concat(
                    [df_fac, attr['df_fac_attr']], axis = 0, ignore_index=True)
            
            #df_nodes_fac = pd.DataFrame.from_dict(dct_nodes_fac, orient='index')
            return df_fac
        
        @staticmethod
        def list_fac_interval_df(lst_fac_traveled: list[dict]) -> pd.DataFrame:
            """ list facility interval (list of dict, searched by bfs) as dataframe
            """
            df_fac_interval = pd.DataFrame()
            for fac_traveled in lst_fac_traveled:
                df_fac_interval = pd.concat(
                    [df_fac_interval, fac_traveled['df_fac_attr']], 
                    axis = 0, ignore_index=True)
            return df_fac_interval
        
        @staticmethod
        def query_facility (DG: nx.DiGraph, fac_code: str) -> pd.DataFrame:
            """ query facility by facility code
            """
            df_fac = CprnTopoSearch.list_vtx_fac_df(DG)
            return df_fac.query(f'fac_code == "{fac_code}"')
        
        @staticmethod
        def fac_bfs_depth(DG : nx.DiGraph, start_node: str, 
                          fac_types: list, direction: str, 
                          max_depth: int = 3,
                          max_dist: int = 1000000,
                          mark_max_dist: bool = False,
                          query_avoid_edge: str = None,
                          verbose: bool = False) -> list[dict]:
            """ Facility BFS with given depth limit
            Find all facility nodes of a specified type within a given depth from a start node.
            Return as list of dicts, that contains attributes of the found facility node    
            Parameters:
            - DG: networkx.DiGraph, the directed graph representing the highway network.
            - start_node: node code (12 digits geohash), the starting facility node.
            - fac_types: list of str, the type of facility to search for.
            - direction: str, 'downstream' or 'upstream' to specify search direction.
            - max_depth: int, the maximum depth to search.
            - max_dist: int, the maximum distance to search.
            - mark_max_dist: bool, whether to mark the maximum distance in result.
            - query_avoid_edge: str, the query string to avoid traversing edge.
            - verbose: bool, whether to print the search process.
            Returns:
            - List of dictionaries containing attributes of the found facility 
                nodes, including depth and cumulative weight.
            """
            
                    
            # Choose the appropriate traversal method based on direction
            if direction == 'downstream':
                func_neighb_search = DG.successors
            elif direction == 'upstream':
                func_neighb_search = DG.predecessors
            else:
                raise ValueError("Direction must be 'downstream' or 'upstream'.")
        
            # Initialize search
            set_fac_types = set(fac_types)  # set of fac types to search for
            vtx_visited = set()
            fac_visited = set()
            # set heap of queue : 
            #   current_node, current_fac, depth, interval_weight, cumulative_weight
            queue = [(start_node, start_node, 0, 0, 0)]
            lst_fac_found = []    
            _ = start_node # if _ is the first fac vertex
        
            # 添加以下代码(最小化修改)
            # 特殊处理起点，不受fac_types限制
            if DG.nodes[start_node].get('is_fac', False):
                df_fac_attr = DG.nodes[start_node].get('df_fac_attr')
                if df_fac_attr is not None and not df_fac_attr.empty:
                    dct_found_fac = DG.nodes[start_node].copy()
                    dct_found_fac['vtx_intvl_src'] = start_node
                    dct_found_fac['fac_vtx_tgt'] = start_node
                    dct_found_fac['depth'] = 0
                    dct_found_fac['interval_weight'] = 0
                    dct_found_fac['cumulative_weight'] = 0
                    lst_fac_found.append(dct_found_fac)
                    # 将起点设施代码添加到已访问集合
                    fac_visited = fac_visited | set(df_fac_attr['fac_code'])
                    # 更新queue
                    queue = [(start_node, start_node, 1, 0, 0)]

            # 开始遍历
            while queue:
                current_node, current_fac, depth, interval_weight, cumulative_weight = queue.pop(0)
        
                # Stop Criteria
                if depth > max_depth:
                    log.info(f"depth exceeds max_depth {max_depth}, stop searching") if verbose else None
                    continue
                if cumulative_weight > max_dist:
                    log.info(f"traverse distance exceeds max_dist {max_dist}, stop searching") if verbose else None
                    if mark_max_dist:
                        dct_max_dist_reach = DG.nodes[current_node].copy()
                        dct_max_dist_reach['reach_max_dist'] = True
                        dct_max_dist_reach['df_fac_attr'] = None
                        dct_max_dist_reach['vtx_intvl_src'] = current_fac
                        dct_max_dist_reach['vtx_intvl_tgt'] = current_node
                        # dct_max_dist_reach['vtx_intvl_tgt'] = None
                        dct_max_dist_reach['depth'] = depth
                        dct_max_dist_reach['interval_weight'] = interval_weight
                        dct_max_dist_reach['cumulative_weight'] = cumulative_weight
                        lst_fac_found.append(dct_max_dist_reach)
                    continue

                # Check if the current node is a facility of the specified type
                if DG.nodes[current_node].get('is_fac') and DG.nodes[current_node]['is_fac'] == True:
                    log.info(f"traverse at {current_node} is fac") if verbose else ''
                    # 新代码: 精确过滤指定类型的设施
                    df_fac_attr = DG.nodes[current_node].get('df_fac_attr')
                    # 只保留指定类型的设施记录
                    df_fac_filtered = df_fac_attr[df_fac_attr['fac_type'].isin(set_fac_types)]
                    log.info(f"len df_fac_satisfied: {len(df_fac_filtered)}") if verbose else ''
                    
                    log.info(f"df_fac_filtered empty check: {df_fac_filtered.empty}") if verbose else ''
                    if not df_fac_filtered.empty:
                        # 只使用过滤后的设施代码
                        set_fac_code = set(df_fac_filtered['fac_code'])
                        if set_fac_code.issubset(fac_visited):
                            if verbose:
                                log.info(f"facility {set_fac_code} already visited at {current_node}")
                        else:
                            if verbose:
                                fac_names = set(df_fac_filtered['fac_name'])
                                fac_types = set(df_fac_filtered['fac_type'])
                                log.info(f"facility {set_fac_code} (name: {fac_names}, type: {fac_types}) found at {current_node}")
                            dct_found_fac = DG.nodes[current_node].copy()
                            depth += 1
                            # 更新设施属性为过滤后的数据
                            dct_found_fac['df_fac_attr'] = df_fac_filtered
                            dct_found_fac['vtx_intvl_src'] = current_fac
                            dct_found_fac['vtx_intvl_tgt'] = current_node
                            dct_found_fac['depth'] = depth
                            dct_found_fac['interval_weight'] = interval_weight
                            dct_found_fac['cumulative_weight'] = cumulative_weight
                            if depth > max_depth:
                                dct_found_fac['reach_max_depth'] = True
                            lst_fac_found.append(dct_found_fac)

                            current_fac = current_node
                            interval_weight = 0
                            fac_visited = fac_visited | set_fac_code

                # Add neighbors to the queue for iterative search
                for neighbor in func_neighb_search(current_node):
                    if neighbor not in vtx_visited:
                        vtx_visited.add(neighbor)
                        # Get the weight of the edge from current_node to neighbor
                        if direction == 'downstream':
                            dict_edge = DG[current_node][neighbor]
                            edge_weight = DG[current_node][neighbor].get('weight', 1)  # Default weight is 1 if not specified
                        elif direction == 'upstream':
                            dict_edge = DG[neighbor][current_node]
                            edge_weight = DG[neighbor][current_node].get('weight', 1)  # Default weight is 1 if not specified

                        if query_avoid_edge:
                            dq_edge = dq(dict_edge)
                            if dq_edge.query(query_avoid_edge):
                                if verbose:
                                    log.info(f"Avoid Edge {current_node} -> {neighbor}, {dict_edge}")
                                continue

                        edge_weight = dict_edge.get('weight', 1)
                        queue.append((neighbor, current_fac, depth, 
                                     interval_weight + edge_weight, 
                                     cumulative_weight + edge_weight))  # Update cumulative weight

            return lst_fac_found

        @staticmethod
        def parse_fac_interval_df(lst_fac_topo : list[dict], start_node: str, 
                                cols_fac_attr: list[str] = [
                                    'gh_fac_rp', 'fac_code', 'fac_type', 
                                    'fac_name', 'geom_fac_wgs_3d']
            ) -> pd.DataFrame:
            """ parse facility interval (list of dict, searched by bfs) into dataframe
            
            Parameters:
            - lst_fac_topo: list of dict, facility topology results (searched by bfs)
            - start_node: str, geohash code of starting node of the traversal
            Returns:
            - pd.DataFrame, DataFrame with columns describing facility intervals
            """

            df_bfs_interval = pd.DataFrame(lst_fac_topo)
            df_bfs_interval['vtx_start'] = start_node

            df_fac_ = CprnTopoSearch.list_fac_interval_df(lst_fac_topo)
            df_fac_ = df_fac_[cols_fac_attr]
            df_fac_src = df_fac_.add_suffix('_src')
            df_fac_tgt = df_fac_.add_suffix('_tgt')

            df_interval = pd.merge(
                df_bfs_interval, df_fac_src,
                left_on = 'vtx_intvl_src', right_on = 'gh_fac_rp_src',
                suffixes = ('', '_src'),
                how = 'left')

            df_interval = pd.merge(
                df_interval, df_fac_tgt,
                left_on = 'vtx_intvl_tgt', right_on = 'gh_fac_rp_tgt',
                suffixes = ('', '_tgt'),
                how = 'left')

            return df_interval

        @staticmethod
        def parse_fac_interval_df_v2(lst_fac_topo: list[dict], start_node: str, DG: nx.DiGraph,
                    cols_fac_attr: list[str] = ['gh_fac_rp', 'fac_code', 'fac_type', 
                    'fac_name', 'geom_fac_wgs_3d'],) -> pd.DataFrame:
            """ parse facility interval (list of dict, searched by bfs) into dataframe

            Parameters:
            - lst_fac_topo: list of dict, facility topology results (searched by bfs)
            - start_node: str, geohash code of starting node of the traversal
            Returns:
            - pd.DataFrame, DataFrame with columns describing facility intervals
            """
            # 1. Create initial dataframe with basic columns
            df_bfs_interval = pd.DataFrame(lst_fac_topo)
            df_bfs_interval['vtx_start'] = start_node

            # 2. Get facility dataframe more efficiently
            df_fac_ = CprnTopoSearch.list_vtx_fac_df(DG)
            df_fac_ = df_fac_[cols_fac_attr]
            df_fac_src = df_fac_.add_suffix('_src')
            df_fac_tgt = df_fac_.add_suffix('_tgt')

            df_interval = pd.merge(
                df_bfs_interval, df_fac_src,
                left_on = 'vtx_intvl_src', right_on = 'gh_fac_rp_src',
                suffixes = ('', '_src'),
                how = 'left')

            df_interval = pd.merge(
                df_interval, df_fac_tgt,
                left_on = 'vtx_intvl_tgt', right_on = 'gh_fac_rp_tgt',
                suffixes = ('', '_tgt'),
                how = 'left')

            # 5. Select final columns in desired order
            cols_order = [
                'vtx_start', 'fac_vtx_src', 'fac_vtx_tgt',
                'depth', 'interval_weight', 'cumulative_weight',
                'fac_code_src', 'fac_name_src', 'fac_type_src', 'gh_fac_src',
                'dist_fac_rp_src', 'fac_vtx_type_src',
                'fac_code_tgt', 'fac_name_tgt', 'fac_type_tgt', 'gh_fac_tgt',
                'dist_fac_rp_tgt', 'fac_vtx_type_tgt',]

            # 6. Clean up memory by removing unnecessary columns
            # df_res = df_interval[cols_order].copy()

            return df_interval