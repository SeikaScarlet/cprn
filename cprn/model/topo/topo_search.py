# -*- coding : utf-8 -*-
# create date : Apr 15th, 25
# last update : Sept11‘25
# author : seika<seika@live.ca>

"""
topic : topology search using preprocessed roadrefline network (cprn)
ver : mk2 / adapt from `hdmap.topology.py`
moved from `taisl_sop`
"""


import itertools
import pandas as pd
import networkx as nx

from loguru import logger as log

# from taisl_sop.util.decorators import deprecated

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
            """ list vertices of facility in dg as dataframe (deprecated)
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
        def list_fac_df(DG: nx.DiGraph) -> pd.DataFrame:
            """ list embeded facility in cprn(dg) as dataframe
            """
            # 过滤设施节点并提取lst_fac_attr
            dct_nodes_fac = {k: v for k, v in DG.nodes(data=True) if v.get('is_fac', False)}
            # 使用列表推导式提取所有lst_fac_attr，然后用chain展平
            all_fac_records = list(itertools.chain.from_iterable(
                attr.get('lst_fac_attr', []) for attr in dct_nodes_fac.values()))

            return pd.DataFrame(all_fac_records)

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
            df_fac = CprnTopoSearch.list_fac_df(DG)
            return df_fac.query(f'fac_code == "{fac_code}"')

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
                left_on = 'vtx_intvl_src', 
                # right_on = 'gh_fac_rp_src',
                right_on = 'vtx_fac_src',
                suffixes = ('', '_src'),
                how = 'left')

            df_interval = pd.merge(
                df_interval, df_fac_tgt,
                left_on = 'vtx_intvl_tgt', 
                # right_on = 'gh_fac_rp_tgt',
                right_on = 'vtx_fac_tgt',
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

# ------ Refactored Version (as of Sep15'25) ------

        @staticmethod
        def fac_bfs_depth(DG: nx.DiGraph, start_node: str, 
                      fac_types: list, direction: str, 
                      max_depth: int = 3, max_dist: int = 1000000,
                      mark_max_dist: bool = False,
                      query_avoid_fac: list = None,
                      query_avoid_edge: str = None, 
                      edge_code_attr: str = 'edge_code',
                      version: str = 'v2',
                      verbose: bool = False,
                      **kwargs) -> list[dict]:
            """ Universal Facility BFS with intelligent parameter adaptation """
            
            # 版本函数映射
            version_functions = {
                'v1': CprnTopoSearch.fac_bfs_depth_v1,
                'v2': CprnTopoSearch.fac_bfs_depth_v2,
            }
            
            if version not in version_functions:
                available_versions = list(version_functions.keys())
                raise ValueError(f"Version '{version}' not supported. Available versions: {available_versions}")
            
            log.info(f"Using version {version} of `fac_bfs_depth`")
            func = version_functions[version]
            
            # 获取函数的参数签名
            import inspect
            sig = inspect.signature(func)
            func_params = set(sig.parameters.keys())
            
            # 准备所有可能的参数
            all_params = {
                'DG': DG,
                'start_node': start_node,
                'fac_types': fac_types,
                'direction': direction,
                'max_depth': max_depth,
                'max_dist': max_dist,
                'mark_max_dist': mark_max_dist,
                'query_avoid_fac': query_avoid_fac,
                'query_avoid_edge': query_avoid_edge,
                'edge_code_attr': edge_code_attr,
                'verbose': verbose,
                **kwargs
            }
            
            # 只传递函数支持的参数
            filtered_params = {k: v for k, v in all_params.items() 
                              if k in func_params}
            
            # 检查必需参数
            required_params = {name for name, param in sig.parameters.items() 
                              if param.default == inspect.Parameter.empty}
            missing_params = required_params - set(filtered_params.keys())
            
            if missing_params:
                raise TypeError(f"Missing required parameters for {version}: {missing_params}")
            
            return func(**filtered_params)


        @staticmethod
        def fac_bfs_depth_v1(DG : nx.DiGraph, start_node: str, 
                          fac_types: list, direction: str, 
                          max_depth: int = 3, max_dist: int = 1000000,
                          mark_max_dist: bool = False,
                          query_avoid_fac: list = None,
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
        def fac_bfs_depth_v2(DG : nx.DiGraph, start_node: str, 
                          fac_types: list , direction: str, 
                          max_depth: int = 3, max_dist: int = 1000000,
                          mark_max_dist: bool = False,
                          query_avoid_fac: list = None,
                          query_avoid_edge: str = None, 
                          edge_code_attr: str = 'edge_code', # 边编号列名
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
            set_fac_avoid = set(query_avoid_fac) if query_avoid_fac else set()
            vtx_visited = set()
            fac_visited = set()

            # Setup heap of queue : 
            # current_node, current_fac, depth, interval_weight, cumulative_weight, interval_edges, cumulative_edges
            queue = [(start_node, start_node, 0, 0, 0, [], [])]
            lst_fac_found = []

            # If start node is a suitable facility
            if (set_fac_types.intersection(DG.nodes[start_node].get('fac_types', set()))):
                lst_fac_attr_start = DG.nodes[start_node].get('lst_fac_attr', [])
                lst_fac_start_fit = [fac for fac in lst_fac_attr_start if fac['fac_type'] in set_fac_types]

                if set_fac_avoid:
                    lst_fac_start_fit = [fac for fac in lst_fac_start_fit if fac['fac_code'] not in set_fac_avoid]
                    if verbose:     # log facilities to avoid
                        lst_fac_avoid = [fac for fac in lst_fac_start_fit if fac['fac_code'] in set_fac_avoid]
                        log.info(f"Facilities to avoid: {lst_fac_avoid}") if len(lst_fac_avoid) > 0 else None

                for fac in lst_fac_start_fit:
                    dct_fac_traveled = {'depth': 0,  # Start depth is 0
                        'vtx_intvl_src': start_node, 'vtx_intvl_tgt': start_node,
                        'interval_weight': 0, 'cumulative_weight': 0, 
                        'interval_edges': [], 'cumulative_edges': [], **fac,}
                    lst_fac_found.append(dct_fac_traveled)
                    fac_visited.add(fac['fac_code'])
                queue = [(start_node, start_node, -1, 0, 0, [], [])]    # Update queue 😄
                log.info(f"Start node {start_node} is a suitable facility, add as depth 0 😄") if verbose else None

            # 开始遍历
            while queue:
                current_node, passed_fac_vtx, depth, interval_weight, cumulative_weight, interval_edges, cumulative_edges = queue.pop(0)
                # Stop Criteria Check
                if depth > max_depth:
                    log.info(f"📛 Stop Criteria Activated: Max depth exceeds {max_depth}, stop searching at {current_node}") if verbose else None
                    continue
                if cumulative_weight > max_dist:
                    log.info(f"📛 Stop Criteria Activated: Traverse distance exceeds {max_dist}, stop searching at {current_node}") if verbose else None
                    if mark_max_dist:
                        dct_final_vtx = {'depth': depth, 'vtx_intvl_src': passed_fac_vtx, 'vtx_intvl_tgt': current_node,
                            'interval_weight': interval_weight, 'cumulative_weight': cumulative_weight,
                            'interval_edges': interval_edges, 'cumulative_edges': cumulative_edges,
                            'reach_max_dist': True,}
                        lst_fac_found.append(dct_final_vtx)
                    continue

                # Check if the current node is a target facility
                if set_fac_types.intersection(DG.nodes[current_node].get('fac_types', set())):
                    # log.info(f"traverse at {current_node} is a fac") if verbose else ''
                    lst_fac_attr_ = DG.nodes[current_node].get('lst_fac_attr', [])
                    lst_fac_attr_type_fit = [fac for fac in lst_fac_attr_ if fac['fac_type'] in set_fac_types]

                    # filter out facilities to avoid
                    if set_fac_avoid:
                        if verbose:
                            lst_fac_avoid = [fac for fac in lst_fac_attr_type_fit if fac['fac_code'] in set_fac_avoid]
                            log.info(f"⛔️ Avoided Facilities: {lst_fac_avoid}") if len(lst_fac_avoid) > 0 else None
                        lst_fac_attr_type_fit = [fac for fac in lst_fac_attr_type_fit if fac['fac_code'] not in set_fac_avoid]

                    if len(lst_fac_attr_type_fit) != 1:
                        log.info(f"⚠️ found irregular number {len(lst_fac_attr_type_fit)} of fac binded to vtx {current_node}") if verbose else None
                    if lst_fac_attr_type_fit:
                        depth += 1
                        if depth > max_depth:
                            log.info(f"📛 Stop Criteria Activated: Max depth exceeds {max_depth}, stop searching at {current_node}") if verbose else None
                            continue

                    for fac in lst_fac_attr_type_fit:
                        if fac['fac_code'] not in fac_visited:
                            log.info(f"🏰 Facility {fac['fac_code']} at vtx {current_node} found") if verbose else ''
                            # prepare fac data for output
                            dct_fac_traveled = {
                                'depth': depth, 'vtx_intvl_src': passed_fac_vtx, 'vtx_intvl_tgt': current_node,
                                'interval_weight': interval_weight, 'cumulative_weight': cumulative_weight,
                                'interval_edges': interval_edges, 'cumulative_edges': cumulative_edges,
                                'reach_max_depth': depth >= max_depth,
                                **fac}
                            # append fac data to putput
                            lst_fac_found.append(dct_fac_traveled)
                            # update fac visited
                            fac_visited.add(fac['fac_code'])
                            passed_fac_vtx = current_node
                            interval_weight = 0
                            interval_edges = []

                        else:   # already visited
                            log.info(f"🏰 Facility {fac['fac_code']} at vtx {current_node} found but already visited") if verbose else ''
                            # necessary update
                            # passed_fac_vtx = current_node
                            # interval_weight = 0

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
                                    log.info(f"🚫 Avoid Edge {current_node} -> {neighbor}, {dict_edge}")
                                continue

                        edge_weight = dict_edge.get('weight', 1)
                        current_edge_code = dict_edge.get(edge_code_attr, None) # 获取当前边编号
                        
                         # 创建新的边列表
                        new_interval_edges = interval_edges.copy()
                        new_cumulative_edges = cumulative_edges.copy()
                        if current_edge_code is not None:
                            new_interval_edges.append(current_edge_code)
                            new_cumulative_edges.append(current_edge_code)

                        queue.append((neighbor, passed_fac_vtx, depth, 
                                     interval_weight + edge_weight, 
                                     cumulative_weight + edge_weight,
                                     new_interval_edges,
                                     new_cumulative_edges))  # Update cumulative weight
            return lst_fac_found
