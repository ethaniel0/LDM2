import sys
sys.path.append('..')
import unittest
import json
from ldm.lib_config2.spec_parsing import parse_spec
import ldm.lib_config2.parsing_types as pt
from ldm.lib_config2.def_parsing import add_structure_definitions_to_spec
from ldm.source_tokenizer.tokenize import TokenizerItems, Tokenizer
from ldm.source_tokenizer.tokenizer_types import *
from ldm.ast.parsing import ParsingItems, parse
from ldm.ast import parsing_types as ast_pt


def load_setup():
    spec_file = 'test_std_spec.json'
    def_file = 'test_std_def.json'
    with open(spec_file) as f:
        spec_data = json.load(f)
        spec = parse_spec(spec_data)

    with open(def_file) as f:
        def_data = json.load(f)
        add_structure_definitions_to_spec(spec, def_data)

    return spec


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
    precedence=8,
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
        "+": PLUS_OPERATOR
    }
)

TOKENIZER_ITEMS = TokenizerItems(SPEC.primitive_types, SPEC.operators)
TOKENIZER = Tokenizer(TOKENIZER_ITEMS)


class MyTestCase(unittest.TestCase):
    
    def test_literal_tokenizing(self):
        source_code = "hello"
        tokens = TOKENIZER.tokenize(source_code)

        assert len(tokens) == 1
        assert tokens[0].type == TokenType.Identifier
        assert tokens[0].value == "hello"
        assert tokens[0].line == 1

    def test_number_tokenizing(self):
        source_code = "123 1.5 2"
        tokens = TOKENIZER.tokenize(source_code)

        assert len(tokens) == 3
        assert tokens[0].type == TokenType.Integer
        assert tokens[0].value == "123"
        assert tokens[0].line == 1

        assert tokens[1].type == TokenType.Float
        assert tokens[1].value == "1.5"
        assert tokens[1].line == 1

        assert tokens[2].type == TokenType.Integer
        assert tokens[2].value == "2"
        assert tokens[2].line == 1

    def test_operator_tokenizing(self):
        source_code = "+"
        tokens = TOKENIZER.tokenize(source_code)

        assert len(tokens) == 1
        assert tokens[0].type == TokenType.Operator
        assert tokens[0].value == "+"
        assert tokens[0].line == 1

    def test_unknown_operator(self):
        source_code = "-"
        tokens = TOKENIZER.tokenize(source_code)
        # even if unknown, will recognize as operator
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.Operator
        assert tokens[0].value == "-"
        assert tokens[0].line == 1

    def test_make_variable_parsing(self):
        source_code = "int x = 5"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(SPEC), TOKENIZER_ITEMS)

        assert len(ast) == 1
        assert isinstance(ast[0], ast_pt.MakeVariableInstance)
        mv: ast_pt.MakeVariableInstance = ast[0]
        assert mv.name == 'standard'
        assert mv.structure['typename'].value == 'int'
        assert mv.typename.value == 'int'
        assert mv.structure['varname'].value == 'x'
        assert mv.varname.value == 'x'

        expr: ast_pt.ValueToken = mv.structure['expr']
        assert isinstance(expr, ast_pt.ValueToken)
        assert expr.value.value == '5'
        var_expr: ast_pt.ValueToken = mv.expr
        assert var_expr.value.value == '5'

    def test_parsing(self):
        print()
        spec = load_setup()
        source_code = "int x = 5"
        tokens = TOKENIZER.tokenize(source_code)
        ast = parse(tokens, ParsingItems(spec), TOKENIZER_ITEMS)
        print(ast)


if __name__ == '__main__':
    unittest.main()
