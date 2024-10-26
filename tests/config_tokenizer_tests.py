from ldm.lib_config.config_token import ConfigTokenBuilder

def test_tokenize():
    tokenizer = ConfigTokenBuilder()
    with open('test_lib.ldm_lib') as file:
        source = file.read()
        tokens = tokenizer.get_tokens(source)

        expected_tokens = 'type int ( %method ( bool isEven ) % ) keyword for ( %structure for { typename typename is' \
                            + ' int } { name var } in { typed int start } %optional .. { typed int step } % { block'\
                            + ' block } % )'
        expected_tokens = expected_tokens.split(' ')
        token_strs = [t.token for t in tokens][:len(expected_tokens)]
        assert token_strs == expected_tokens
