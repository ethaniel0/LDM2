from ldm.lib_config.config_token import parse_config, CommandItemType, BracketItem, Command, ConfigTokenType
from ldm.lib_config.config_parser import Type, ParsingError, Keyword


def test_parse_config():
    with open('./test_lib.ldm_lib') as f:
        text = f.read()
        config = parse_config(text)

        assert len(config) == 6

        c1 = config[0]
        print()
        # assertions for type int
        assert c1.class_type.token == "type"
        assert len(c1.specifiers) == 1
        assert c1.specifiers[0].token == "int"
        assert len(c1.commands) == 1
        assert c1.commands[0].name == "method"
        assert len(c1.commands[0].args) == 2
        assert c1.commands[0].args[0].token == "bool"
        assert c1.commands[0].args[1].token == "isEven"
        assert len(c1.commands[0].inner) == 0

        c2 = config[1]
        # assertions for keyword for
        assert c2.class_type.token == "keyword"
        assert len(c2.specifiers) == 1
        assert c2.specifiers[0].token == "for"
        assert len(c2.commands) == 1
        assert c2.commands[0].name == "structure"
        assert len(c2.commands[0].args) == 0
        assert len(c2.commands[0].inner) == 7
        assert c2.commands[0].inner[0].item_type == CommandItemType.Word
        assert c2.commands[0].inner[0].item.token == "for"
        assert c2.commands[0].inner[1].item_type == CommandItemType.Bracketed
        c2_i1_item: BracketItem = c2.commands[0].inner[1].item
        assert len(c2_i1_item.inner) == 4
        assert c2_i1_item.inner[0].token_type == ConfigTokenType.StructureWord
        assert c2_i1_item.inner[0].token == "typename"
        assert c2_i1_item.inner[1].token_type == ConfigTokenType.StructureWord
        assert c2_i1_item.inner[1].token == "typename"
        assert c2_i1_item.inner[2].token_type == ConfigTokenType.StructureWord
        assert c2_i1_item.inner[2].token == "is"
        assert c2_i1_item.inner[3].token_type == ConfigTokenType.StructureWord
        assert c2_i1_item.inner[3].token == "int"
        assert c2.commands[0].inner[2].item_type == CommandItemType.Bracketed
        c2_i2_item: BracketItem = c2.commands[0].inner[2].item
        assert len(c2_i2_item.inner) == 2
        assert c2_i2_item.inner[0].token_type == ConfigTokenType.StructureWord
        assert c2_i2_item.inner[0].token == "name"
        assert c2_i2_item.inner[1].token_type == ConfigTokenType.StructureWord
        assert c2_i2_item.inner[1].token == "var"
        assert c2.commands[0].inner[3].item_type == CommandItemType.Word
        assert c2.commands[0].inner[3].item.token == "in"
        assert c2.commands[0].inner[4].item_type == CommandItemType.Bracketed
        c2_i4_item: BracketItem = c2.commands[0].inner[4].item
        assert len(c2_i4_item.inner) == 3
        assert c2_i4_item.inner[0].token_type == ConfigTokenType.StructureWord
        assert c2_i4_item.inner[0].token == "typed"
        assert c2_i4_item.inner[1].token_type == ConfigTokenType.StructureWord
        assert c2_i4_item.inner[1].token == "int"
        assert c2_i4_item.inner[2].token_type == ConfigTokenType.StructureWord
        assert c2_i4_item.inner[2].token == "start"
        assert c2.commands[0].inner[5].item_type == CommandItemType.Command
        assert c2.commands[0].inner[5].item.name == "optional"
        assert len(c2.commands[0].inner[5].item.args) == 0
        assert len(c2.commands[0].inner[5].item.inner) == 2
        c2_cmd5: Command = c2.commands[0].inner[5].item
        assert len(c2_cmd5.inner) == 2
        assert c2_cmd5.inner[0].item_type == CommandItemType.Word
        assert c2_cmd5.inner[0].item.token == ".."
        assert c2_cmd5.inner[1].item_type == CommandItemType.Bracketed
        c2_i5_item: BracketItem = c2_cmd5.inner[1].item
        assert len(c2_i5_item.inner) == 3
        assert c2_i5_item.inner[0].token_type == ConfigTokenType.StructureWord
        assert c2_i5_item.inner[0].token == "typed"
        assert c2_i5_item.inner[1].token_type == ConfigTokenType.StructureWord
        assert c2_i5_item.inner[1].token == "int"
        assert c2_i5_item.inner[2].token_type == ConfigTokenType.StructureWord
        assert c2_i5_item.inner[2].token == "step"
        assert c2.commands[0].inner[6].item_type == CommandItemType.Bracketed
        c2_i6_item: BracketItem = c2.commands[0].inner[6].item
        assert len(c2_i6_item.inner) == 2
        assert c2_i6_item.inner[0].token_type == ConfigTokenType.StructureWord
        assert c2_i6_item.inner[0].token == "block"
        assert c2_i6_item.inner[1].token_type == ConfigTokenType.StructureWord
        assert c2_i6_item.inner[1].token == "block"


def test_type_parsing():
    print()

    type_test1 = '''
            type int (
            %initialize {typed number value}%
            %method(bool isEven)%
            %method(float sqrt)
                {arg optional int base}
            %
            %method(bool equals)
                {arg int other}
            %
            %method(int trisum)
                {arg int a}
                {arg int b}
            %
        )
    '''

    config = parse_config(type_test1)
    if len(config) > 1:
        assert False

    item = config[0]
    assert item.class_type.token == 'type'
    assert len(item.specifiers) == 1
    assert item.specifiers[0].token == 'int'

    t: Type | ParsingError = Type.process(item)
    if isinstance(t, ParsingError):
        raise t

    assert isinstance(t, Type)
    t: Type = t

    assert len(t.methods) == 4
    assert t.methods[0].name == 'isEven'
    assert t.methods[0].return_type == 'bool'
    assert len(t.methods[0].args) == 0

    assert t.methods[1].name == 'sqrt'
    assert t.methods[1].return_type == 'float'
    assert len(t.methods[1].args) == 1
    assert t.methods[1].args[0].type == 'int'
    assert t.methods[1].args[0].name == 'base'
    assert t.methods[1].args[0].optional is True

    assert t.methods[2].name == 'equals'
    assert t.methods[2].return_type == 'bool'
    assert len(t.methods[2].args) == 1
    assert t.methods[2].args[0].type == 'int'
    assert t.methods[2].args[0].name == 'other'
    assert t.methods[2].args[0].optional is False

    assert t.methods[3].name == 'trisum'
    assert t.methods[3].return_type == 'int'
    assert len(t.methods[3].args) == 2
    assert t.methods[3].args[0].type == 'int'
    assert t.methods[3].args[0].name == 'a'
    assert t.methods[3].args[0].optional is False
    assert t.methods[3].args[1].type == 'int'
    assert t.methods[3].args[1].name == 'b'
    assert t.methods[3].args[1].optional is False


def test_keyword_parsing():
    print()

    keyword_test1 = '''
        keyword for (
            %structure 
                for {typename typename is int} {name var} in {typed int start} .. {typed int end} %optional ..{typed int step}% {block block}
            %
        )
    '''

    config = parse_config(keyword_test1)
    if len(config) > 1:
        assert False

    item = config[0]
    assert item.class_type.token == 'keyword'
    assert len(item.specifiers) == 1
    assert item.specifiers[0].token == 'for'

    k: Keyword | ParsingError = Keyword.process(item)
    if isinstance(k, ParsingError):
        raise k

    assert isinstance(k, Keyword)



