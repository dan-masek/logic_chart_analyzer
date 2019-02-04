import numpy as np
import cv2

from logic_data import dataset_1

# ============================================================================

labels = dataset_1["labels"]
lines = dataset_1["lines"]

# ============================================================================

out_img = np.zeros((2000, 3200, 3), np.uint8)

for line in lines:
    cv2.line(out_img, line[0], line[1], (0, 255, 0), 2)

for label in labels:
    p1 = int(label[1][0]), int(label[1][1])
    p2 = int(label[2][0]), int(label[2][1])
    cv2.rectangle(out_img, p1, p2, (0, 0, 255), 2)
    
    pt = p1[0] + 10, p1[1] + 30
    cv2.putText(out_img, label[0], pt, cv2.FONT_HERSHEY_DUPLEX, 1, (127, 127, 255))
    
cv2.imwrite('logic_output.png', out_img)
