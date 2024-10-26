import unittest

import json
from ldm.lib_config2.spec_parsing import parse_spec
from ldm.lib_config2.def_parsing import add_structure_definitions_to_spec
from ldm.source_tokenizer.tokenize import tokenize, TokenizerItems
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
        items = TokenizerItems(list(spec.primitive_types.values()))
        # print('items:', items)
        tokens = tokenize(source_code, items)
        print(tokens)
        assert len(tokens) == 4
        assert tokens[0].type == TokenType.PrimitiveType
        assert tokens[0].value == 'int'

        assert tokens[1].type == TokenType.Identifier
        assert tokens[1].value == 'x'

        assert tokens[2].type == TokenType.Operator
        assert tokens[2].value == '='

        assert tokens[3].type == TokenType.Number
        assert tokens[3].value == '5'

    def test_parsing(self):
        print()
        spec = load_setup()
        source_code = "int x = 5"
        tokenizer_items = TokenizerItems(list(spec.primitive_types.values()))
        tokens = tokenize(source_code, tokenizer_items)
        ast = parse(tokens, ParsingItems(spec.primitive_types, spec.make_variables), tokenizer_items)
        print(ast)

if __name__ == '__main__':
    unittest.main()
