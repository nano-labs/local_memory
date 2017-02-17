# Local Memory Utils

Some tools that I made to help me in some projects

## SharedMemoryDict

![N](https://github.com/nano-labs/local_memory/blob/master/anim.gif)

Dict-like object that allow you to share data between various applications on same computer

###Usage:

First process:
```python
>>> from local_memory import SharedMemoryDict
>>> foo = SharedMemoryDict()
>>> foo["hello"] = "world"
>>> foo
{'hello': 'world'}
>>> foo.name
'2125001920'
```

Second process:
```python
>>> from local_memory import SharedMemoryDict
>>> bar = SharedMemoryDict(name='2125001920')  # Name fromm foo.name from first process
>>> bar
{'hello': 'world'}
```

Or given a name for the dict
First process:
```python
>>> from local_memory import SharedMemoryDict
>>> foo = SharedMemoryDict(name="parrot")
>>> foo["hello"] = "world"
>>> foo
{'hello': 'world'}
```

Second process:
```python
>>> from local_memory import SharedMemoryDict
>>> bar = SharedMemoryDict(name="parrot")
>>> bar
{'hello': 'world'}
```


### Cache

Simple local memory key-value Cache object. Allow you to set expiration time to a key
