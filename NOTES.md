Implementation Notes
====================

The idea is to use the detected lines and labels to construct a [graph](https://en.wikipedia.org/wiki/Graph_theory)
corresponding to the diagram.

## Graph representation

The graph will be represented by a collection of `Vertex` objects.
The edges (connections between vertices) will be represented by a pair of object references,
in order to facilitate easy traversal of the graph in both directions.

Each `Vertex` object has:
* an associated bounding box
* optional name
* 0 or more inputs
* 0 or more outputs
* means to obtain a logical expression of itself and all its parent vertices

Connections always go between an output and an input.

There are several different types of vertices we will use. Some, we can create directly from the input labels.
Others are created while processing, to facilitate easy connections and junctions of the input lines.

### `InputTerm`

![Image](img/example_input.jpg)

Has 0 inputs, and 1 output. Represents an input variable (e.g. J,K,M,...)

Generated logical expression is the term itself: `<name>`

### `OutputTerm`

![Image](img/example_output.jpg)

Has 1 input and 0 outputs. Represents the result of the expression (e.g. Q)

Generated logical expression is in form `<name> = <input>`

### `Gate`

Represents a logic operation (gate). We support 2 types of gates:

#### `UnaryGate`

A gate with 1 input and 1 output (e.g. NOT).

Generated logical expression is in form `(<name> <input>)`

#### `BinaryGate`

**NB:** Misnomer, this is more like N-aryGate where N > 1

**TODO:** Implement support for more than 2 inputs.

A gate with 2-4 inputs and 1 output (e.g. AND, OR, XOR, ...)

Generated logical expression with 2 inputs is in form `(<input-1> <name> <input-2>)`

Generated logical expression with 3 inputs is in form `(<input-1> <name> <input-2> <name> <input-3>)`

Generated logical expression with 4 inputs is in form `(<input-1> <name> <input-2> <name> <input-3> <name> <input-4>)`

### `Node`

![Image](img/example_node_pair.jpg)

Has 1 input and 1 output. A pair of nodes represents a bridge (to avoid crossing lines).

Generated logical expression is: `<input>`

### `Connection`

![Image](img/example_connection.jpg)

Has 1 input and 1 output. Represents a corner in the connecting lines (horizontal and vertical lines connected at the end).

Generated logical expression is: `<input>`

### `Junction`

![Image](img/example_junction.jpg)

Has 1 input and 2 outputs. Represents a T-connection between a horizontal and vertical line.

Generated logical expression is: `<input>`

----

