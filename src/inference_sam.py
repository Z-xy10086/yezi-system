import os
import sys
import cv2
import numpy as np
import torch
from segment_anything import sam_model_registry, SamPredictor

def read_image_with_chinese_path(file_path):
    try:
        img_array = np.fromfile(file_path, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"读取图像失败: {e}")
        return None

def segment_leaf_opencv(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    max_contour = max(contours, key=cv2.contourArea)
    
    leaf_mask = np.zeros_like(mask)
    cv2.drawContours(leaf_mask, [max_contour], -1, 255, -1)
    
    return leaf_mask

def detect_lesion_candidates(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_brown = np.array([10, 50, 50])
    upper_brown = np.array([40, 255, 200])
    
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([40, 255, 255])
    
    mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    lesion_candidate = cv2.bitwise_or(mask_brown, mask_yellow)
    
    contours, _ = cv2.findContours(lesion_candidate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    points = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 20:
            M = cv2.moments(contour)
            if M["m00"] > 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                points.append([cX, cY])
    
    return np.array(points) if points else None

def run_sam_segmentation(image, sam_predictor, points):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    sam_predictor.set_image(image_rgb)
    
    if points is None or len(points) == 0:
        return None
    
    input_points = points
    input_labels = np.ones(len(input_points))
    
    masks, scores, logits = sam_predictor.predict(
        point_coords=input_points,
        point_labels=input_labels,
        multimask_output=True,
    )
    
    best_mask_idx = np.argmax(scores)
    best_mask = masks[best_mask_idx]
    
    return best_mask

def merge_masks(masks):
    if len(masks) == 0:
        return None
    
    merged = np.zeros_like(masks[0], dtype=np.uint8)
    for mask in masks:
        mask_uint8 = (mask * 255).astype(np.uint8)
        merged = cv2.bitwise_or(merged, mask_uint8)
    
    return merged

def calculate_area_ratio(leaf_mask, lesion_mask):
    leaf_area = np.sum(leaf_mask > 0)
    lesion_area = np.sum(lesion_mask > 0)
    
    if leaf_area > 0:
        ratio = (lesion_area / leaf_area) * 100
    else:
        ratio = 0
    
    return leaf_area, lesion_area, ratio

def draw_results(image, leaf_mask, lesion_mask):
    result = image.copy()
    
    if lesion_mask is not None:
        contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 10:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(result, (x, y), (x + w, y + h), (0, 0, 255), 2)
    
    if leaf_mask is not None:
        leaf_contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(result, leaf_contours, -1, (0, 255, 0), 3)
    
    return result

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(project_root, '叶子.png')
    model_path = os.path.join(project_root, 'models', 'sam_vit_b_01ec64.pth')
    output_dir = os.path.join(project_root, 'output')
    
    print(f"项目根目录: {project_root}")
    print(f"输入图像: {input_path}")
    print(f"模型路径: {model_path}")
    print(f"输出目录: {output_dir}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    image = read_image_with_chinese_path(input_path)
    if image is None:
        print('无法读取图像')
        return
    
    print(f'图像尺寸: {image.shape}')
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    if not os.path.exists(model_path):
        print(f"模型文件不存在: {model_path}")
        print("使用颜色阈值方法...")
        lesion_mask = detect_lesions_opencv(image)
    else:
        try:
            print("加载SAM模型...")
            sam = sam_model_registry["vit_b"](checkpoint=model_path)
            sam.to(device=device)
            sam_predictor = SamPredictor(sam)
            
            print("检测病斑候选点...")
            lesion_points = detect_lesion_candidates(image)
            
            if lesion_points is None or len(lesion_points) == 0:
                print("未检测到病斑候选点，使用颜色阈值方法")
                lesion_mask = detect_lesions_opencv(image)
            else:
                print(f"检测到 {len(lesion_points)} 个病斑候选点")
                print("使用SAM进行零样本分割...")
                
                masks = []
                batch_size = 10
                
                for i in range(0, len(lesion_points), batch_size):
                    batch_points = lesion_points[i:i+batch_size]
                    mask = run_sam_segmentation(image, sam_predictor, batch_points)
                    if mask is not None:
                        masks.append(mask)
                        print(f"  批次 {i//batch_size + 1}: 分割成功")
                
                if masks:
                    lesion_mask = merge_masks(masks)
                    print(f"合并了 {len(masks)} 个mask")
                else:
                    print("SAM分割失败，使用颜色阈值方法")
                    lesion_mask = detect_lesions_opencv(image)
        except Exception as e:
            print(f"SAM推理出错: {e}")
            print("使用颜色阈值方法...")
            lesion_mask = detect_lesions_opencv(image)
    
    leaf_mask = segment_leaf_opencv(image)
    
    if leaf_mask is None:
        print('未检测到叶片区域')
        return
    
    leaf_area, lesion_area, ratio = calculate_area_ratio(leaf_mask, lesion_mask)
    
    print(f'叶片面积: {leaf_area} 像素')
    print(f'病斑面积: {lesion_area} 像素')
    print(f'病斑占比: {ratio:.2f}%')
    
    result_img = draw_results(image, leaf_mask, lesion_mask)
    
    leaf_mask_path = os.path.join(output_dir, 'leaf_mask.png')
    lesion_mask_path = os.path.join(output_dir, 'lesion_mask_sam.png')
    result_path = os.path.join(output_dir, 'result_sam.png')
    
    cv2.imwrite(leaf_mask_path, leaf_mask)
    cv2.imwrite(lesion_mask_path, lesion_mask)
    cv2.imwrite(result_path, result_img)
    
    print(f'结果已保存:')
    print(f'  - {leaf_mask_path}')
    print(f'  - {lesion_mask_path}')
    print(f'  - {result_path}')

def detect_lesions_opencv(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_brown = np.array([10, 50, 50])
    upper_brown = np.array([40, 255, 200])
    
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([40, 255, 255])
    
    mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    lesion_mask = cv2.bitwise_or(mask_brown, mask_yellow)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    return lesion_mask

if __name__ == '__main__':
    main()