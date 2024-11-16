import unittest

import json
from ldm.lib_config2.spec_parsing import parse_spec
from ldm.lib_config2.def_parsing import add_structure_definitions_to_spec
from ldm.source_tokenizer.tokenize import Tokenizer, TokenizerItems
from ldm.source_tokenizer.tokenizer_types import *
from ldm.ast.parsing import ParsingItems, parse


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


class MyTestCase(unittest.TestCase):
    def test_simple(self):
        print()
        spec = load_setup()
        source_code = "int x = 5"
        items = TokenizerItems(spec.primitive_types, spec.operators, spec.expression_separators)
        tokenizer = Tokenizer(items)
        tokens = tokenizer.tokenize(source_code)
        print(tokens)
        assert len(tokens) == 4
        assert tokens[0].type == TokenType.PrimitiveType
        assert tokens[0].value == 'int'

        assert tokens[1].type == TokenType.Identifier
        assert tokens[1].value == 'x'

        assert tokens[2].type == TokenType.Operator
        assert tokens[2].value == '='

        assert tokens[3].type == TokenType.Integer
        assert tokens[3].value == '5'

    def test_numerical_types(self):
        spec = load_setup()
        source_code = "5 2.6"
        items = TokenizerItems(spec.primitive_types, spec.operators, spec.expression_separators)
        tokenizer = Tokenizer(items)
        tokens = tokenizer.tokenize(source_code)
        assert len(tokens) == 2

        assert tokens[0].type == TokenType.Integer
        assert tokens[0].value == '5'

        assert tokens[1].type == TokenType.Float
        assert tokens[1].value == '2.6'

    def test_expression_separators(self):
        spec = load_setup()
        source_code = ";;"
        items = TokenizerItems(spec.primitive_types, spec.operators, spec.expression_separators)

        tokenizer = Tokenizer(items)
        tokens = tokenizer.tokenize(source_code)
        assert len(tokens) == 2

        assert tokens[0].type == TokenType.ExpressionSeparator
        assert tokens[0].value == ';'

        assert tokens[1].type == TokenType.ExpressionSeparator
        assert tokens[1].value == ';'


if __name__ == '__main__':
    unittest.main()
