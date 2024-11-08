import unittest
import sys
sys.path.append('..')

import json
from ldm.lib_config2.spec_parsing import parse_spec, string_to_typespec
from ldm.lib_config2.def_parsing import add_structure_definitions_to_spec


class MyTestCase(unittest.TestCase):

    def test_typespec_parsing(self):
        # simple type
        spec = string_to_typespec('int')
        assert spec.name == 'int'
        assert len(spec.subtypes) == 0

        # one subtype
        spec = string_to_typespec('int<float>')
        assert spec.name == 'int'
        assert len(spec.subtypes) == 1
        assert spec.subtypes[0].name == 'float'
        assert len(spec.subtypes[0].subtypes) == 0

        # multiple subtypes
        spec = string_to_typespec('int<float, double>')
        assert spec.name == 'int'
        assert len(spec.subtypes) == 2
        assert spec.subtypes[0].name == 'float'
        assert len(spec.subtypes[0].subtypes) == 0
        assert spec.subtypes[1].name == 'double'
        assert len(spec.subtypes[1].subtypes) == 0

        # one nested subtype
        spec = string_to_typespec('int<float<int>>')
        assert spec.name == 'int'
        assert len(spec.subtypes) == 1
        assert spec.subtypes[0].name == 'float'
        assert len(spec.subtypes[0].subtypes) == 1
        assert spec.subtypes[0].subtypes[0].name == 'int'
        assert len(spec.subtypes[0].subtypes[0].subtypes) == 0

        # multiple nested subtypes
        spec = string_to_typespec('int<float<int, double>, double<float>>')
        assert spec.name == 'int'
        assert len(spec.subtypes) == 2
        assert spec.subtypes[0].name == 'float'
        assert len(spec.subtypes[0].subtypes) == 2
        assert spec.subtypes[0].subtypes[0].name == 'int'
        assert len(spec.subtypes[0].subtypes[0].subtypes) == 0
        assert spec.subtypes[0].subtypes[1].name == 'double'
        assert len(spec.subtypes[0].subtypes[1].subtypes) == 0
        assert spec.subtypes[1].name == 'double'
        assert len(spec.subtypes[1].subtypes) == 1
        assert spec.subtypes[1].subtypes[0].name == 'float'
        assert len(spec.subtypes[1].subtypes[0].subtypes) == 0


    def test_parsing_doesnt_fail(self):
        filename = 'test_std_spec.json'
        with open(filename) as f:
            data = json.load(f)
            try:
                spec = parse_spec(data)
                assert True

            except ValueError as e:
                assert False


    def test_adding_def_to_spec(self):
        spec_file = 'test_std_spec.json'
        def_file = 'test_std_def.json'
        with open(spec_file) as f:
            spec_data = json.load(f)
            spec = parse_spec(spec_data)

        with open(def_file) as f:
            def_data = json.load(f)
            add_structure_definitions_to_spec(spec, def_data)
            assert True



if __name__ == '__main__':
    unittest.main()
