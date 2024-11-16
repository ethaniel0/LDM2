import sys
sys.path.append('..')
import ldm.lib_config2.parsing_types as pt
from ldm.source_tokenizer.tokenize import TokenizerItems, Tokenizer


INT_TYPE = pt.PrimitiveType(
    spec=pt.TypeSpec("int", 0, []),
    superclass=None,
    methods=[],
    initialize=pt.PrimitiveTypeInitialize("$int"),
    value_keywords=[]
)

FLOAT_TYPE = pt.PrimitiveType(
    spec=pt.TypeSpec("float", 0, []),
    superclass=None,
    methods=[],
    initialize=pt.PrimitiveTypeInitialize("$float"),
    value_keywords=[]
)

BOOL_TYPE = pt.PrimitiveType(
    spec=pt.TypeSpec("bool", 0, []),
    superclass=None,
    methods=[],
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

MAKE_VARIABLE = pt.MakeVariable(
    name="standard",
    structure=pt.Structure(
        component_specs={
            "typename": pt.StructureSpecComponent(base="typename",
                                                  name="typename",
                                                  other={}),
            "varname": pt.StructureSpecComponent(base="name",
                                                 name="varname",
                                                 other={"type": "new-local"}),
            "expr": pt.StructureSpecComponent(base="expression",
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
    )
)

PLUS_OPERATOR = pt.Operator(
    name="+",
    precedence=6,
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base="operator_value", name="left", other={}),
            "right": pt.StructureSpecComponent(base="operator_value", name="right", other={})
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
    overloads=[
        pt.OperatorOverload(
            name="+",
            return_type="int",
            variables={
                "left": "int",
                "right": "int"
            }
        ),
        pt.OperatorOverload(
            name="+",
            return_type="float",
            variables={
                "left": "float",
                "right": "float"
            }
        ),
        pt.OperatorOverload(
            name="+",
            return_type="float",
            variables={
                "left": "float",
                "right": "int"
            }
        ),
        pt.OperatorOverload(
            name="+",
            return_type="float",
            variables={
                "left": "int",
                "right": "float"
            }
        )
    ],
    trigger="+",
    associativity=pt.Associativity.LEFT_TO_RIGHT
)

PLUS_OPERATOR.operator_type = pt.OperatorType.BINARY
PLUS_OPERATOR.calc_num_variables()

MINUS_OPERATOR = pt.Operator(
    name="-",
    precedence=6,
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base="operator_value", name="left", other={}),
            "right": pt.StructureSpecComponent(base="operator_value", name="right", other={})
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
    overloads=[
        pt.OperatorOverload(
            name="-",
            return_type="int",
            variables={
                "left": "int",
                "right": "int"
            }
        ),
        pt.OperatorOverload(
            name="-",
            return_type="float",
            variables={
                "left": "float",
                "right": "float"
            }
        ),
        pt.OperatorOverload(
            name="-",
            return_type="float",
            variables={
                "left": "float",
                "right": "int"
            }
        ),
        pt.OperatorOverload(
            name="-",
            return_type="float",
            variables={
                "left": "int",
                "right": "float"
            }
        )
    ],
    trigger="-",
    associativity=pt.Associativity.LEFT_TO_RIGHT
)

MINUS_OPERATOR.operator_type = pt.OperatorType.BINARY
MINUS_OPERATOR.calc_num_variables()

NEG_OPERATOR = pt.Operator(
    name="- neg",
    precedence=3,
    structure=pt.Structure(
        component_specs={
            "right": pt.StructureSpecComponent(base="operator_value", name="right", other={})
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
    overloads=[
        pt.OperatorOverload(
            name="-",
            return_type="int",
            variables={"right": "int"}
        ),
        pt.OperatorOverload(
            name="-",
            return_type="float",
            variables={"right": "float"}
        )
    ],
    trigger="-",
    associativity=pt.Associativity.LEFT_TO_RIGHT
)

NEG_OPERATOR.operator_type = pt.OperatorType.UNARY_RIGHT
NEG_OPERATOR.calc_num_variables()


TIMES_OPERATOR = pt.Operator(
    name="*",
    precedence=5,
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base="operator_value", name="left", other={}),
            "right": pt.StructureSpecComponent(base="operator_value", name="right", other={})
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
    overloads=[
        pt.OperatorOverload(
            name="*",
            return_type="int",
            variables={
                "left": "int",
                "right": "int"
            }
        ),
        pt.OperatorOverload(
            name="*",
            return_type="float",
            variables={
                "left": "float",
                "right": "float"
            }
        ),
        pt.OperatorOverload(
            name="*",
            return_type="float",
            variables={
                "left": "float",
                "right": "int"
            }
        ),
        pt.OperatorOverload(
            name="*",
            return_type="float",
            variables={
                "left": "int",
                "right": "float"
            }
        )
    ],
    trigger="*",
    associativity=pt.Associativity.LEFT_TO_RIGHT
)

TIMES_OPERATOR.operator_type = pt.OperatorType.BINARY
TIMES_OPERATOR.calc_num_variables()


TERNARY_OPERATOR = pt.Operator(
    name="?:",
    precedence=16,
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base="operator_value", name="left", other={}),
            "middle": pt.StructureSpecComponent(base="operator_value", name="middle", other={}),
            "right": pt.StructureSpecComponent(base="operator_value", name="right", other={})
        },
        component_defs=[
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="left"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value="?"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="middle"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.String,
                value=":"
            ),
            pt.StructureComponent(
                component_type=pt.StructureComponentType.Variable,
                value="right"
            )
        ]
    ),
    overloads=[
        pt.OperatorOverload(
            name="?:",
            return_type="$typename<T>",
            variables={
                "left": "bool",
                "middle": "$typename<T>",
                "right": "$typename<T>"
            }
        )
    ],
    trigger="?",
    associativity=pt.Associativity.LEFT_TO_RIGHT
)

TERNARY_OPERATOR.operator_type = pt.OperatorType.BINARY
TERNARY_OPERATOR.calc_num_variables()


GT_OPERATOR = pt.Operator(
    name=">",
    precedence=9,
    structure=pt.Structure(
        component_specs={
            "left": pt.StructureSpecComponent(base="operator_value", name="left", other={}),
            "right": pt.StructureSpecComponent(base="operator_value", name="right", other={})
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
    overloads=[
        pt.OperatorOverload(
            name=">",
            return_type="bool",
            variables={
                "left": "int",
                "right": "int"
            }
        ),
        pt.OperatorOverload(
            name=">",
            return_type="bool",
            variables={
                "left": "int",
                "right": "float"
            }
        ),
        pt.OperatorOverload(
            name=">",
            return_type="bool",
            variables={
                "left": "float",
                "right": "int"
            }
        ),
        pt.OperatorOverload(
            name=">",
            return_type="bool",
            variables={
                "left": "float",
                "right": "float"
            }
        )
    ],
    trigger=">",
    associativity=pt.Associativity.LEFT_TO_RIGHT
)

GT_OPERATOR.operator_type = pt.OperatorType.BINARY
GT_OPERATOR.calc_num_variables()


PARENTHESES_OPERATOR = pt.Operator(
    name="()",
    precedence=0,
    structure=pt.Structure(
        component_specs={
            "inside": pt.StructureSpecComponent(base="operator_value", name="inside", other={}),
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
    overloads=[
        pt.OperatorOverload(
            name="()",
            return_type="$typename<T>",
            variables={
                "inside": "$typename<T>"
            }
        )
    ],
    trigger="(",
    associativity=pt.Associativity.LEFT_TO_RIGHT
)

PARENTHESES_OPERATOR.operator_type = pt.OperatorType.INTERNAL
PARENTHESES_OPERATOR.calc_num_variables()

SEMICOLON = pt.ExpressionSeparator("semicolon", ";")

SPEC = pt.Spec(
    primitive_types={
        "int": INT_TYPE,
        "float": FLOAT_TYPE,
        "bool": BOOL_TYPE
    },
    make_variables={
        "standard": MAKE_VARIABLE
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
    operators={
        "+": PLUS_OPERATOR,
        "-": MINUS_OPERATOR,
        "- neg": NEG_OPERATOR,
        "*": TIMES_OPERATOR,
        "?:": TERNARY_OPERATOR,
        ">": GT_OPERATOR,
        "()": PARENTHESES_OPERATOR
    },
    expression_separators={";": SEMICOLON}
)

TOKENIZER_ITEMS = TokenizerItems(
    primitive_types=SPEC.primitive_types,
    operators=SPEC.operators,
    expression_separators=SPEC.expression_separators
)
TOKENIZER = Tokenizer(TOKENIZER_ITEMS)