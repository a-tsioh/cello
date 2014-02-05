#-*- coding:utf-8 -*-
""" :mod:`cello.optionable`
==========================

:copyright: (c) 2013 - 2014 by Yannick Chudy, Emmanuel Navarro.
:license: ${LICENSE}

Management of optionable processing component.


inheritance diagrams
--------------------

.. inheritance-diagram:: Optionable
.. inheritance-diagram:: AbstractOption  AbstractOption  BooleanOption EnumOption

Class
-----
"""
import logging

from cello.types import GenericType, Numeric


class ValueOption(object):
    """ Single value option
    """
    
    @staticmethod
    def FromType(name, otype):
        """ ValueOption subclasses factory, creates a convenient option to store
        data from a given Type.

        attribute precedence :
        
        * ``|attrs| > 0`` (``multi`` and ``uniq`` are implicit) => VectorField
        * ``uniq`` (``multi`` is implicit) => SetField 
        * ``multi`` and ``not uniq`` => ListField 
        * ``not multi`` => ValueField
        
        :param name: Name of the option
        :type name: str
        :param otype: the desired type of field
        :type otype: subclass of :class:`.GenericType`
        """
        if otype.attrs is not None and len(otype.attrs):
            raise NotImplementedError("for otype, options can't have attributs")
            #return VectorField(ftype)
        elif otype.uniq:
            raise NotImplementedError("for now, options can't be set of values")
            #return SetField(ftype)
        elif otype.multi:
            raise NotImplementedError("for now, options can't have multiple values")
            #return ListField(ftype)
        else:
            return ValueOption(name, otype)
    
    def __init__(self, name, otype):
        """
        :param name: option name
        :type name: str
        :param otype: option type
        :type otype: subclass of :class:`.GenericType`
        
        """
        assert isinstance(otype, GenericType)
        # declare attributes with properties
        self._name = None
        self._value = None
        #Note default value is stored in the self.otype
        # set attributs
        self.name = name
        self.otype = otype
        self.hidden = False

    @property
    def name(self):
        """ Name of the option. """
        return self._name

    @name.setter
    def name(self, name):
        """ Set name of the option.
        An option name can't contain space. """
        if ' ' in name:
            raise ValueError("Option's name should not contain space '%s'" % name)
        self._name = name

    @property
    def value(self):
        """ Value of the option
        """
        if self._value is None:
            return self.default
        return self._value

    @value.setter
    def value(self, value):
        if self.hidden:
            raise ValueError("This option is hidden, you can't change the value")
        self._value = self.validate(value)

    @property
    def default(self):
        """ Default value of the option
        
        .. warning:: changing the default value also change the current value
        """
        return self.otype.default

    @default.setter
    def default(self, value):
        self.otype.default = self.validate(value)
        self.value = value

    def validate(self, value):
        """ Raises :class:`.ValidationError` if the value is not correct, else
        just returns the given value.

        It is called when a new value is setted.

        :param value: the value to validate
        :returns: the value
        """
#        print self.otype.validators
        return self.otype.validate(value)

    def parse(self, value_str):
        """ Convert the value from a string.

        :param value_str: a potential value for the option
        :type value_str: str
        :returns: the value converted to the good type
        """
        return self.otype.parse(value_str)

    def set(self, value, parse=False):
        """ Set the value of the option.
        
        One can also set the 'value' property:

        >>> opt = ValueOption("oname", Numeric(default=1,help="an option exemple"))
        >>> opt.value = 12
        
        :param value: the new value
        """
        self.value = self.parse(value) if parse else value

    def as_dict(self):
        """ returns a dictionary view of the option
        
        :returns: the option converted in a dict
        :rtype: dict
        """
        opt_info = {}
        opt_info["type"] = "value"
        opt_info["name"] = self.name
        opt_info["value"] = self.value
        opt_info["otype"] = self.otype.as_dict()
        #TODO: est-ce que l'on ne met pas a plat et les attr de otype et ceux de l'option
        return opt_info

