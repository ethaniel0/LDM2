import sys
sys.path.append('..')

import unittest

import json
from ldm.lib_config2.spec_parsing import parse_spec
from ldm.lib_config2.def_parsing import add_structure_definitions_to_spec
from ldm.source_tokenizer.tokenize import TokenizerItems
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
        source_code = "int x = 9 int8 y = 12"
        tokenizer_items = TokenizerItems(list(spec.primitive_types.values()))
        tokens = tokenize(source_code, tokenizer_items)
        parsing_items = ParsingItems(spec)
        ast = parse(tokens, parsing_items, tokenizer_items)
        code = translate(ast, parsing_items, translation)
        print('code:')
        print(code)


if __name__ == '__main__':
    unittest.main()
