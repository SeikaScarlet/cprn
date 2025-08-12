# -*- coding : utf-8 -*-
# create date : Nov 26th, 24
# last update : Nov 26th, 24
# author : Seika/Claude-3.5-sonnet
# topic : dict data manipulation
# ver : mk1



import ast
import operator

class DictQuery:
    """
    A class for querying dictionary data using string expressions.

    This class provides functionality to filter dictionary data using query strings
    similar to pandas query syntax. It supports various comparison operators,
    boolean operations, and list operations.

    Attributes:
        data (dict): The dictionary to be queried
        ops (dict): Mapping of AST operators to their corresponding functions

    Supported Operations:
        - Comparison: ==, >, <, >=, <=, !=
        - Boolean: and, or
        - List: in, not in
        
    Examples:
        >>> data = {'age': 25, 'name': 'John', 'type': 'A'}
        >>> dq = DictQuery(data)
        >>> dq.query("age > 20 and type == 'A'")
        True
        >>> dq.query("name in ['John', 'Jane']")
        True
    """
    def __init__(self, data_dict):
        """
        Initialize the DictQuery instance.

        Args:
            data_dict (dict): The dictionary to be queried
        """
        self.data = data_dict
        self.ops = {
            ast.Eq: operator.eq,
            ast.Gt: operator.gt,
            ast.Lt: operator.lt,
            ast.GtE: operator.ge,
            ast.LtE: operator.le,
            ast.NotEq: operator.ne,
            ast.And: operator.and_,
            ast.Or: operator.or_,
            ast.In: lambda x, y: x in y,      # 添加 in 操作符支持
            ast.NotIn: lambda x, y: x not in y # 添加 not in 操作符支持
        }

    def _eval(self, node):
        """
        Evaluate an AST node recursively.

        This internal method traverses the Abstract Syntax Tree and evaluates
        each node according to its type.

        Args:
            node (ast.AST): The AST node to evaluate

        Returns:
            bool: Result of the evaluation

        Raises:
            ValueError: If an unsupported operation is encountered
        """
        # 处理比较操作
        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, comp in zip(node.ops, node.comparators):
                right = self._eval(comp)
                if not self.ops[type(op)](left, right):
                    return False
                left = right
            return True

        # 修改布尔操作的处理
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result = True
                for value in node.values:
                    result = result and self._eval(value)
                    if not result:  # 短路求值
                        break
                return result
            elif isinstance(node.op, ast.Or):
                result = False
                for value in node.values:
                    result = result or self._eval(value)
                    if result:  # 短路求值
                        break
                return result
            else:
                raise ValueError(f"Unsupported boolean operation: {type(node.op)}")

        # 处理变量名
        elif isinstance(node, ast.Name):
            return self.data.get(node.id)

        # 处理常量
        elif isinstance(node, ast.Constant):
            return node.value

        # 处理列表
        elif isinstance(node, ast.List):
            return [self._eval(elt) for elt in node.elts]

        raise ValueError(f"Unsupported operation: {type(node)}")

    def query(self, query_str):
        """
        Execute a query string against the dictionary data.

        Args:
            query_str (str): The query string to evaluate. Can include spaces
                at beginning or end.

        Returns:
            bool: True if the query conditions are met, False otherwise

        Examples:
            >>> dq.query("age > 20")
            >>> dq.query("type in ['A', 'B'] and age <= 30")
            >>> dq.query(" name == 'John' ")  # Spaces are handled

        Raises:
            Exception: If there's an error in query parsing or evaluation
        """
        try:
            # 清理查询字符串
            query_str = query_str.strip()
            tree = ast.parse(query_str, mode='eval')
            return self._eval(tree.body)
        except Exception as e:
            print(f"Query error: {e}")
            return False