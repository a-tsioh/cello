#!/usr/bin/env python
#-*- coding:utf-8 -*-
import logging
import itertools

from cello.pipeline import GraphPipelineElement 


class BottomFilter(GraphPipelineElement):
    """
    Removes bottom vertices from a bigraph.
    """
    def __init__(self):
        name = self.__class__.__name__
        GraphPipelineElement.__init__(self, name)
        self._logger = logging.getLogger(name)

        self.add_option("top_min",
            "0", 
            "Removes type=false connected to less than top_min (type=True) vertices",
            int)
        self.add_option("top_max_ratio",
            "1.0",
            "Removes type false vertices connected to more than top_max_ratio percents of the (type=True) vertices",
            float)
            
            
    def __call__(self, graph, top_min=0, top_max_ratio=1., **kwargs):
        """
            remove bottoms (type false) vertices,
            that are not enought connected or too much connected.
            :param top_min: <int> 
                removes v[false] if  degree(g,v[false]) <= top_min  
            :param top_max_ratio: <float> % of top vertices  
                removes v[false] if degree(g,v[false]) > top_max_ratio 
        """
        assert graph.is_bipartite();
        
        top_count = len(graph.vs.select(type=True))
        
        self._logger.info("Before filtering: |V_top docs|=%d, |V_bottom terms|=%d, |E|=%d"\
             % (len(graph.vs.select(type=True)), len(graph.vs.select(type=False)), graph.ecount()))
        
        too_poor_bots = graph.vs.select(type=False, _degree_le=top_min)
        
        self._logger.info("%d bottoms have less than %s neighbors, will be deleted" % (len(too_poor_bots), top_min))
        
        too_rich_bots = graph.vs.select(type=False, _degree_gt=top_max_ratio * top_count)
        
        self._logger.info("%d bottoms have more than %s neighbors (%1.2f * %d), will be deleted"\
             % (len(too_rich_bots), top_max_ratio * top_count, top_max_ratio, top_count))
        
        graph.delete_vertices(itertools.chain(too_poor_bots, too_rich_bots))
        
        self._logger.info("After filtering: |V_top|=%d, |V_bottom|=%d, |E|=%d" \
            % (len(graph.vs.select(type=True)), len(graph.vs.select(type=False)), graph.ecount()))
        return graph
