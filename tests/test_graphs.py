import unittest
import igraph

import cello
from cello.providers.igraphGraph import IgraphGraph
from cello.graphs import random_vertex, read_json, export_graph
from cello.schema import Doc

class TestGraph(unittest.TestCase):
    
    def setUp(self):
        
        self.formula = IgraphGraph.Formula("a--b, a--c, a--d, a--f, d--f")
        self.formula.vs["docnum"] = ["%d" % vid if vid%2 == 0 else None 
                                    for vid in range(self.formula.vcount())]
        
        self.expect = {'attributes': {
                    'bipartite': False,
                    'directed': False,
                    'e_attrs': [],
                    'v_attrs': ['docnum', 'name']
                    },
                 'es': [{'s': 0, 't': 1},
                        {'s': 0, 't': 2},
                        {'s': 0, 't': 3},
                        {'s': 0, 't': 4},
                        {'s': 3, 't': 4}],
                 'vs': [{'_id': 0, 'docnum': '0', 'name': 'a'},
                        {'_id': 1, 'docnum': None, 'name': 'b'},
                        {'_id': 2, 'docnum': '2', 'name': 'c'},
                        {'_id': 3, 'docnum': None, 'name': 'd'},
                        {'_id': 4, 'docnum': '4', 'name': 'f'}]
                }

    def test_should_serialize_to_json(self):
        self.assertDictEqual(export_graph(self.formula), self.expect)

    def test_should_serialize_graph_with_doc_to_json(self):
        self.maxDiff = None
        g = IgraphGraph.Formula("a--b, a--c, a--d, a--f, d--f")
        g.vs["_doc"] = [Doc(docnum= "%d" % vid) if vid%2 == 0 else None 
                            for vid in range(g.vcount())]
        self.assertDictEqual(export_graph(g), self.expect)
        
        
    def test_should_read_json(self):
        graph = read_json(self.expect)

        self.assertEqual(graph.vs['name'], self.formula.vs['name'])
        self.assertEqual(graph.vcount(), self.formula.vcount())
        self.assertEqual(graph.ecount(), self.formula.ecount())
    
    def test_should_select_random_vertex(self):
        vid = random_vertex(self.formula) 
        vertex = self.formula.vs[vid]
        self.assertTrue('docnum' in vertex.attributes())
