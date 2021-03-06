# -*- coding:utf-8; python-indent:2; indent-tabs-mode:nil -*-

# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Our way of using namedtuple is confusing pylint.
# pylint: disable=no-member

"""AST representation of a pytd file."""

from pytypedecl.parse import node


class Type(object):
  """The superclass of all types.

  This is a marker superclass that is mixed into each class that represents a
  pytd type.
  """
  pass


class TypeDeclUnit(node.Node('constants', 'classes', 'functions', 'modules')):
  """Module node. Holds module contents (classes / functions) and submodules.

  Attributes:
    constants: List of module-level constants.
    functions: List of functions defined in this type decl unit.
    classes: List of classes defined in this type decl unit.
    modules: Map of submodules of the current module.
  """

  def Lookup(self, name):
    """Convenience function: Look up a given name in the global namespace.

    Tries to find a constant, function or class by this name.

    Args:
      name: Name to look up.

    Returns:
      A Constant, Function or Class.

    Raises:
      KeyError: if this identifier doesn't exist.
    """
    # TODO: Remove. Change constants, classes and functions to dict.
    try:
      return self._name2item[name]
    except AttributeError:
      self._name2item = {}
      for x in self.constants + self.functions + self.classes:
        self._name2item[x.name] = x
      return self._name2item[name]


class Constant(node.Node('name', 'type')):
  __slots__ = ()


class Class(node.Node('name', 'parents', 'methods', 'constants', 'template')):
  """Represents a class declaration.

  Attributes:
    name: Class name (string)
    parents: The super classes of this class (instances of Type).
    methods: List of class methods (instances of Function).
    constants: List of constant class attributes (instances of Constant).
    template: List of TemplateItem instances.
  """
  # TODO: Rename "parents" to "bases". "Parents" is confusing since we're
  #              in a tree.

  def Lookup(self, name):
    """Convenience function: Look up a given name in the class namespace.

    Tries to find a method or constant by this name in the class.

    Args:
      name: Name to look up.

    Returns:
      A Constant or Function instance.

    Raises:
      KeyError: if this identifier doesn't exist in this class.
    """
    # TODO: Remove this. Make methods and constants dictionaries.
    try:
      return self._name2item[name]
    except AttributeError:
      self._name2item = {}
      for x in self.methods + self.constants:
        self._name2item[x.name] = x
      return self._name2item[name]


class Function(node.Node('name', 'signatures')):
  """A function or a method.

  Attributes:
    name: The name of this function.
    signatures: Possible list of parameter type combinations for this function.
  """
  __slots__ = ()


class Signature(node.Node('params', 'return_type', 'exceptions', 'template',
                          'has_optional'), Type):
  """Represents an individual signature of a function.

  For overloaded functions, this is one specific combination of parameters.
  For non-overloaded functions, there is a 1:1 correspondence between function
  and signature.

  Attributes:
    name: The name of this function.
    params: The list of parameters for this function definition.
    return_type: The return type of this function.
    exceptions: List of exceptions for this function definition.
    template: names for bindings for bounded types in params/return_type
    has_optional: Do we have optional parameters ("...")?
  """

  __slots__ = ()


class Parameter(node.Node('name', 'type')):
  """Represents a parameter of a function definition.

  Attributes:
    name: The name of the parameter.
    type: The type of the parameter.
  """
  __slots__ = ()


# Conceptually, this is a subtype of Parameter:
class MutableParameter(node.Node('name', 'type', 'new_type')):
  """Represents a parameter that's modified by the function.

  Attributes:
    name: The name of the parameter.
    type: The type of the parameter.
    new_type: The type the parameter will have after the function is called.
  """
  __slots__ = ()


class TemplateItem(node.Node('name', 'within_type', 'level')):
  """Represents "template name extends bounded_type".

  This can be either the result of the 'template' in the parser (e.g.,
    funcdef : DEF template NAME LPAREN params RPAREN ...)
  or the result of a lookup using the ExpandTemplates visitor.

  Attributes:
    name: the name that's used in a generic type
    type: the "extends" type for this name (e.g., NamedType('object'))
    level: When this object is the result of a lookup, it is how many
           levels "up" the name was found. For example:
             class <T> Foo:
               def <U> bar(t: T, u: U)
           in the definition of 'bar', T has level=1 and U has level=0
  """
  __slots__ = ()


# There are multiple representations of a "type" (used for return types,
# arguments, exceptions etc.):
# 1.) NamedType:
#     Specifies a type by name (i.e., a string)
# 2.) NativeType
#     Points to a Python type. (int, float etc.)
# 3.) ClassType
#     Points back to a Class in the AST. (This makes the AST circular)
# visitors.py contains tools for converting between the corresponding AST
# representations.


class NamedType(node.Node('name'), Type):
  """A type specified by name."""
  __slots__ = ()

  def __str__(self):
    return str(self.name)


class NativeType(node.Node('python_type'), Type):
  """A type specified by a native Python type. Used during runtime checking."""
  __slots__ = ()


class ClassType(node.Node('name'), Type):
  """A type specified through an existing class node."""

  # This type is different from normal nodes:
  # (a) It's mutable, and there are functions (parse/visitors.py:FillInClasses)
  #     that modify a tree in place.
  # (b) Because it's mutable, it's not actually using the tuple/Node interface
  #     to store things (in particular, the pointer to the existing class).
  # (c) Visitors will not process the "children" of this node. Since we point
  #     to classes that are back at the top of the tree, that would generate
  #     cycles.

  def __new__(cls, name):
    self = super(ClassType, cls).__new__(cls, name)
    self.cls = None  # later, name is looked up, and cls is filled in
    return self

  def __str__(self):
    return str(self.cls.name) if self.cls else self.name

  def __repr__(self):
    return '{%sClassType}(%s)' % (
        'Unresolved' if self.cls is None else '',
        self.name
    )


class UnknownType(node.Node(), Type):
  """A type we know nothing about yet."""
  __slots__ = ()


class NothingType(node.Node(), Type):
  """An "impossible" type, with no instances.

  Also known as the "uninhabited" type. For representing empty lists, and
  functions that never return.
  """
  __slots__ = ()


class Scalar(node.Node('value'), Type):
  __slots__ = ()


class UnionType(node.Node('type_list'), Type):
  __slots__ = ()

  def __eq__(self, other):
    if isinstance(other, UnionType):
      return set(self.type_list) == set(other.type_list)
    return NotImplemented

  def __ne__(self, other):
    return not (self == other)


class IntersectionType(node.Node('type_list'), Type):
  __slots__ = ()


class HomogeneousContainerType(node.Node('base_type', 'element_type'), Type):
  __slots__ = ()


class GenericType(node.Node('base_type', 'parameters'), Type):
  __slots__ = ()


def Print(n):
  """Convert a PYTD node to a string."""
  # TODO: fix circular import
  from pytypedecl.parse import visitors  # pylint: disable=g-import-not-at-top
  v = visitors.PrintVisitor()
  return n.Visit(v)
