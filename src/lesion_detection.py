import cv2
import numpy as np
import os

def read_image_with_chinese_path(file_path):
    img_array = np.fromfile(file_path, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

def segment_leaf(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, None
    
    max_contour = max(contours, key=cv2.contourArea)
    
    leaf_mask = np.zeros_like(mask)
    cv2.drawContours(leaf_mask, [max_contour], -1, 255, -1)
    
    leaf_segmented = cv2.bitwise_and(img, img, mask=leaf_mask)
    
    return leaf_segmented, leaf_mask

def detect_lesions(img, leaf_mask):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    lower_brown = np.array([10, 50, 50])
    upper_brown = np.array([40, 255, 200])
    
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([40, 255, 255])
    
    mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    lesion_mask = cv2.bitwise_or(mask_brown, mask_yellow)
    
    if leaf_mask is not None:
        lesion_mask = cv2.bitwise_and(lesion_mask, lesion_mask, mask=leaf_mask)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    return lesion_mask

def calculate_area(mask):
    return np.sum(mask > 0)

def draw_results(img, leaf_mask, lesion_mask):
    result = img.copy()
    
    contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 10:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 0, 255), 2)
    
    leaf_contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(result, leaf_contours, -1, (0, 255, 0), 3)
    
    return result

def main():
    input_path = '叶子.png'
    output_dir = 'output'
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    img = read_image_with_chinese_path(input_path)
    if img is None:
        print('无法读取图像')
        return
    
    print('图像尺寸:', img.shape)
    
    leaf_segmented, leaf_mask = segment_leaf(img)
    
    if leaf_mask is None:
        print('未检测到叶片区域')
        return
    
    lesion_mask = detect_lesions(img, leaf_mask)
    
    leaf_area = calculate_area(leaf_mask)
    lesion_area = calculate_area(lesion_mask)
    
    if leaf_area > 0:
        lesion_ratio = (lesion_area / leaf_area) * 100
    else:
        lesion_ratio = 0
    
    print(f'叶片面积: {leaf_area} 像素')
    print(f'病斑面积: {lesion_area} 像素')
    print(f'病斑占比: {lesion_ratio:.2f}%')
    
    result_img = draw_results(img, leaf_mask, lesion_mask)
    
    cv2.imwrite(os.path.join(output_dir, 'leaf_mask.png'), leaf_mask)
    cv2.imwrite(os.path.join(output_dir, 'lesion_mask.png'), lesion_mask)
    cv2.imwrite(os.path.join(output_dir, 'leaf_segmented.png'), leaf_segmented)
    cv2.imwrite(os.path.join(output_dir, 'result.png'), result_img)
    
    print('结果已保存到 output 目录')

if __name__ == '__main__':
    main()