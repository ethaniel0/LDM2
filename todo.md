Structures
- add checks to make sure no two structures have the same structure
- add checks to make sure no two operator-creating structures with the same trigger have the 
same operator type (binary, unary-l/r, internal) (right now it'll just take the first one)

- allow a structure to create multiple variables or types
- for typename_attributes, specify all (map)
- allow searching through structures of type expressions for elements of specific names (like constructors),
    this may already be possible with the current system
- operator overloading
  - ability to do arbitrarily-ordered typing 
    (like in Java, where you can use a class even if it's defined later in the code)
- operator overload type lists, individual overloads can get too verbose
- operator overloads should be for all components of type expression, not just operators (e.g. if, for, etc.)
- unordered parameters (`public static void` and `static public void` both work in Java)
- repeated elements with a set or ranged number of repeats
- repeated elements whose number of repeats is determined by some other value
- forward declarations if wanted
- existing scope variables

Honestly I should get rid of the concept of operators altogether in the traditional sense,
and operator overloads should be applied to anything that has an expression element.
Instead I should have a tag system so you can group types of structures together for better filtering.

Also do I need a tokenizer? I define the structures yes, but it doesn't really do all that much.
The exception would be for numbers. I'd need to add regex for that. A discrete tokenizer also means
it's hard to account for whitespace in the definition of languages where it's needed, like Python.
I've come up with potential ways to get around that, but I need to think more about the practicality of that.

I need to refactor the structure parser. It's over 900 lines right now, and I
need to use more active classes here. Everything right now is more or less just a record class,
with the structure parser in charge of all the work. I just need to figure out how reasonable ways
to split that work.