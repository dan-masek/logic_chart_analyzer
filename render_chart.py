import numpy as np
import cv2

from logic_data import dataset_1

# ============================================================================

labels = dataset_1["labels"]
lines = dataset_1["lines"]

# ============================================================================

#out_img = np.zeros((2000, 3200, 3), np.uint8)
out_img = cv2.imread('logic_chart_1.jpg')

for line in lines:
    cv2.line(out_img, line[0], line[1], (0, 255, 0), 2)

for label in labels:
    if label[0] == 'NODE':
        color = (255, 127, 127)
    elif label[0] == 'OUTPUT':
        color = (0, 255, 255)
    elif label[0] in ['AND', 'OR', 'XOR', 'NAND', 'NOR', 'NOT']:
        color = (127, 127, 255)
    else:
        color = (255, 127, 255)

    p1 = int(label[1][0]), int(label[1][1])
    p2 = int(label[2][0]), int(label[2][1])
    cv2.rectangle(out_img, p1, p2, color, 2)
    
    pt = p1[0] + 10, p1[1] + 30
    cv2.putText(out_img, label[0], pt, cv2.FONT_HERSHEY_DUPLEX, 1, color)
    
cv2.imwrite('logic_output.png', out_img)
