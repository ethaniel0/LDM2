import sys
sys.path.append('..')

import unittest

import json
from ldm.lib_config2.spec_parsing import parse_spec
from ldm.lib_config2.def_parsing import add_structure_definitions_to_spec
from ldm.source_tokenizer.tokenize import TokenizerItems, Tokenizer
from ldm.ast.parsing import ParsingItems, parse
from ldm.translation.translate import translate, TranslationItems


def load_setup():
    spec_file = 'test_std_spec.json'
    def_file = 'test_std_def.json'
    python_file = 'python_std.json'

    with open(spec_file) as f:
        spec_data = json.load(f)
        spec = parse_spec(spec_data)

    with open(def_file) as f:
        def_data = json.load(f)
        add_structure_definitions_to_spec(spec, def_data)

    with open(python_file) as f:
        translation_data = json.load(f)
        translation = TranslationItems(translation_data)

    return spec, translation


class MyTestCase(unittest.TestCase):
    def test_parsing(self):
        print()
        spec, translation = load_setup()
        source_code = "int x = 9"

        tokenizer_items = TokenizerItems(
            primitive_types=spec.primitive_types,
            operators=spec.operators,
            expression_separators=spec.expression_separators
        )
        tokenizer = Tokenizer(tokenizer_items)
        tokens = tokenizer.tokenize(source_code)
        parsing_items = ParsingItems(spec)
        ast = parse(tokens, parsing_items, tokenizer_items)
        code = translate(ast, parsing_items, translation)
        print('code:')
        print(code)

    def test_parsing_with_operators(self):
        print()
        spec, translation = load_setup()
        source_code = "int x = true ? 4 * 3 + 2 : 5 - -4"

        tokenizer_items = TokenizerItems(
            spec.primitive_types,
            spec.operators,
            spec.expression_separators
        )
        tokenizer = Tokenizer(tokenizer_items)
        tokens = tokenizer.tokenize(source_code)
        parsing_items = ParsingItems(spec)
        ast = parse(tokens, parsing_items, tokenizer_items)
        code = translate(ast, parsing_items, translation)
        print('code:')
        print(code)

    def test_with_block(self):
        print()
        spec, translation = load_setup()
        source_code = """
        int x = 12;
        if (x < 14) {
            if (x < 14) {
            int zx = 69;
            if (x < 14) {}
            float cwdeas = x < 14 ? 69 : 420;
            if (x < 14) {
            if (x < 14) {
            if (x < 14) {
            if (x < 14) {
            int y = 14;
        }
        }
        }
        }
        }
        }
        """

        tokenizer_items = TokenizerItems(
            spec.primitive_types,
            spec.operators,
            spec.expression_separators
        )
        tokenizer = Tokenizer(tokenizer_items)
        tokens = tokenizer.tokenize(source_code)
        parsing_items = ParsingItems(spec)
        ast = parse(tokens, parsing_items, tokenizer_items)
        code = translate(ast, parsing_items, translation)
        print('code:')
        print(code)


if __name__ == '__main__':
    unittest.main()
