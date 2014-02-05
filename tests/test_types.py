#-*- coding:utf-8 -*-
import unittest
import cello

from datetime import datetime
from cello.exceptions import SchemaError, ValidationError
from cello.types import GenericType, Numeric, Text, Datetime

class TestFieldTypes(unittest.TestCase):
    def setUp(self):
        pass

    def test_generic_type(self):
        f = GenericType()
        self.assertEqual(f.validate("45"), "45")
        self.assertEqual(f.validate(45), 45)
        self.assertEqual(f.validate(str), str)
        
        self.assertEqual(f.parse("45"), "45")

    def test_numeric(self):
        # Numeric Field (int or float)
        f = Numeric(numtype=float)
        self.assertNotEqual(repr(f), "")
        self.assertRaises(SchemaError, lambda: Numeric(numtype=any) )
        self.assertEqual(f.validate(2.), 2.)  # ok
        self.assertEqual(f.validate(-2.2), -2.2)  # ok
        self.assertEqual(f.validate(-5e0), -5.)  # ok
        self.assertEqual(f.validate(0.), 0.)  # ok
        self.assertRaises(ValidationError, f.validate, 1)
        self.assertRaises(ValidationError, f.validate, "1")
        self.assertRaises(ValidationError, f.validate, "blabla")
        self.assertRaises(ValidationError, f.validate, int)
        
        self.assertEqual(f.parse("45"), 45.)

        # unsigned field
        f = Numeric(numtype=int, min=0)
        self.assertEqual(f.validate(2), 2)  # ok
        self.assertEqual(f.validate(0), 0)  # ok
        self.assertRaises(ValidationError, f.validate, -1)
        
        self.assertEqual(f.parse("45"), 45)
        
        # with min and max
        f = Numeric(numtype=int, min=-10, max=45)
        self.assertEqual(f.validate(-10), -10)  # ok
        self.assertEqual(f.validate(0), 0)  # ok
        self.assertEqual(f.validate(2), 2)  # ok
        self.assertEqual(f.validate(45), 45)  # ok
        self.assertRaises(ValidationError, f.validate, -45)
        self.assertRaises(ValidationError, f.validate, 4.5)
        self.assertRaises(ValidationError, f.validate, -11)
        self.assertRaises(ValidationError, f.validate, 55)
        
        
        # with min and max
        f = Numeric(numtype=int, min=0, max=4, help="an int")
        self.assertEqual(f.validate(0), 0)  # ok
        self.assertEqual(f.validate(4), 4)  # ok
        self.assertRaises(ValidationError, f.validate, -1)
        self.assertRaises(ValidationError, f.validate, 8)

    def test_text(self):
        # setting wrong types 
        self.assertRaises(SchemaError, lambda: Text(texttype=any))
        
        # check unicode
        f_unicode = Text(texttype=unicode)
        self.assertNotEqual(repr(f_unicode), "")
        # good type
        self.assertEqual(f_unicode.validate(u"boé"), u'boé')
        self.assertRaises(ValidationError, f_unicode.validate, "boo")
        self.assertRaises(ValidationError, f_unicode.validate, 1)
        
        self.assertEqual(f_unicode.parse("boé"), u'boé')
        self.assertEqual(f_unicode.parse(u"boé"), u'boé')

        # check str
        f_str = Text(texttype=str)
        self.assertNotEqual(repr(f_str), "")
        # good type
        self.assertEqual(f_str.validate("boé"), 'boé')
        self.assertRaises(ValidationError, f_str.validate, u"boo")
        self.assertRaises(ValidationError, f_str.validate, 1)

        self.assertEqual(f_str.parse("boé"), 'boé')
        self.assertEqual(f_str.parse(u"boé"), 'boé')


    def test_datetime(self):
        f = Datetime()
        self.assertRaises(ValidationError, f.validate, "45")
        self.assertEqual(f.validate(datetime(year=2013, month=11, day=4)), \
                datetime(year=2013, month=11, day=4))


