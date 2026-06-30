import os
import cv2
import numpy as np
from torch.utils.data import Dataset
from torchvision import transforms

class LeafDataset(Dataset):
    def __init__(self, images_dir, masks_dir=None, transform=None, is_train=True):
        self.images_dir = images_dir
        self.masks_dir = masks_dir
        self.transform = transform
        self.is_train = is_train
        
        self.image_filenames = sorted([f for f in os.listdir(images_dir) 
                                       if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        
        if masks_dir and os.path.exists(masks_dir):
            self.mask_filenames = sorted([f for f in os.listdir(masks_dir) 
                                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        else:
            self.mask_filenames = None
        
        if self.mask_filenames and len(self.image_filenames) != len(self.mask_filenames):
            print(f"警告：图像数量({len(self.image_filenames)})与mask数量({len(self.mask_filenames)})不一致")
    
    def __len__(self):
        return len(self.image_filenames)
    
    def __getitem__(self, idx):
        img_path = os.path.join(self.images_dir, self.image_filenames[idx])
        
        img_array = np.fromfile(img_path, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        mask = None
        if self.mask_filenames:
            mask_path = os.path.join(self.masks_dir, self.mask_filenames[idx])
            mask_array = np.fromfile(mask_path, dtype=np.uint8)
            mask = cv2.imdecode(mask_array, cv2.IMREAD_GRAYSCALE)
        
        if self.transform:
            if mask is not None:
                augmented = self.transform(image=image, mask=mask)
                image = augmented['image']
                mask = augmented['mask']
            else:
                image = self.transform(image=image)
        
        if mask is not None:
            mask = (mask > 128).astype(np.float32)
        
        return image, mask, self.image_filenames[idx]

def get_transforms(is_train=True):
    if is_train:
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 256)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    else:
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    return transform

if __name__ == '__main__':
    train_dataset = LeafDataset(
        images_dir='data/train/images',
        masks_dir='data/train/masks',
        transform=get_transforms(is_train=True)
    )
    
    val_dataset = LeafDataset(
        images_dir='data/val/images',
        masks_dir='data/val/masks',
        transform=get_transforms(is_train=False)
    )
    
    print(f"训练集大小: {len(train_dataset)}")
    print(f"验证集大小: {len(val_dataset)}")
    
    if len(train_dataset) > 0:
        img, mask, fname = train_dataset[0]
        print(f"图像形状: {img.shape}, mask形状: {mask.shape if mask is not None else 'None'}")