#-*- coding:utf-8 -*-
import unittest

import json
from flask import Flask

from cello.pipeline import Optionable
from cello.engine import Engine
from cello.types import Numeric
from cello.exceptions import ValidationError

from cello.utils.web import CelloFlaskView

class OptProductEx(Optionable):
    def __init__(self, name="mult_opt"):
        super(OptProductEx, self).__init__(name)
        self.add_option("factor", Numeric(default=5, help="multipliation factor", vtype=int))

    def __call__(self, arg, factor=5):
        return arg * factor


class TestCelloFlaskView(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.engine = Engine("op1", "op2")
        self.engine.op1.setup(in_name="in")
        self.engine.op2.setup(out_name="out")

        self.engine.op1.set(OptProductEx())
        
        foisdouze = OptProductEx("foisdouze")
        foisdouze.force_option_value("factor", 12)
        self.engine.op2.set(foisdouze, OptProductEx())

        api = CelloFlaskView(self.engine)
        api.set_input_type(Numeric(vtype=int, min=-5, max=5))
        api.add_output("out")

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api, url_prefix="/api")
        self.app = app.test_client()

    def test_options(self):
        resp = self.app.get('api/options')
        data = json.loads(resp.data)
        # check we have the same than in engine
        self.assertListEqual(data["blocks"], self.engine.as_dict()["blocks"])
        self.assertEqual(data["args"], ["in"])
        self.assertListEqual(data["returns"], ["out"])

    def test_play_simple(self):
        # prepare query
        rdata = {'in': 2}
        json_data = json.dumps(rdata)
        resp = self.app.get('api/play', data=json_data, content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        self.assertTrue("results" in resp_data)
        results = resp_data["results"]
        self.assertTrue("out" in results)
        self.assertEquals(len(results), 1)
        self.assertEquals(results["out"], 2*5*12)

    def test_play_fail(self):
        json_data = json.dumps({'in': 10})
        with self.assertRaises(ValidationError):
            resp = self.app.get('api/play', data=json_data, content_type='application/json')

        json_data = json.dumps({'in': "chat"})
        with self.assertRaises(ValueError):
            resp = self.app.get('api/play', data=json_data, content_type='application/json')

        json_data = json.dumps({'in': 1})
        resp = self.app.get('api/play', data=json_data)
        # error 415 "Unsupported Media Type" see:
        # http://en.wikipedia.org/wiki/List_of_HTTP_status_codes#4xx_Client_Error
        self.assertEquals(resp.status_code, 415)

    def test_play_simple_options(self):
        # prepare query
        rdata = {'in': 2}
        rdata["options"] = {
            'op2': [{
                'name': 'mult_opt',
                'options': {
                    'factor': '2'
                }
            }]
        }
        json_data = json.dumps(rdata)
        resp = self.app.get('api/play', data=json_data, content_type='application/json')
        # load the results
        resp_data = json.loads(resp.data)
        # check it
        self.assertTrue("results" in resp_data)
        results = resp_data["results"]
        self.assertTrue("out" in results)
        self.assertEquals(len(results), 1)
        self.assertEquals(results["out"], 2*2*5)

