#-*- coding:utf-8 -*-
""" :mod:`cello.engine`
========================

Cello processing system
^^^^^^^^^^^^^^^^^^^^^^^

code sample
~~~~~~~~~~~

Here is a simple exemple of Cellist usage. First you need to setup your Cellist:

>>> from cello.engine import Engine
>>> cellist = Engine()
>>> cellist.requires('foo', 'bar', 'boo')

one can make imaginary components:

>>> from cello.pipeline import Pipeline, Optionable, Composable
>>> from cello.types import Numeric
>>> class One(Optionable):
...     def __init__(self):
...         super(One, self).__init__(name="one")
...         self.add_option("val", Numeric(default=1))
... 
...     @Optionable.check
...     def __call__(self, input, val=None):
...         return input + val
... 
>>> one = One()
>>> two = Composable(name="two", func=lambda x: x*2)
>>> three = Composable(lambda x: x - 2) | Composable(lambda x: x/2.)
>>> three.name = "three"

one can configure a block with this three components:

>>> foo_comps = [one, two, three]
>>> foo_options = {'defaults': 'two'}
>>> cellist.set('foo', *foo_comps, **foo_options)

or

>>> cellist['bar'].setup(multiple=True)
>>> cellist['bar'].append(two, default=True)
>>> cellist['bar'].append(three, default=True)

or

>>> cellist["boo"].set(two, three)
>>> cellist["boo"].setup(multiple=True)
>>> cellist["boo"].defaults = [comp.name for comp in (two, three)]

One can have the list of all configurations:

>>> from pprint import pprint
>>> pprint(cellist.as_dict())
{'args': None,
 'blocks': [{'args': None,
             'components': [{'default': False,
                             'name': 'one',
                             'options': [{'name': 'val',
                                          'otype': {'choices': None,
                                                    'default': 1,
                                                    'help': '',
                                                    'max': None,
                                                    'min': None,
                                                    'multi': False,
                                                    'type': 'Numeric',
                                                    'uniq': False,
                                                    'vtype': 'int'},
                                          'type': 'value',
                                          'value': 1}]},
                            {'default': True,
                             'name': 'two',
                             'options': None},
                            {'default': False,
                             'name': 'three',
                             'options': []}],
             'multiple': False,
             'name': 'foo',
             'required': True,
             'returns': 'foo'},
            {'args': None,
             'components': [{'default': True,
                             'name': 'two',
                             'options': None},
                            {'default': True,
                             'name': 'three',
                             'options': []}],
             'multiple': True,
             'name': 'bar',
             'required': True,
             'returns': 'bar'},
            {'args': None,
             'components': [{'default': True,
                             'name': 'two',
                             'options': None},
                            {'default': True,
                             'name': 'three',
                             'options': []}],
             'multiple': True,
             'name': 'boo',
             'required': True,
             'returns': 'boo'}]}



And then you can configure and run it:

>>> request_options = {
...     'foo':[
...         {
...             'name': 'one',
...             'options': {
...                 'val': 2
...             }
...        },     # input + 2
...     ],
...     'bar':[
...         {'name': 'two'},
...     ],     # input * 2
...     'boo':[
...         {'name': 'two'},
...         {'name': 'three'},
...     ], # (input - 2) / 2.
... }
>>> cellist.configure(request_options)
>>> # test before running:
>>> cellist.validate()

One can then run only one block:

>>> cellist['boo'].play(10)
4.0

or all blocks :

>>> res = cellist.play(4)
>>> res['foo']      # 4 + 2
6
>>> res['bar']      # 6 * 2
12
>>> res['boo']      # (12 - 2) / 2.0
5.0

"""

import time
import logging
import warnings
import itertools
from collections import OrderedDict

from cello.exceptions import CelloError
from cello.pipeline import Pipeline, Optionable, Composable

#XXX move it in cello/__init__
def define_logger(init):
    from functools import wraps
    @wraps(init)
    def wrapinit(self, *args, **kwargs):
        self._logger = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        init(self, *args, **kwargs)
    return wrapinit 


class Result(object):
    """ Block result metadata
    """
    def __init__(self, block):
        self.name = block.name
        self.multiple = block.multiple
        self.hidden = block.hidden
        self.components = {}
        self.outputs = []

    def walltime(self):
        """ Block computation time
        """
        return sum(c['time'] for c in self.components)

    @property
    def errors(self):
        """ Views on components errors
        """
        errors = (c['errors'] for c in self.components)
        return list(itertools.chain.from_iterable(errors))

    @property
    def warnings(self):
        """ Views on components warnings
        """
        warnings = (c['warnings'] for c in self.components)
        return list(itertools.chain.from_iterable(warnings))

    @property
    def has_error(self):
        """ wether any error happened in component  """
        return len(self.errors)

    @property
    def has_warning(self):
        return len(self.warnings) > 0


class Block(object):
    """ A block is a processing step realised by one component.

    A component is a callable object that has a *name* attribute,
    often it is also a :class:`.Optionable` object or a pipeline beeing a :class:`.Composable` .

    Block object provides methods to discover and parse components options (if any).
    """

    #TODO: ajout validation de type sur input/output
    @define_logger
    def __init__(self, name):
        """ Intialise a block. This should be done only from the :class:`.Engine`.

        :param name: name of the Block
        :type name: str
        """
        # declare attributs
        self._name = None 
        self._selected = []
        self._components = None
        # note: the componants options values are stored in the components
        # name
        self.name = name
        # input output
        self.in_name = None
        self.out_name = self.name
        # default value for component options
        self.required = True
        self.hidden = False
        self.multiple = False
        self._defaults = []
        #handle results meta
        self.meta = Result(self)

        self.reset()
        # Attrs used to build a result object
        self.has_run = False

    @property
    def name(self):
        """Name of the optionable component"""
        return self._name

    @name.setter
    def name(self, name):
        if not isinstance(name, basestring):
            raise ValueError("Block name should be a string")
        if ' ' in name:
            raise ValueError("Block name should not contain space")
        self._name = name

    def __len__(self):
        """ returns the count of components of the given name
        """
        return len(self._components)

    def __iter__(self):
        """ iterate over all components
        """
        return self._components.itervalues()

    def __getitem__(self, name):
        """ returns the component of the given name
        """
        return self._components[name]

    def __contains__(self, name):
        """ returns whether a component of the given name exists
        """
        return name in self._components

    def component_names(self):
        """ returns the list of component names.
        
        Component names will have the same order than components
        """
        return self._components.keys()

    @property
    def defaults(self):
        """ component selected by default
        """
        default = self._defaults
        # if require and no default, th first component as default
        if not len(default) and self.required and len(self._components):
            default = [self._components.itervalues().next().name]
        return default

    @defaults.setter
    def defaults(self, defaults):
        if isinstance(defaults, basestring):
            defaults = [defaults]
        for comp_name in defaults:
            if not comp_name in self._components:
                raise ValueError("Component '%s' doesn't exist it can be set as default." % comp_name)
        self._defaults = defaults

    def selected(self):
        """ returns the list of selected component names.

        if no component selected return the one marked as default.
        If the block is required and no component where indicated as default,
        then the first component is selected.
        """
        selected = self._selected
        if len(self._selected) == 0: # nothing has been selected yet
            selected = self.defaults
        return selected

    def as_dict(self):
        """ returns a dictionary representation of the block and of all
        component options
        """
        #TODO/FIXME: add selected information
        if self.hidden:
            rdict = {}
        else:
            def_selected = self.selected()
            comps = [
                {
                    'name': comp.name,
                    'default': comp.name in self.defaults,
                    'options': comp.get_ordered_options() if isinstance(comp, Optionable) else None
                }
                for comp in self
            ]
            rdict = {
                'name': self.name,
                'required': self.required,
                'multiple': self.multiple,
                'args': self.in_name,
                'returns': self.out_name,
                'components': comps
            }
        return rdict

    def reset(self):
        """ Removes all the components of the block
        """
        self._components = OrderedDict()
        self.clear_selections()

    def clear_selections(self):
        """ Reset the current selections and **reset option** values to default
        for all components
        
        .. Warning:: This method also reset the components options values to
            the defaults values.
        """
        self._selected = []
        for component in self._components.itervalues():
            if isinstance(component, Optionable):
                self._logger.info("'%s' clear selection an options for '%s'" % (self.name, component.name))
                component.clear_options_values()

    def setup(self, in_name=None, out_name=None, required=None, hidden=None,
                multiple=None, defaults=None):
        """ Set the options of the block.
        Only the not None given options are set
        
        :param in_name: name of the block input data
        :type in_name: str
        :param out_name: name of the block output data
        :type out_name: str
        :param required: whether the block will be required or not
        :type required: bool
        :param hidden: whether the block will be hidden to the user or not
        :type hidden: bool
        :param multiple: if True more than one component may be selected/ run) 
        :type multiple: bool
        :param defaults: names of the selected components
        :type defaults: list of str, or str
        """
        if in_name is not None:
            self.in_name = in_name if type(in_name) ==list else [in_name] 
        if out_name is not None:
            self.out_name = out_name
        if required is not None:
            self.required = required
        if hidden is not None:
            self.hidden = hidden
        if multiple is not None:
            self.multiple = multiple
        if defaults is not None:
            #FIXME: what it default is just a 'str'
            self.defaults = defaults

        # TODO depends
        # self.depends = depends # *dependence_block_names  

    def set(self, *components):
        """ Set the possible components of the block
        
        :param components: components to append Optionables or Composables
        """
        self._logger.info("'%s' set components: \n\t%s", self.name, "\n\t".join(("'%s':%s" % (e.name, e) for e in components)))
        self.reset()
        if len(components) == 1:
            self.append(components[0])
        else:
            for comp in components:
                self.append(comp)

    def append(self, component, default=False):
        """ Add one component to the block
        
        :param default: if true this component will be use by default
        :type default: bool
        """
        if not isinstance(component, Composable):
            raise ValueError("component '%s' is not type of Optionable or Composable" % component)
        if component.name in self._components:
            raise ValueError("We already have a component with the name '%s'" % component.name)
        self._components[component.name] = component
        if default:
            if self.multiple:
                self.defaults = self.defaults + [component.name]
            else:
                self.defaults = component.name

    def select(self, comp_name, options=None):
        """ set an component as runnable with given options.

        `options` will be passed to :func:`.Optionable.parse_options` is the
        component is :class:`Optionable`.

        .. Warning:: this function also setup the options (if given) of the
            selected component. Use :func:`clear_selections` to restore both
            selection and component's options.

        This method may be call at play 'time', before to call :func:`play` to
        run all selected components.

        :param name: name of the component to select
        :type comp_name: str
        :param options: options to set to the components
        :type options: dict
        """
        self._logger.info("select comp '%s' for block '%s' (options: %s)" % (comp_name, self._name, options))
        if comp_name not in self._components:
            raise ValueError("'%s' has no component '%s' (components are: %s)"\
                  % (self._name, comp_name, ", ".join(self.component_names())))
        if options is None:
            options = {}
        # get the componsent
        component = self._components[comp_name]
        # check options make sens
        if not isinstance(component, Optionable) and len(options):
            raise ValueError("the component %s is not optionable you can't provide options..." % comp_name)
        # add component as selected, aware of multiple
        if comp_name not in self._selected:
            if not self.multiple and len(self._selected):
                assert len(self._selected) == 1
                self._selected[0] = comp_name
            else:
                self._selected.append(comp_name)
        else:
            # TODO the component has already been selected
            pass
        # component might be a function or any callable
        # only Optionable will get options
        if isinstance(component, Optionable):
            component.set_options_values(options, parse=True, strict=True)

    def validate(self):
        """ check that the block can be run
        """
        if self.required and len(self.selected()) == 0:
            raise CelloError("No component selected for block '%s'" % self.name)

    def play(self, *args):
        """ Run the selected components of the block
        
        .. warning:: Defaut 'multiple' behavior is a **pipeline** !
q        
        :param *args: arguments (i.e. inputs) to give to the components
        """
        start = time.time()
        # TODO: multi mode option(False, pipeline, map)
        self.validate() # TODO what if validate fails

        _break_on_error = True
        results = None
        # run
        for comp_name in self.selected():
            comp = self._components[comp_name]
            if isinstance(comp, Optionable):
                options = comp.get_options_values(hidden=True)
            else:
                options = {}
            # TODO store args and kwargs ?
            argstr = [repr(arg)[:100].replace('\n', '') for arg in args]
            comp_res = {
                "name": comp.name,
                "obj": repr(comp),
                "args": "".join(argstr),
                "kwargs": options,
                "errors": [],
                "warnings": [],
                "time": 0
            }
            self._logger.info("""'%s' playing: %s
                component: %s,
                args=%s,
                kwargs=%s""" % (self._name, comp.name, comp, "\n\t\t".join(argstr), options))

            try:
                # multi = False or pipeline
                # given that the args in input are also the returning value
                # This behavior allows to modify the data given in input.
                # actually same arg if given several times 
                # but may be transformed during the process
                # then finally returned
                results = comp(*args, **options)

                # TODO implements different mode for multiple 
                # another way would be declaring a list var outside the loop,
                # then append result of each call to the components __call__
                # and finally returns all computed results
                #   map( lambda x : x(*arg), *components )
                # >>> results.append( comp(*args, **options) )
                # >>> return *results

            # TODO catch warnings TODO
            # warning may be raised for many reasons like:
            # * options has been modified
            # * deprecation
            # * pipeline inconsistency 
            # * invalid input (graph with no edge ...)

            except Exception as err:
                # component error handling
                comp_res['errors'].append("error in component %s %s /n %s" % (comp, comp.name, err.message))
                self._logger.error(comp_res['errors'])
                if _break_on_error:
                    break
            
            # component time
            now = time.time()
            comp_res['time'] = now - start
            start = now
            self.meta.components[comp.name] = comp_res

        # XXX may return more than one value with multi=map 
        return results



class Engine(object):
    """ The Cello engine.
    """
    @define_logger
    def __init__(self, *names):
        self._blocks = OrderedDict()
        self.time = 0
        self._logger.info("\n\n\t\t\t ** ============= Init engine ============= ** \n")
        if len(names):
            self.requires(*names)

    def requires(self, *names):
        """ Declare what block will be used in this engine.
    
        It should be call before adding or setting any component.
        Blocks order will be preserved for runnning task.
        """
        if len(names) == 0:
            raise ValueError("You should give at least one block name")
    
        if self._blocks is not None and len(self._blocks) > 0:
            raise CelloError("Method 'requires' should be called only once before adding any composant")
        for name in names:
            if name in self._blocks:
                raise ValueError("Duplicate block name %s" % name)
            self._blocks[name] = Block(name)
        self._logger.info(" ** requires ** %s", names)

    def set(self, name, *components, **options):
        """ Set available components and the options of one block.
        
        :param name: block name
        :param components: a list of components (see :meth:`Block.set`)
        :param options: options of the block (see :meth:`Block.setup`)
        """
        self._logger.info(" ** SET ** '%s' "% name)

        if name not in self:
            raise ValueError("'%s' is not a block (%s)" % (name, ",".join(self.names())))
        self[name].set(*components)
        self[name].setup(**options)

    @property
    def in_name(self):
        return iter(self).next().in_name

    def __contains__(self, name):
        """ returns whether a block of the given name exists
        """
        return name in self._blocks

    def __getitem__(self, name):
        """ returns the block of the given name
        """
        if name not in self._blocks:
            raise ValueError("'%s' is not a block (%s)" % (name, ",".join(self.names())))
        return self._blocks[name]

    def __getattr__(self, name):
        """ returns the block of the given name
        """
        return self[name]

    def __len__(self):
        """ returns block count
        """
        return len(self._blocks)

    def __iter__(self):
        """ iterate over all blocks
        """
        return self._blocks.itervalues()

    def names(self):
        """ returns the list of block names
        """
        return self._blocks.keys()

    def configure(self, config):
        """ Configure all the blocks from an (horible) configuration dictionary
        this data are coming from a json client request and has to be parsed.
        It takes the default value if missing (for component selection and 
        options).

        :param config: dictionary that give the component to use for each step
               and the associated options 
        :type config: dict

        `config` format ::

            {
                block_name: [{
                    'name': name_of_the_comp_to_use,
                    'options': {
                            name: value,
                            name: va...
                        }
                    },
                    {...}
                ]
           }
           
        .. warning:: values of options in this dictionnary are strings

        """
        self._logger.info("Parsing config, retrieve the components to use")
        # normalise input format
        for block_name in config.iterkeys():
            if isinstance(config[block_name], dict):
                config[block_name] = [config[block_name]]
        # check errors
        for block_name, request_comps in config.iteritems():
            if block_name not in self:
                raise ValueError("Block '%s' doesn't exist !" % block_name)
            block = self[block_name]
            if block.hidden and len(request_comps):
                raise ValueError("Component '%s' is hidden you can't change it's configuration from here" % block.name)
            if block.required and len(request_comps) == 0:
                raise ValueError("Component '%s' is required but None given" % block.name)
            # comp is given
            if not block.multiple and isinstance(request_comps, list) and len(request_comps) > 1:
                raise ValueError("Block '%s' allows only one component to be selected" % block.name)
            # check input dict
            for req_comp in request_comps:
                if 'name' not in req_comp:
                    raise ValueError("Config error in '%s' " % block.name)
                if req_comp['name'] not in block:
                    raise ValueError("Invalid component (%s) for block '%s' "
                        % (req_comp['name'], block.name))

        # clear the current selection and option
        for block in self:
            # remove selection and reset to default options
            block.clear_selections()
        # configure the blocks
        for block_name, request_comps in config.iteritems():
            block = self[block_name]
            # select and set options
            for req_comp in request_comps:
                block.select(req_comp['name'], req_comp.get("options", {}))

    def validate(self):
        """ Check that the blocks configuration is ok """
        if not len(self._blocks):
            #XXX: better error than CelloError ?
            raise CelloError("There is no block in this engine")
        for block in self:
            block.validate()
        # check the inputs and outputs
        # note: fornow only the first block can have user given input
        available = set()       # set of available data
        maybe_available = set() # data that are produced be not required blocks
        # add the first block input as available data
        first_in_name = self.in_name[0] if self.in_name is not None else None 
        if first_in_name is not None:
            available.add(first_in_name)
        for bnum, block in enumerate(self):
            if block.in_name is not None:
                if any( [ e in maybe_available for e in block.in_name ] ):
                    raise CelloError("The block '%s' need an input ('%s') that *may* not be produced before" % (block.name, block.in_name))
                if not all( [ e in available for e in block.in_name ] ):
                    raise CelloError("The block '%s' need an input ('%s') that is not produced before" % (block.name, block.in_name))
            # register the output
            if not block.required:
                maybe_available.add(block.out_name)
            else:
                available.add(block.out_name)

    def play(self, input_data):
        """ Run the engine that should have been configured first
        
        :param input_data: 
        """
        self.validate()
        results = OrderedDict()
        # prepare the input data
        last_output_name = ["input"]
        first_in_name = iter(self).next().in_name or last_output_name
        results[first_in_name[0]] = input_data # self.first_in_name est une property qui 
        # run the blocks
        for block in self:
            inputs = block.in_name or last_output_name
            inputs = [results[name] for name in inputs]
            results[block.out_name] = block.play(*inputs)
            #^ Note: le validate par rapport au type est fait dans le run du block
            last_output_name = [block.out_name]
        return results

    def get_play_trace(self):
        return {block.name: block.meta.components for block in self}

    def as_dict(self):
        """ dict repr of the components """
        drepr = {
            'blocks': [
                block.as_dict() for block in self if block.hidden == False
            ],
            'args': self.in_name
        }
        return drepr

