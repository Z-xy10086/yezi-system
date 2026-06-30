import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision.models.segmentation import deeplabv3_resnet50
from torchvision import transforms
from tqdm import tqdm
import numpy as np

from datasets import LeafDataset, get_transforms

class DiceLoss(nn.Module):
    def __init__(self, smooth=1.0):
        super(DiceLoss, self).__init__()
        self.smooth = smooth
    
    def forward(self, pred, target):
        pred = torch.sigmoid(pred)
        pred = pred.view(-1)
        target = target.view(-1)
        
        intersection = (pred * target).sum()
        union = pred.sum() + target.sum()
        
        dice = (2.0 * intersection + self.smooth) / (union + self.smooth)
        return 1.0 - dice

def train_one_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    
    for images, masks, _ in tqdm(dataloader):
        images = images.to(device)
        masks = masks.to(device)
        
        optimizer.zero_grad()
        
        outputs = model(images)['out']
        
        if outputs.size(1) > 1:
            outputs = outputs[:, 0:1, :, :]
        
        loss = criterion(outputs, masks.unsqueeze(1))
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item() * images.size(0)
    
    return running_loss / len(dataloader.dataset)

def validate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    dice_scores = []
    
    with torch.no_grad():
        for images, masks, _ in tqdm(dataloader):
            images = images.to(device)
            masks = masks.to(device)
            
            outputs = model(images)['out']
            
            if outputs.size(1) > 1:
                outputs = outputs[:, 0:1, :, :]
            
            loss = criterion(outputs, masks.unsqueeze(1))
            running_loss += loss.item() * images.size(0)
            
            pred = torch.sigmoid(outputs)
            pred = (pred > 0.5).float()
            
            intersection = (pred * masks.unsqueeze(1)).sum().item()
            union = pred.sum().item() + masks.sum().item()
            
            if union > 0:
                dice = 2.0 * intersection / union
                dice_scores.append(dice)
    
    avg_loss = running_loss / len(dataloader.dataset)
    avg_dice = np.mean(dice_scores) if dice_scores else 0.0
    
    return avg_loss, avg_dice

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
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
    
    if len(train_dataset) == 0:
        print("警告：训练集为空！请先准备数据集")
        return
    
    train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False)
    
    model = deeplabv3_resnet50(pretrained=True)
    num_classes = 1
    model.classifier[-1] = nn.Conv2d(256, num_classes, kernel_size=(1, 1), stride=(1, 1))
    
    model = model.to(device)
    
    criterion = DiceLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)
    
    num_epochs = 20
    best_dice = 0.0
    
    os.makedirs('models', exist_ok=True)
    
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch + 1}/{num_epochs}")
        
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_dice = validate(model, val_loader, criterion, device)
        
        scheduler.step()
        
        print(f"训练损失: {train_loss:.4f}")
        print(f"验证损失: {val_loss:.4f}")
        print(f"验证Dice: {val_dice:.4f}")
        
        if val_dice > best_dice:
            best_dice = val_dice
            torch.save(model.state_dict(), os.path.join('models', 'best_model.pth'))
            print(f"保存最佳模型 (Dice: {best_dice:.4f})")
    
    torch.save(model.state_dict(), os.path.join('models', 'final_model.pth'))
    print("训练完成！")

if __name__ == '__main__':
    main()