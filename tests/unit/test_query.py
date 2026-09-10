from skein.store import LocalGraphStore
from skein.schema import GraphNode,GraphEdge
from skein.query import query

def test_query_calls():
 s=LocalGraphStore(); s.add_node(GraphNode(id='function:a',type='Function')); s.add_node(GraphNode(id='function:b',type='Function')); s.add_edge(GraphEdge(source='function:a',target='function:b',type='CALLS',attributes={'confidence':'EXTRACTED'}))
 assert 'function:a' in query(s,'what calls function:b?')
