Operators
- add checks to make sure no two operators have the same structure
- add checks to make sure no two operators with the same trigger have the 
same operator type (binary, unary-l/r, internal)


Keywords
- check to make sure all keywords have triggers
- make sure structure def has all variables listed in spec
- check base for variables in structure spec to make sure they're all valid

Expressions Config Type
- enforce that all vars of type "block" have some closing tag as a way to signify
the end of the code block