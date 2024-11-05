from ldm.source_tokenizer.tokenize import Token, TokenizerItems, Tokenizer, TokenType
from ldm.ast.parsing_types import TokenIterator, ParsingItems, ParsingContext, ExpressionToken
from ldm.lib_config2.parsing_types import Structure, StructureComponentType, StructureComponent


def parse_expression(tokens: TokenIterator, items: ParsingItems):
    t, _ = next(tokens)
    val: str = t.type.value[0]

    if t.type == TokenType.Identifier:
        val = t.value

    if val in items.config_spec.initializer_formats:
        spec = items.config_spec.initializer_formats[val]
        val_type = spec.ref_type
    else:
        val_type = t.type.value[0]

    return t, val_type


class StructureParser:
    def __init__(self, items: ParsingItems, tokenizer_items: TokenizerItems):
        self.items = items
        self.tokenizer_items = tokenizer_items

        self.structure_count = 0
        self.parsed_variables: dict[str, Token] = {}
        self.context: ParsingContext = ParsingContext()
        self.tokens: TokenIterator = TokenIterator([])

    def __handle_typename(self, comp: StructureComponent, structure: Structure):
        var = structure.component_specs[comp.value]
        # get typename, check primitive types
        tn, _ = next(self.tokens)
        if tn.value not in self.items.config_spec.primitive_types:
            raise RuntimeError(f'{tn} not a type on line {tn.line}')
        self.parsed_variables[var.name] = tn
        self.structure_count += 1

    def __handle_name(self, comp: StructureComponent, structure: Structure):
        var = structure.component_specs[comp.value]

        var_type = 'existing-global'
        if 'type' in var.other:
            var_type = var.other['type']

        varname, _ = next(self.tokens)

        if var_type == 'existing-global':
            if not self.context.has_global(varname.value):
                raise RuntimeError(f'{varname} does not exist at line {varname.line}')
        elif var_type == 'existing-local':
            if not self.context.has_local(varname.value):
                raise RuntimeError(f'{varname} does not exist at line {varname.line}')
        elif var_type == 'new-global':
            if self.context.has_global(varname.value):
                raise RuntimeError(f'{varname} already exists at line {varname.line}')
        elif var_type == 'new-local':
            if self.context.has_local(varname.value):
                raise RuntimeError(f'{varname} already exists at line {varname.line}')
        elif var_type != 'any':
            raise RuntimeError(f'make-variable type "{var_type}" not recognized')

        self.parsed_variables[var.name] = varname
        self.structure_count += 1

    def __handle_expression(self, comp: StructureComponent, structure: Structure):
        var = structure.component_specs[comp.value]

        expr, var_type = parse_expression(self.tokens, self.items)

        self.parsed_variables[var.name] = ExpressionToken(expr, var_type)
        self.structure_count += 1

    def __handle_variable(self, comp: StructureComponent, structure: Structure):
        if comp.value not in structure.component_specs:
            raise RuntimeError(f"structure component {comp.value} not found")
        var = structure.component_specs[comp.value]

        if var.base == 'typename':
            self.__handle_typename(comp, structure)

        elif var.base == 'name':
            self.__handle_name(comp, structure)

        elif var.base == 'expression':
            self.__handle_expression(comp, structure)

        else:
            raise RuntimeError(f'base {var.base} not recognized')

    def parse(self, tokens: TokenIterator, structure: Structure, context: ParsingContext) -> dict[str, Token]:
        self.structure_count = 0
        self.parsed_variables: dict[str, Token] = {}
        self.context = context
        self.tokens = tokens

        while self.structure_count < len(structure.component_defs) and not tokens.done():
            s = structure.component_defs[self.structure_count]

            if s.component_type == StructureComponentType.Variable:
                self.__handle_variable(s, structure)

            elif s.component_type == StructureComponentType.String:
                string_tokens = Tokenizer(self.tokenizer_items).tokenize(s.value)
                for token in string_tokens:
                    tn, _ = next(tokens)
                    if tn.value != token.value:
                        raise RuntimeError(f'Expected {token.value}, got {tn.value} at line {tn.line}')
                self.structure_count += 1

            elif s.component_type == StructureComponentType.Command:
                pass

            elif s.component_type == StructureComponentType.EndCommand:
                pass

        return self.parsed_variables
