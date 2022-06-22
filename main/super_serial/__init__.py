from collections import OrderedDict


override_table = OrderedDict()
fallback_table = OrderedDict()

import ez_yaml
from dill import dumps, loads
ez_yaml.yaml.version = None

none_type = type(None)
def serialize(value, **options):
    recursion = lambda value: serialize(value, **options)
    # 
    # builtins
    # 
    the_type = type(value)
    if the_type == none_type:
        return "null"
    elif the_type in (int, float, bool, str,):
        return f"{value}"
    elif the_type in (tuple, list, set, frozenset):
        return "{'__super_serial__': {'loader': '"+the_type.__name__+"', 'value': "+ez_yaml.to_string([ recursion(each) for each in value ]) +"}"+"}"
    elif the_type in (dict, ):
        return "{'__super_serial__': {'loader': '"+the_type.__name__+"', 'value': "+ez_yaml.to_string({ recursion(each_key) : recursion(each_value) for each_key, each_value in value.items() }) +"}"+"}"
    
    # 
    # then check the override_table
    # 
    for each_checker in reversed(override_table.keys()):
        type_matches = isinstance(each_checker, type) and isinstance(value, each_checker)
        callable_check_matches = not isinstance(each_checker, type) and callable(each_checker) and each_checker(value)
        if type_matches or callable_check_matches:
            custom_converter_function = override_table[each_checker]
            return recursion(custom_converter_function(value))
    
    # 
    # then check the __serialize__ method
    # 
    if hasattr(value.__class__, "__serialize__"):
        function = getattr(value.__class__, "__serialize__", wrapped_default.default)
        return recursion( function(value) )
        
    # 
    # then check the fallback_table
    # 
    for each_checker in reversed(fallback_table.keys()):
        type_matches = isinstance(each_checker, type) and isinstance(value, each_checker)
        callable_check_matches = not isinstance(each_checker, type) and callable(each_checker) and each_checker(value)
        if type_matches or callable_check_matches:
            custom_converter_function = fallback_table[each_checker]
            return recursion( custom_converter_function(value) )
    
    # 
    # generic fallbacks
    # 
    
    # __json__
    if hasattr(value.__class__, "__json__"):
        function = getattr(value.__class__, "__json__", wrapped_default.default)
        return recursion( function(value) )
    # __yaml__
    if hasattr(value.__class__, "__yaml__"):
        function = getattr(value.__class__, "__yaml__", wrapped_default.default)
        return recursion( function(value) )
    
    # dill
    try:
        return  "{'__super_serial__': {'loader': 'dill', 'value': "+dumps(value).hex() +"}"+"}"
    except Exception as error:
        # if force is enabled, avoid throwing an error
        if options.get("force", False):
            return recursion(None)
        
        str_worked = False
        try:
            str_value = str(value)
            str_worked = True
        except Exception as error:
            pass
        
        object_id = id(value)
        message = f"Object was: {str_value}" if str_worked else f"Unable to print object, the id is {object_id}"
        raise Exception(f'''
        
        Unable to serialize an object. Fix this by adding a .__serialize__() method or by
        
            import serialize
            
            is_kind_of_object = lambda obj: *your_custom_if_condition*
            serialize.fallback_table[is_kind_of_object] = lambda obj: *your_way_of_serializing_the_object*
        
        {message}
        
        ''')

def deserialize(string, loaders=None, **options):
    value = ez_yaml.to_object(string)
    loaders = {
        "list": lambda obj: [convert(each) for each in obj],
        "tuple": lambda obj: tuple(convert(each) for each in obj),
        "set": lambda obj: set(convert(each) for each in obj),
        "frozenset": lambda obj: frozenset(convert(each) for each in obj),
        "dict": lambda obj: dict({ convert(each_key) : convert(each_value) for each_key, each_value in obj.items() }),
        "dill": loads,
        **(loaders or {}),
    }
    
    def convert(value):
        the_type = type(value)
        if the_type == (none_type, int, float, bool, str,):
            return value
        else:
            massive_dictionary = value
            info = massive_dictionary.get('__super_serial__',{})
            loader = loaders.get(info.get('loader', None), None)
            value = info.get('value', None)
            if callable(loader):
                return loader(value)
            else:
                return Exception(f"""Unable to deserialize {massive_dictionary}""")
