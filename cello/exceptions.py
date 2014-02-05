#-*- coding:utf-8 -*-
""" :mod:`cello.exceptions`
==========================

:copyright: (c) 2013 - 2014 by Yannick Chudy, Emmanuel Navarro.
:license: ${LICENSE}

Class
-----

"""

class SchemaError(Exception):
    """ Error
    
    #TODO: précissé le docstr, c'est quoi quand on a cette erreur exactement ?
    """
    pass


class ValidationError(Exception):
    """An error while validating data of a given type.
    
    It may be either a single validation error or a list of validation error
    
    >>> from cello.utils.i18n import _
    >>> error = ValidationError(_("a message with a value : %(value)s"), {'value': 42})
    >>> for err in error: print err
    a message with a value : 42

    """

    def __init__(self, message, params=None):
        super(ValidationError, self).__init__(message, params)
        #
        if isinstance(message, list):
            self.error_list = []
            for error in message:
                # Normalize plain strings to instances of ValidationError.
                if not isinstance(error, ValidationError):
                    error = ValidationError(error)
                self.error_list.extend(error.error_list)
        else:
            self.message = message
            self.params = params
            self.error_list = [self]

    def __iter__(self):
        for error in self.error_list:
            message = error.message
            if error.params:
                message %= error.params
            yield message

    def __str__(self):
        return repr(list(self))

    def __repr__(self):
        return 'ValidationError(%s)' % self