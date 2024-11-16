from __future__ import annotations
from dataclasses import dataclass

'''
@ creates an object
direct argument: @name(arg1 arg2 ...)
argument: @name arg1 arg2 ...
property: @name { @prop1 ... @prop2 ... }
string: [ ...string... ]
'''


@dataclass
class ConfigObject:
    object_type: str
    object_direct_arguments: list[str]
    object_arguments: list[str]
    object_properties: dict[str, ConfigObject]


