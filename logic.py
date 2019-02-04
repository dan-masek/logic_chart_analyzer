import numpy as np
import cv2

from logic_data import *
from logic_utils import *
from logic_classes import *

# ============================================================================

labels = dataset_1["labels"]
lines = dataset_1["lines"]

# ============================================================================

# STEP: Split lines into horizontal and vertical

lines_h = []
lines_v = []

for line in lines:
    if is_line_horizontal(line):
        lines_h.append(line)
    else:
        lines_v.append(line)
    
# Note: Assume line endpoints are sorted per line.
# -- for horizontal x1 < x2, for vertical y1 < y2

# ============================================================================

# STEP: Split up labels into distinct types

nodes = []
gates = []
inputs = []
outputs = []
junctions = [] # Will be populated later
connections = [] # Ditto

for label in labels:
    label_name, label_bbox = label[0], inflate_bbox(label[1:3], 10)
    if label_name == 'NODE':
        nodes.append(Node(label_bbox))
    elif label_name == 'OUTPUT':
        outputs.append(OutputTerm(label_name, label_bbox))
    elif label_name == 'NOT':
        gates.append(UnaryGate(label_name, label_bbox))
    elif label_name in ['AND', 'OR', 'XOR', 'NAND', 'NOR']:
        gates.append(BinaryGate(label_name, label_bbox))
    else:
        inputs.append(InputTerm(label_name, label_bbox))

# ============================================================================

def connect_vertices(input, output):
    input.add_output(output)
    output.add_input(input)

# ============================================================================

def process_node(source, down):
    # Find other nodes below/above this one
    matches = []
    for i, node in enumerate(nodes):
        if node != source:
            dist, slope = bbox_distance_slope(source, node)
            if (slope < -20) or (slope > 20):
                matches.append((dist, slope, i))
    
    matches = sorted(matches, key=lambda l: l[0], reverse=True)
    if len(matches) == 0:
        raise RuntimeError("No matching node")
    
    print "NODE: %s (node_id=%d)" % (("Down" if down else "Up"), matches[0][2])
    target = nodes[matches[0][2]]
    connect_vertices(source, target)
    
    connected_lines = []
    for i, vline in enumerate(lines_v):
        startpoint_v = vline[0] if down else vline[1]
        if target.contains_point(startpoint_v):
            connected_lines.append(i)
    
    if len(connected_lines) != 1:
        raise RuntimeError("Invalid number of node connections")
        
    cline = lines_v[connected_lines[0]]
    del lines_v[connected_lines[0]]
    process_v_line(target, cline, down)
    
    print "NODE: Done"

# ----------------------------------------------------------------------------
# TODO: Refactor, this is almost the same thing as processing input

def process_gate(source):
    print "Processing gate '%s'..." % source.name
    # gate will have horizontal line starting nearby...
    candidate_line_ids = []
    for i, line in enumerate(lines_h):
        if source.contains_point(line[0]):
            candidate_line_ids.append(i)
    if len(candidate_line_ids) > 1:
        raise RuntimeError("More than one line from gate '%s'." % source.name)

    if len(candidate_line_ids) == 1:
        current_line = lines_h[candidate_line_ids[0]]
        # Nothing else should use this line, so drop it from the list
        del lines_h[candidate_line_ids[0]]
        
        process_h_line(source, current_line, True)

    print "GATE: Done"
    
# ----------------------------------------------------------------------------

def process_v_line(source, line, down):
    THRESHOLD = 30
    
    endpoint_v = line[1] if down else line[0]

    print "VLINE: %s (endpoint=%s)" % (("Down" if down else "Up"), endpoint_v)
    
    connection_count = 0
    for node in nodes:
        if node.contains_point(endpoint_v):
            connect_vertices(source, node)
            process_node(node, down)
            connection_count += 1
            
    if connection_count > 1:
        raise RuntimeError("Too many node connections")
        
    if connection_count == 1:
        return

    # try horizontal
    candidate_lines_r = []
    candidate_lines_l = []
    
    for i, line in enumerate(lines_h):
        d_left = point_distance(line[0], endpoint_v)
        d_right = point_distance(line[1], endpoint_v)
    
        if d_left < THRESHOLD:
            candidate_lines_r.append(i)
        if d_right < THRESHOLD:
            candidate_lines_l.append(i)

    if len(candidate_lines_r) + len(candidate_lines_l) != 1:
        raise RuntimeError("Invalid number of connections")

    going_right = len(candidate_lines_r) > len(candidate_lines_l)
    index = candidate_lines_r[0] if going_right else candidate_lines_l[0]
    line = lines_h[index]
    del lines_h[index]
    
    print "VLINE: Connection (index=%d, line=%s, right=%s)" % (index, line, going_right)
    
    vertex = Connection(None)
    connections.append(vertex)
    connect_vertices(source, vertex)
    
    process_h_line(vertex, line, going_right)
    
    print "VLINE: Done"

# ----------------------------------------------------------------------------

def process_h_line(source, line, forward):
    print "* Processing horizontal line %s (forward=%s)" % (line, forward)
    THRESHOLD = 30
    
    endpoint_h = line[1] if forward else line[0]
    
    # Find any vertical lines that connect to this
    connected_lines = []
    for i, vline in enumerate(lines_v):
        d_top = point_to_line_dist(np.asarray(vline[0]), np.asarray(line))
        d_bottom = point_to_line_dist(np.asarray(vline[1]), np.asarray(line))
        
        intersect_top = (d_top <= THRESHOLD)
        intersect_bottom = (d_bottom <= THRESHOLD)
        
        if intersect_top and intersect_bottom:
            raise RuntimeError("Both ends of vline intersect hline")
            
        endpoint_v = vline[0] if intersect_top else vline[1]
       
        if intersect_top or intersect_bottom:
            endpoint_dist = point_distance(endpoint_h, endpoint_v)
            connected_lines.append((intersect_top, endpoint_dist, i))
            
    connection_count = len(connected_lines)

    # Start from the furthest connection from the end
    connected_lines = sorted(connected_lines, key=lambda l: l[1], reverse=True)

    # Process all the vertical connecting lines    
    has_end_connection = False
    current_source = source
    i = 0
    for i, cline in enumerate(connected_lines):
        print "* Processing connected line #%d (%s, %s)" % (i, cline, lines_v[cline[2]])
        down, dist, index = cline
        v_line = lines_v[index]
        del lines_v[index]
        if dist > THRESHOLD: # Junction in the line
            vertex = Junction(None)
            junctions.append(vertex)
            connect_vertices(current_source, vertex)
            process_v_line(vertex, v_line, down)
        else: # End connection
            if i != len(connected_lines) - 1:
                raise RuntimeError("Only one end connection allowed.")
            has_end_connection = True
            vertex = Connection(None)
            connections.append(vertex)
            connect_vertices(current_source, vertex)
            process_v_line(vertex, v_line, down)
        current_source = vertex        
       
    has_gate_connection = False
    if not has_end_connection:
        # Find connected gates
        for gate in gates:
            if gate.contains_point(endpoint_h):
                has_gate_connection = True
                connection_count += 1
                connect_vertices(current_source, gate)
                print "End in gate %s -- %s" % (gate.name, endpoint_h)
                process_gate(gate)
    
        # Find connected outputs
        if not has_gate_connection:
            for output in outputs:
                if output.contains_point(endpoint_h):
                    connection_count += 1
                    connect_vertices(current_source, output)
                    print "End in output %s" % output.name        
        
    if connection_count == 0:
        raise RuntimeError("Nothing connected")
        
    print "HLINE: Done"

# ----------------------------------------------------------------------------

def process_input(input):
    print "Processing input '%s'..." % input.name
    # Input will have horizontal line starting nearby...
    candidate_line_ids = []
    for i, line in enumerate(lines_h):
        if input.contains_point(line[0]):
            candidate_line_ids.append(i)
    if len(candidate_line_ids) > 1:
        raise RuntimeError("More than one line from input '%s'." % input.name)

    current_line = lines_h[candidate_line_ids[0]]
    # Nothing else should use this line, so drop it from the list
    del lines_h[candidate_line_ids[0]]
    
    process_h_line(input, current_line, True)

    print "INPUT: Done"

# ============================================================================

for input in inputs:
    process_input(input)

if (len(lines_h) != 0) or (len(lines_v) != 0):
    raise RuntimeError("Leftover lines")

print "=" * 80

for output in outputs:
    print output.expression































