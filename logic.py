import numpy as np
import cv2

from logic_data import *
from logic_utils import *
from logic_classes import *

# ============================================================================

class Line(object):
    def __init__(self, endpoints):
        self.endpoints = endpoints
        self.used = False
        
    def __str__(self):
        return "{%s -> %s}" % tuple(self.endpoints)

    @property
    def is_horizontal(self):
        return is_line_horizontal(self.endpoints)
        
    def get_startpoint(self, forward):
        return self.endpoints[0 if forward else 1] 
        
    def get_endpoint(self, forward):
        return self.endpoints[1 if forward else 0]
        
    def point_distance(self, point):
        return point_to_line_dist(np.asarray(point), np.asarray(self.endpoints))
       
       
# ============================================================================

def connect_vertices(input, output):
    input.add_output(output)
    output.add_input(input)
    
# ----------------------------------------------------------------------------

def find_connected_in_elements(elements, endpoint):
    connected_elements = []
    for element in elements:
        if element.contains_point(endpoint):
            connected_elements.append(element)
    return connected_elements
    
# ============================================================================

class DataSet(object):
    def __init__(self, lines, labels):
        self._initialize_lines(lines)
        self._initialize_labels(labels)
        
        self.junctions = [] # Will be populated later
        self.connections = [] # Ditto
        
    def _initialize_lines(self, lines):
        # Split lines into horizontal and vertical
        # Note: Assuming line endpoints are sorted per line.
        # -- for horizontal x1 < x2, for vertical y1 < y2
        
        self.lines_h = [] 
        self.lines_v = []
        
        for line in lines:
            l = Line(line)
            if l.is_horizontal:
                self.lines_h.append(l)
            else:
                self.lines_v.append(l)
    
    def _initialize_labels(self, labels):
        # Split up labels into distinct types
        self.nodes = []
        self.gates = []
        self.inputs = []
        self.outputs = []

        for label in labels:
            label_name, label_bbox = label[0], inflate_bbox(label[1:4], 10)
            if label_name == 'NODE':
                self.nodes.append(Node(label_bbox))
            elif label_name == 'OUTPUT':
                self.outputs.append(OutputTerm(label_name, label_bbox))
            elif label_name == 'NOT':
                self.gates.append(UnaryGate(label_name, label_bbox))
            elif label_name in ['AND', 'NAND', 'OR', 'NOR', 'XOR', 'XNOR']:
                self.gates.append(BinaryGate(label_name, label_bbox))
            else:
                self.inputs.append(InputTerm(label_name, label_bbox))
                
    def validate(self):
        all_lines_used = True
        for line in self.lines_h + self.lines_v:
            all_lines_used = all_lines_used and line.used

        if not all_lines_used:
            raise RuntimeError("Some lines remain unused.")
            
        collections = [
            self.nodes
            , self.gates
            , self.inputs
            , self.outputs
            , self.junctions
            , self.connections
            ]

        for collection in collections:
            for element in collection:
                element.validate()

# ----------------------------------------------------------------------------

    def process_node(self, source, down):
        # Find other nodes below/above this one
        matches = []
        for i, node in enumerate(self.nodes):
            if node != source:
                dist, slope = bbox_distance_slope(source, node)
                print dist, slope
                if (slope < -SLOPE_THRESHOLD) or (slope > SLOPE_THRESHOLD):
                    matches.append((dist, slope, i))

        if len(matches) == 0:
            raise RuntimeError("No matching node")
                    
        matches = sorted(matches, key=lambda l: l[0], reverse=True)
        
        print "NODE: %s (node_id=%d)" % (("Down" if down else "Up"), matches[0][2])
        target = self.nodes[matches[0][2]]
        connect_vertices(source, target)
        
        connected_lines = []
        for i, vline in enumerate(self.lines_v):
            if vline.used:
                continue
            startpoint_v = vline.get_startpoint(down)
            if target.contains_point(startpoint_v):
                connected_lines.append(i)
        
        if len(connected_lines) != 1:
            raise RuntimeError("Invalid number of node connections")
            
        cline = self.lines_v[connected_lines[0]]
        self.lines_v[connected_lines[0]].used = True
        
        self.process_v_line(target, cline, down)
        
        print "NODE: Done"
   
# ----------------------------------------------------------------------------

    def find_connected_h_lines(self, line, tolerance, down):
        candidate_lines_r = []
        candidate_lines_l = []
        
        endpoint_v = line.get_endpoint(down)
        
        for i, h_line in enumerate(self.lines_h):
            if h_line.used:
                continue
        
            d_left = point_distance(h_line.get_startpoint(True), endpoint_v)
            d_right = point_distance(h_line.get_startpoint(False), endpoint_v)
        
            if d_left < tolerance:
                candidate_lines_r.append(i)
            if d_right < tolerance:
                candidate_lines_l.append(i)

        return candidate_lines_l, candidate_lines_r

# ----------------------------------------------------------------------------

    def process_v_line(self, source, line, down):
        endpoint_v = line.get_endpoint(down)
        print "VLINE: %s (endpoint=%s)" % (("Down" if down else "Up"), endpoint_v)
        
        connected_nodes = find_connected_in_elements(self.nodes, endpoint_v)
           
        if len(connected_nodes) > 1:
            raise RuntimeError("Too many connected nodes.")
        elif len(connected_nodes) > 0:
            node = connected_nodes[0]
            
            connect_vertices(source, node)
            self.process_node(node, down)
            return
        
        candidate_lines_l, candidate_lines_r = self.find_connected_h_lines(line, LINE_CONN_TOLERANCE, down)
        
        if len(candidate_lines_r) + len(candidate_lines_l) != 1:
            raise RuntimeError("Invalid number of connections")

        going_right = len(candidate_lines_r) > len(candidate_lines_l)
        index = candidate_lines_r[0] if going_right else candidate_lines_l[0]
        line = self.lines_h[index]
        self.lines_h[index].used = True # Mark used
        
        print "VLINE: Connection (index=%d, line=%s, right=%s)" % (index, line, going_right)
        
        vertex = Connection(None)
        self.connections.append(vertex)
        connect_vertices(source, vertex)
        
        self.process_h_line(vertex, line, going_right)
        
        print "VLINE: Done"

# ----------------------------------------------------------------------------

    def find_connected_v_lines(self, line, tolerance, forward):
        connected_lines = []
        for i, vline in enumerate(self.lines_v):
            if vline.used:
                continue # Line already used
            
            d_top = line.point_distance(vline.get_startpoint(True))
            d_bottom = line.point_distance(vline.get_startpoint(False))
            
            intersect_top = (d_top <= tolerance)
            intersect_bottom = (d_bottom <= tolerance)
            
            if intersect_top and intersect_bottom:
                raise RuntimeError("Both ends of vline intersect hline")
                
            if intersect_top or intersect_bottom:
                endpoint_h = line.get_endpoint(forward)
                endpoint_v = vline.get_endpoint(intersect_top)
                endpoint_dist = point_distance(endpoint_h, endpoint_v)
                connected_lines.append((intersect_top, endpoint_dist, i))
                
        return connected_lines

# ----------------------------------------------------------------------------

    def process_connected_v_lines(self, source, connected_lines, tolerance):
        has_end_connection = False
        current_source = source
        
        # Start from the furthest connection from the end
        connected_lines = sorted(connected_lines, key=lambda l: l[1], reverse=True)

        for i, cline in enumerate(connected_lines):
            down, dist, index = cline
            v_line = self.lines_v[index]

            print "* Processing connected line #%d (%s, %s)" % (i, cline, v_line)

            self.lines_v[index].used = True # Mark line as used
            
            if dist > tolerance: # Junction in the line
                vertex = Junction(None)
                self.junctions.append(vertex)            
            else: # End connection
                if i != len(connected_lines) - 1:
                    raise RuntimeError("Only one end connection allowed.")
                has_end_connection = True
                vertex = Connection(None)
                self.connections.append(vertex)
                
            connect_vertices(current_source, vertex)
            self.process_v_line(vertex, v_line, down)
            current_source = vertex
            
        return has_end_connection, current_source
    
# ----------------------------------------------------------------------------
    
    def process_h_line(self, source, line, forward):
        print "* Processing horizontal line %s (forward=%s)" % (line, forward)
      
        # Find any vertical lines that connect to this
        connected_lines = self.find_connected_v_lines(line, LINE_CONN_TOLERANCE, forward)
      
        # Process all the vertical connecting lines    
        has_end_connection, current_source = self.process_connected_v_lines(source, connected_lines, LINE_CONN_TOLERANCE)

        endpoint_h = line.get_endpoint(forward)
           
        connected_gates = []
        if not has_end_connection:
            # Find connected gates
            connected_gates = find_connected_in_elements(self.gates, endpoint_h)
               
            if len(connected_gates) > 1:
                raise RuntimeError("Too many connected gates.")
            elif len(connected_gates) > 0:
                gate = connected_gates[0]
                print "End in gate %s -- %s" % (gate.name, endpoint_h)
                connect_vertices(current_source, gate)
                self.process_gate(gate)

        connected_outputs = []        
        if (not has_end_connection) and (len(connected_gates) == 0):
            # Find connected outputs
            connected_outputs = find_connected_in_elements(self.outputs, endpoint_h)
                    
            if len(connected_outputs) > 1:
                raise RuntimeError("Too many connected outputs.")                
            elif len(connected_outputs) > 0:
                output = connected_outputs[0]
                print "End in output %s" % output.name   
                connect_vertices(current_source, output)
                # Nothing else to do with an output
            
        if (len(connected_lines) + len(connected_gates) + len(connected_outputs)) == 0:
            raise RuntimeError("Nothing connected")
            
        print "HLINE: Done"

# ----------------------------------------------------------------------------

    def find_output_h_lines(self, source, forward):
        connected_line_ids = []
        for i, hline in enumerate(self.lines_h):
            if hline.used: # Already used
                continue
            if source.contains_point(hline.get_startpoint(forward)):
                connected_line_ids.append(i)
        return connected_line_ids

# ----------------------------------------------------------------------------
    
    def process_output_h_line(self, source, id, forward):
        current_line = self.lines_h[id]
        # Mark line as used
        self.lines_h[id].used = True
        
        self.process_h_line(source, current_line, forward)

# ----------------------------------------------------------------------------

    def process_out_element(self, source, element_type):
        print "Processing %s '%s'..." % (element_type, source.name)
        
        connected_line_ids = self.find_output_h_lines(source, True)

        if len(connected_line_ids) > 1:
            raise RuntimeError("More than one line from %s '%s'." % (element_type, source.name))
        elif len(connected_line_ids) > 0:
            self.process_output_h_line(source, connected_line_ids[0], True)
        else:
            # Nothing to do... we may have already processed connection line
            # Rest will be caught in validation
            pass

# ----------------------------------------------------------------------------

    def process_gate(self, source):
        self.process_out_element(source, "gate")
        print "GATE: '%s' done." % source.name

# ----------------------------------------------------------------------------
    
    def process_input(self, input):
        self.process_out_element(input, "input")
        print "INPUT: '%s' done." % input.name
        
# ----------------------------------------------------------------------------

    def analyze(self):
        for input in self.inputs:
            self.process_input(input)
            
# ----------------------------------------------------------------------------
    
    @property
    def expressions(self):
        result = []
        
        for output in self.outputs:
            result.append(output.expression)
        
        return result

# ============================================================================

def process_raw_data(lines, labels):
    ds = DataSet(lines, labels)

    ds.analyze()

    print "=" * 80

    print "Validating..."
        
    ds.validate()
        
    print "=" * 80

    for expression in ds.expressions:
        print expression

# ============================================================================

SLOPE_THRESHOLD = 5
LINE_CONN_TOLERANCE = 30

for raw_dataset in raw_datasets:
    labels = raw_dataset["labels"]
    lines = raw_dataset["lines"]
    process_raw_data(lines, labels)
