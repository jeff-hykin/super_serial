Under construction

<!-- # What is this?

(Your answer here)

# How do I use this?

`pip install super-serial`


```python
from super_serial import serialize, deserialize, auto_serial

@auto_serial(included_attributes=["name"], excluded_attributes=["a_func"])
class Person:
    __deserialize_id__ = "0.5334486126134206-Thing"
    
    def __init__(self, name):
        self.name = name
        self.a_func = lambda : print("lambdas like me are difficult to impossible to serialize")


# 
# save
# 
person = Person("hi")
person.save("./some/path.person.yaml")

# 
# load
# 
person = Person.load("./some/path.person.yaml")

# 
# serialize
# 
person_string = serialize(person) # returns a string

# 
# deserialize
# 
person = deserialize(person_string) # returns a person object

# 
# load + reconnect 
# 
person = Person.load(
    "./some/path.person.yaml",
    # manually reconnect stuff that simply cant be serialized
    a_func= lambda : print("lambdas like me are difficult to impossible to serialize")
)

``` -->
