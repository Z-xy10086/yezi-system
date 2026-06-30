import os
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision.models.segmentation import deeplabv3_resnet50
from torchvision import transforms

def read_image_with_chinese_path(file_path):
    img_array = np.fromfile(file_path, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

def preprocess_image(image, target_size=(256, 256)):
    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(target_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_tensor = transform(image_rgb)
    image_tensor = image_tensor.unsqueeze(0)
    return image_tensor

def load_model(model_path, device):
    model = deeplabv3_resnet50(pretrained=False)
    num_classes = 1
    model.classifier[-1] = nn.Conv2d(256, num_classes, kernel_size=(1, 1), stride=(1, 1))
    
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model = model.to(device)
    model.eval()
    
    return model

def predict(model, image_tensor, device, original_size):
    with torch.no_grad():
        image_tensor = image_tensor.to(device)
        outputs = model(image_tensor)['out']
        pred = torch.sigmoid(outputs)
        pred = (pred > 0.5).float()
    
    pred_np = pred.cpu().numpy()[0, 0, :, :]
    pred_resized = cv2.resize(pred_np, (original_size[1], original_size[0]), interpolation=cv2.INTER_NEAREST)
    
    return pred_resized

def calculate_area_ratio(leaf_mask, lesion_mask):
    leaf_area = np.sum(leaf_mask > 0)
    lesion_area = np.sum(lesion_mask > 0)
    
    if leaf_area > 0:
        ratio = (lesion_area / leaf_area) * 100
    else:
        ratio = 0
    
    return leaf_area, lesion_area, ratio

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

def draw_results(image, leaf_mask, lesion_mask):
    result = image.copy()
    
    contours, _ = cv2.findContours((lesion_mask * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
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
    input_path = '叶子.png'
    model_path = 'models/best_model.pth'
    output_dir = 'output'
    
    os.makedirs(output_dir, exist_ok=True)
    
    image = read_image_with_chinese_path(input_path)
    if image is None:
        print('无法读取图像')
        return
    
    print('图像尺寸:', image.shape)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    if os.path.exists(model_path):
        print("加载预训练模型...")
        model = load_model(model_path, device)
        
        image_tensor = preprocess_image(image)
        lesion_mask = predict(model, image_tensor, device, image.shape[:2])
    else:
        print("未找到预训练模型，使用颜色阈值方法...")
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
    
    cv2.imwrite(os.path.join(output_dir, 'leaf_mask.png'), leaf_mask)
    cv2.imwrite(os.path.join(output_dir, 'lesion_mask.png'), (lesion_mask * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(output_dir, 'result.png'), result_img)
    
    print('结果已保存到 output 目录')

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
    
    return lesion_mask / 255.0

if __name__ == '__main__':
    main()