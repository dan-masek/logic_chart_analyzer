from abc import ABCMeta, abstractmethod, abstractproperty

# ============================================================================

class Vertex(object):
    __metaclass__ = ABCMeta

    def __init__(self, max_inputs, max_outputs, bounding_box):
        self.inputs = []
        self.max_inputs = max_inputs
        self.outputs = []
        self.max_outputs = max_outputs
        self.bounding_box = bounding_box

    def add_input(self, input):
        if len(self.inputs) >= self.max_inputs:
            raise RuntimeError("Too many inputs")
        self.inputs.append(input)
        
    def add_output(self, output):
        if len(self.outputs) >= self.max_outputs:
            raise RuntimeError("Too many outputs")
        self.outputs.append(output)
        
    def contains_point(self, point):
        p1, p2 = self.bounding_box
        x0, y0 = p1
        x1, y1 = p2
        x, y = point
        return ((x0 <= x) and (x <= x1)) and ((y0 <= y) and (y <= y1))
        
    @abstractproperty
    def expression(self):
        pass

# ----------------------------------------------------------------------------

class InputTerm(Vertex):
    def __init__(self, name, bounding_box):
        super(InputTerm, self).__init__(0, 1, bounding_box)
        self.name = name
        
    @property
    def expression(self):
        return self.name

# ----------------------------------------------------------------------------

class OutputTerm(Vertex):
    def __init__(self, name, bounding_box):
        super(OutputTerm, self).__init__(1, 0, bounding_box)
        self.name = name
        
    @property
    def expression(self):
        return "%s = %s" % (self.name, self.inputs[0].expression)

# ----------------------------------------------------------------------------

class Gate(Vertex):
    def __init__(self, name, max_inputs, max_outputs, bounding_box):
        super(Gate, self).__init__(max_inputs, max_outputs, bounding_box)
        self.name = name

# ----------------------------------------------------------------------------

class UnaryGate(Gate):
    def __init__(self, name, bounding_box):
        super(UnaryGate, self).__init__(name, 1, 1, bounding_box)
        
    @property
    def expression(self):
        return "(%s %s)" % (self.name, self.inputs[0].expression)

# ----------------------------------------------------------------------------

class BinaryGate(Gate):
    def __init__(self, name, bounding_box):
        super(BinaryGate, self).__init__(name, 2, 1, bounding_box)
        
    @property
    def expression(self):
        return "(%s %s %s)" % (self.inputs[0].expression, self.name, self.inputs[1].expression)
        
# ----------------------------------------------------------------------------

class Node(Vertex):
    def __init__(self, bounding_box):
        super(Node, self).__init__(1, 1, bounding_box)
        
    @property
    def expression(self):
        return self.inputs[0].expression
        
# ----------------------------------------------------------------------------

class Connection(Vertex):
    def __init__(self, bounding_box):
        super(Connection, self).__init__(1, 1, bounding_box)
        
    @property
    def expression(self):
        return self.inputs[0].expression

# ----------------------------------------------------------------------------

class Junction(Vertex):
    def __init__(self, bounding_box):
        super(Junction, self).__init__(1, 2, bounding_box)
        
    @property
    def expression(self):
        return self.inputs[0].expression

# ============================================================================
