from collections import OrderedDict


override_table = OrderedDict()
fallback_table = OrderedDict()
global_deserializers = deserializers = {} # there can only be one deserializer

import ez_yaml
from dill import dumps, loads
ez_yaml.yaml.version = None

none_type = type(None)
def serialize(value, *, deserializer_id=None, **options):
    recursion = lambda value: serialize(value, **options)
    
    if deserializer_id:
        return "{'__super_serial__': {'loader': '"+deserializer_id+"', 'value': "+recursion(value)+"}" +"}" 
    
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

def deserialize(string, deserializers=None, **options):
    value = ez_yaml.to_object(string)
    deserializers = {
        **global_deserializers,
        "list": lambda obj: [convert(each) for each in obj],
        "tuple": lambda obj: tuple(convert(each) for each in obj),
        "set": lambda obj: set(convert(each) for each in obj),
        "frozenset": lambda obj: frozenset(convert(each) for each in obj),
        "dict": lambda obj: dict({ convert(each_key) : convert(each_value) for each_key, each_value in obj.items() }),
        "dill": loads,
        **(deserializers or {}),
    }
    
    def convert(value):
        the_type = type(value)
        if the_type == (none_type, int, float, bool, str,):
            return value
        else:
            massive_dictionary = value
            info = massive_dictionary.get('__super_serial__',{})
            loader = deserializers.get(info.get('loader', None), None)
            value = info.get('value', None)
            if callable(loader):
                return loader(value)
            else:
                return Exception(f"""Unable to deserialize {massive_dictionary}""")


class Object:
    pass

def auto_serial(excluded_attributes=None, included_attributes=None, get_path_from="path", exclude_system=True, exclude_methods=True):
    include             = included_attributes
    exclude             = excluded_attributes
    attribute_with_path = get_path_from
    if include is not None:
        include = set(include)
    if exclude is not None:
        exclude = set(exclude)
    
    def wrapper1(a_class):
        if not hasattr(a_class, "__deserialize_id__"):
            from random import random
            raise Exception(f'''\n\n
                
                On the {a_class.__name__} class ({repr(a_class)}), please add this __deserialize_id__
                    
                    
                    class {a_class.__name__}:
                        __deserialize_id__ = "{random()}-{a_class.__name__}"
                
                
                And WARNING, if you:
                - save an {a_class.__name__} object (serialize)
                - change the __deserialize_id__ for some reason
                - then try load an {a_class.__name__} object (deserialize)
                - the deserializer_id will fail because it uses the ID
                  (classes themselves can't really be serialized)
                
            \n\n''')
        
        
        new_class_name = f'{a_class.__name__}WithSuperSerialWrapper'
        
        exec(f'''
        class {new_class_name}(a_class):
            @classmethod
            def __deserialize__(cls, *args, attributes={}, **kwargs):
                # 
                # prefer inherited function
                # 
                one_up = super({new_class_name}, cls)
                if hasattr(one_up, "__deserialize__"):
                    return one_up.__deserialize__(*args, **kwargs)
                # 
                # fallback on this one
                # 
                else:
                    value = args[0]
                    an_object = Object()
                    # set all attributes
                    for each_key, each_value in save_dict.items():
                        setattr(the_object, each_key, each_value)
                    for each_key, each_value in attributes.items():
                        setattr(the_object, each_key, each_value)
                    # then inherit the class
                    an_object.__class__ = {new_class_name}
            
            @classmethod
            def load(cls, *args, **kwargs):
                path = args[0]
                with open(path,'r') as file:
                    output = file.read()
                return cls.__deserialize__(output, attributes=kwargs)
            
            def __serialize__(self, *args, **kwargs):
                # 
                # prefer inherited function
                # 
                one_up = super({new_class_name}, cls)
                if hasattr(one_up, "__serialize__"):
                    return one_up.__serialize__(*args, **kwargs)
                # 
                # fallback on stanard method
                # 
                else:
                    attributes = set(dir(self))
                    
                    if include is None: include = attributes
                    if exclude is None: exclude = set()
                    
                    attirbutes_to_save = ((attributes - exclude) & include) | attributes # exlude ones, then include, then make sure they exist
                    save_dict = {'{}'}
                    for each in attirbutes_to_save:
                        if exclude_methods and callable(each):
                            continue
                        # skip double underscore names
                        if exclude_system and each[0:2] == '__' and each[-2:] == '__':
                            continue
                        
                        save_dict[each] = getattr(self, each)
                    
                    return serialize(
                        save_dict,
                        deserializer_id={repr(a_class.__deserialize_id__)},
                    )
                
            
            def save(self, path=None):
                # 
                # prefer inherited function
                # 
                one_up = super({new_class_name}, cls)
                if hasattr(one_up, "save"):
                    return one_up.save(*args, **kwargs)
                else:
                    if hasattr(self, path_attribute):
                        path_attribute = getattr(self, path_attribute)
                        if path_attribute:
                            path = path or path_attribute
                    
                    with open(path, 'w') as outfile:
                        outfile.write(serialize_this(self))
                    
                    return self
        '''.replace('\n        ',"\n"), locals(), locals())
        
        new_class = eval(f"{new_class_name}", locals(), locals())
        
        # register the deserializer globally
        global_deserializers[a_class.__deserialize_id__] = new_class.__deserialize__
        
        return new_class
    
    return wrapper1
