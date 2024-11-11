## Start
Operators are *tough*. So here are my thoughts:

Allowing operators to have any structure makes things more difficult.
Luckily code is 1D, so there are only four classifications an operator can have:
- binary: {expr} + ... {expr}
- unary right and left: {expr}...+ or +...{expr}
- internal: ({expr}...)

The ... stands for any number of other expressions or included tokens.

## Restrictions
A number of conditions would lead to ambiguity, so here are all the ones I've thought about:
### Triggers
A trigger is a token that to be used to signify an operator. While this seems trivial,
think of the ternary operator `{expr} ? {expr} : {expr}`. Is the `?` or the `:` the operator?

The tokens are read sequentially, so the parser would come into contact with `?` first. So the trigger should
be `?` to avoid backtracking. This also allows `:` to be its own operator if we want, like the Python slicing operator.
If only `?` is the trigger here, then the parser can distinguish more easily the difference between
ternary statements and array slicing (`arr[0:5]` as an example), due to context.

Allowing operators to have a trigger that isn't the first non-expression token in the list can also cause
ambiguity. As an example, we could define two operators that look the same but have opposite triggers, such as this:

Ternary 1 = `{expr} ? {expr} : {expr}` with `?` as the trigger

Ternary 2 = `{expr} ? {expr} : {expr}` with `:` as the trigger

Say Ternary 2 works in reverse, so it evaluates the last expression if the first is false. These two would conflict 
with one another, but would register as separate operators because the triggers are different.

So the trigger must be the first non-expression token in the operator.

### Operator Type

As mentioned before, operator types are binary, unary, and internal. This is important to avoid ambiguity.

As an example, say we've defined the `>` operator two versions of the `+` operator:

The normal binary addition operator

> {expr} + {expr}

And a ternary-style operator that sums the first expression with the max of the last two:

> {expr} + {expr} > {expr}

This can be parsed in two ways: `({expr} + {expr}) > {expr}` and the ternary `{expr} + {expr} > {expr}`.
To avoid this ambiguity, any one operator trigger cannot be used to create more than one operator of the same type.

Both of these hypothetical operators would be binary, so they would be in conflict.

### Operator Overlap

To avoid ambiguity, operator structure will be read left to right. Let's walk through an example.

Let's assume the existence of the binary-style addition operator:

    {expr} + {expr}

And a ternary `@` operator that adds the first expression to the maximum of the last two:

    {expr} @ {expr} + {expr}

If read right to left, the `+` operator would be read first, and would later have to be restructured to fit the 
`@` operator. The tokens are read left to right, so `@` will be read first, and the `+` operator will remain secondary,
allowing both operators to be parsed correctly. 

Because of the operator type constraint, there can be no ambiguity about either of the `+` or the `@` operators.
