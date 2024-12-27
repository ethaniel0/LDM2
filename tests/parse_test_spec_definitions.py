import sys
sys.path.append('..')
import ldm.lib_config2.parsing_types as pt
from ldm.source_tokenizer.tokenize import TokenizerItems, Tokenizer


INT_TYPE = pt.PrimitiveType(
    spec=pt.TypeSpec("int", 0, []),
    superclass=None,
    initialize=pt.PrimitiveTypeInitialize("$int"),
    value_keywords=[]
)

FLOAT_TYPE = pt.PrimitiveType(
    spec=pt.TypeSpec("float", 0, []),
    superclass=None,
    initialize=pt.PrimitiveTypeInitialize("$float"),
    value_keywords=[]
)

BOOL_TYPE = pt.PrimitiveType(
    spec=pt.TypeSpec("bool", 0, []),
    superclass=None,
    initialize=pt.PrimitiveTypeInitialize("bool"),
    value_keywords=[
        pt.ValueKeyword(
            name="true", value_type="bool"
        ),
        pt.ValueKeyword(
            name="false", value_type="bool"
        )
    ],
)

MAKE_VARIABLE = pt.StructuredObject(
    name="make_variable_standard",
    structure=pt.Structure(
        component_specs={
            "typename": pt.StructureSpecComponent(base=pt.ComponentType.TYPENAME,
                                                  name="type",
                                                  other={}),
            "varname": pt.StructureSpecComponent(base=pt.ComponentType.NAME,
                                                 name="varname",
                                                 other={"type": "new-local"}),
            "expr": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="expr",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="typename"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="varname"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="="
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="expr"
            )
        ]
    ),
    create_variable=pt.CreateVariable(
        name="$varname",
        type=pt.TypeSpec("typename", 0, []),
        scope=pt.ScopeOptions.LOCAL,
        check_type=None
    ),
    create_type=None,
    dependent=False
)

PLUS_OPERATOR = pt.StructuredObject(
    name="+",
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="left",
                                                  other={}),
            "right": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="right",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="left"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="+"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="right"
            )
        ]
    ),
    create_variable=None,
    create_type=None,
    create_operator=pt.CreateOperator(
        fields=["left", "right"],
        precedence=6,
        associativity=pt.Associativity.LEFT_TO_RIGHT,
        overloads=[
            pt.OperatorOverload(
                name="+",
                return_type=pt.TypeSpec("int", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="+",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="+",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="+",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            )
        ]
    ),
    dependent=False
)



# This is the exact same as the + operator, but it has right-to-right associativity
PLUS_PLUS_OPERATOR = pt.StructuredObject(
    name="++",
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="left",
                                                  other={}),
            "right": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="right",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="left"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="++"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="right"
            )
        ]
    ),
    create_variable=None,
    create_type=None,
    create_operator=pt.CreateOperator(
        fields=["left", "right"],
        precedence=6,
        associativity=pt.Associativity.RIGHT_TO_LEFT,
        overloads=[
            pt.OperatorOverload(
                name="++",
                return_type=pt.TypeSpec("int", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="++",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="++",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="++",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            )
        ]
    ),
    dependent=False
)

MINUS_OPERATOR = pt.StructuredObject(
    name="-",
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="left",
                                                  other={}),
            "right": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="right",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="left"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="-"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="right"
            )
        ]
    ),
    create_variable=None,
    create_type=None,
    create_operator=pt.CreateOperator(
        fields=["left", "right"],
        precedence=6,
        associativity=pt.Associativity.LEFT_TO_RIGHT,
        overloads=[
            pt.OperatorOverload(
                name="-",
                return_type=pt.TypeSpec("int", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="-",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="-",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="-",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            )
        ]
    ),
    dependent=False
)

NEG_OPERATOR = pt.StructuredObject(
    name="- neg",
    structure=pt.Structure(
        component_specs={
            "right": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="right",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="-"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="right"
            )
        ]
    ),
    create_variable=None,
    create_type=None,
    create_operator=pt.CreateOperator(
        fields=["right"],
        precedence=3,
        associativity=pt.Associativity.LEFT_TO_RIGHT,
        overloads=[
            pt.OperatorOverload(
                name="- neg",
                return_type=pt.TypeSpec("int", 0, []),
                variables={
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="- neg",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "right": pt.TypeSpec("float", 0, [])
                }
            )
        ]
    ),
    dependent=False
)

TIMES_OPERATOR = pt.StructuredObject(
    name="*",
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="left",
                                                  other={}),
            "right": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="right",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="left"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="*"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="right"
            )
        ]
    ),
    create_variable=None,
    create_type=None,
    create_operator=pt.CreateOperator(
        fields=["left", "right"],
        precedence=5,
        associativity=pt.Associativity.LEFT_TO_RIGHT,
        overloads=[
            pt.OperatorOverload(
                name="*",
                return_type=pt.TypeSpec("int", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="*",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="*",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="*",
                return_type=pt.TypeSpec("float", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            )
        ]
    ),
    dependent=False
)

TERNARY_OPERATOR = pt.StructuredObject(
    name="?:",
    structure=pt.Structure(
        component_specs={
            "condition": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="condition",
                                                  other={}),
            "on_true": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="on_true",
                                                  other={}),
            "on_false": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="on_false",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="condition"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="?"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="on_true"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value=":"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="on_false"
            )
        ]
    ),
    create_variable=None,
    create_type=None,
    create_operator=pt.CreateOperator(
        fields=["condition", "on_true", "on_false"],
        precedence=16,
        associativity=pt.Associativity.RIGHT_TO_LEFT,
        overloads=[
            pt.OperatorOverload(
                name="?:",
                return_type=pt.TypeSpec("$typename", 1, [pt.TypeSpec("T", 0, [])]),
                variables={
                    "condition": pt.TypeSpec('bool', 0, []),
                    "on_true": pt.TypeSpec("$typename", 1, [pt.TypeSpec("T", 0, [])]),
                    "on_false": pt.TypeSpec("$typename", 1, [pt.TypeSpec("T", 0, [])])
                }
            )
        ],
    ),
    dependent=False
)

GT_OPERATOR = pt.StructuredObject(
    name=">",
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="left",
                                                  other={}),
            "right": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="right",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="left"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value=">"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="right"
            )
        ]
    ),
    create_variable=None,
    create_type=None,
    create_operator=pt.CreateOperator(
        fields=["left", "right"],
        precedence=9,
        associativity=pt.Associativity.LEFT_TO_RIGHT,
        overloads=[
            pt.OperatorOverload(
                name=">",
                return_type=pt.TypeSpec("bool", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name=">",
                return_type=pt.TypeSpec("bool", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            ),
            pt.OperatorOverload(
                name=">",
                return_type=pt.TypeSpec("bool", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name=">",
                return_type=pt.TypeSpec("bool", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            )
        ]
    ),
    dependent=False
)

LT_OPERATOR = pt.StructuredObject(
    name="<",
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="left",
                                                  other={}),
            "right": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                              name="right",
                                              other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="left"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value=">"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="right"
            )
        ]
    ),
    create_variable=None,
    create_type=None,
    create_operator=pt.CreateOperator(
        fields=["left", "right"],
        precedence=9,
        associativity=pt.Associativity.LEFT_TO_RIGHT,
        overloads=[
            pt.OperatorOverload(
                name="<",
                return_type=pt.TypeSpec("bool", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="<",
                return_type=pt.TypeSpec("bool", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="<",
                return_type=pt.TypeSpec("bool", 0, []),
                variables={
                    "left": pt.TypeSpec("float", 0, []),
                    "right": pt.TypeSpec("int", 0, [])
                }
            ),
            pt.OperatorOverload(
                name="<",
                return_type=pt.TypeSpec("bool", 0, []),
                variables={
                    "left": pt.TypeSpec("int", 0, []),
                    "right": pt.TypeSpec("float", 0, [])
                }
            )
        ]
    ),
    dependent=False
)

PARENTHESES_OPERATOR = pt.StructuredObject(
    name="()",
    structure=pt.Structure(
        component_specs={
            "inside": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION,
                                                  name="inside",
                                                  other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="("
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="inside"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value=")"
            )
        ]
    ),
    create_operator=pt.CreateOperator(
        fields=["inside"],
        precedence=0,
        associativity=pt.Associativity.LEFT_TO_RIGHT,
        overloads=[
            pt.OperatorOverload(
                name="()",
                return_type=pt.TypeSpec("$typename", 1, [pt.TypeSpec("T", 0, [])]),
                variables={
                    "inside": pt.TypeSpec("$typename", 1, [pt.TypeSpec("T", 0, [])])
                }
            )
        ]
    ),
    dependent=False
)


SEMICOLON = pt.ExpressionSeparator("semicolon", ";")

BLOCK = pt.StructuredObject(
    name="block_main",
    structure=pt.Structure(
        component_specs={
            "body": pt.StructureSpecComponent(
                base=pt.ComponentType.EXPRESSIONS,
                name="body",
                other={
                    "allow": "all",
                    "scope": "local"
                }
            )
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="{"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="body"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="}"
            )
        ]
    ),
    dependent=True
)


IF_KEYWORD = pt.StructuredObject(
    name="if",
    structure=pt.Structure(
        component_specs={
            "condition": pt.StructureSpecComponent(base=pt.ComponentType.EXPRESSION, name="condition", other={}),
            "body": pt.StructureSpecComponent(
                base=pt.ComponentType.STRUCTURE,
                name="body",
                other={
                    "structure": "block_main"
                })
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="if"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="("
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="condition"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value=")"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="body"
            ),
        ]
    ),
)

SPEC = pt.Spec(
    primitive_types={
        "int": INT_TYPE,
        "float": FLOAT_TYPE,
        "bool": BOOL_TYPE
    },
    structured_objects={
        "make_variable_standard": MAKE_VARIABLE,
        "if": IF_KEYWORD,
        "block_main": BLOCK,
        "+": PLUS_OPERATOR,
        "++": PLUS_PLUS_OPERATOR,
        "-": MINUS_OPERATOR,
        "- neg": NEG_OPERATOR,
        "*": TIMES_OPERATOR,
        "?:": TERNARY_OPERATOR,
        ">": GT_OPERATOR,
        "<": LT_OPERATOR,
        "()": PARENTHESES_OPERATOR
    },
    initializer_formats={
        "$int": pt.InitializationSpec(
            ref_type="int",
            init_type=pt.InitializationType.VARIABLE,
            format="$int"
        ),
        "$float": pt.InitializationSpec(
            ref_type="float",
            init_type=pt.InitializationType.VARIABLE,
            format="$float"
        ),
        "true": pt.InitializationSpec(
            ref_type="bool",
            init_type=pt.InitializationType.LITERAL,
            format="true"
        ),
        "false": pt.InitializationSpec(
            ref_type="bool",
            init_type=pt.InitializationType.LITERAL,
            format="false"
        )
    },
    expression_separators={";": SEMICOLON}
)

TOKENIZER_ITEMS = TokenizerItems(
    primitive_types=SPEC.primitive_types,
    expression_separators=SPEC.expression_separators
)
TOKENIZER = Tokenizer(TOKENIZER_ITEMS)
