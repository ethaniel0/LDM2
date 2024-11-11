Operators
- add checks to make sure no two oeprators have the same structure
- add checks to make sure no two operators with the same trigger have the 
same operator type (binary, unary-l/r, internal)
- OperatorInstances made when tokenized or when parsed? (currently when parsed)
- add checks to make sure no operator structure contains the trigger for 
another operator as a non-trigger structure element