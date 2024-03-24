import os, tifffile, numpy as np

import torch

from pprint import pprint 
from dataset_utils import DatasetUtils

import scipy
import matplotlib.pyplot as plt
from mpl_interactions import ipyplot as iplt
import skimage


class CellDataset(torch.utils.data.Dataset):

    def __init__(self, images_dir, masks_dir, padding=64):
        self.images_dir = images_dir
        self.masks_dir = masks_dir
        self.padding = padding

        self.image_paths = sorted([os.path.join(images_dir, f) for f in os.listdir(images_dir) if f.endswith('.tif')])
        self.mask_paths = sorted([os.path.join(masks_dir, f) for f in os.listdir(masks_dir) if f.endswith('.tif')])

        assert len(self.image_paths) == len(self.mask_paths), "The number of images and masks must be the same"

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):    # this is missing the interpolation and the mirror padding (but I don't think mirror padding is needed)
        image = tifffile.imread(self.image_paths[idx])
        mask = tifffile.imread(self.mask_paths[idx])

        image = image.astype(np.float32)
        mask = mask.astype(np.float32)

        image_min = image.min()
        image_max = image.max()
        image = (image - image_min) / (image_max - image_min)

        desired_height, desired_width = 139, 140
        image = DatasetUtils().apply_padding(image, desired_height, desired_width)
        mask = DatasetUtils.apply_padding(mask, desired_height, desired_width)

        image = torch.from_numpy(image)
        mask = torch.from_numpy(mask)

        #mirror padding
        image = torch.nn.functional.pad(image, (self.padding, self.padding, self.padding, self.padding), mode='reflect')    
        mask = torch.nn.functional.pad(mask, (self.padding, self.padding, self.padding, self.padding), mode='reflect')
        if len(image.shape) == 3:
            image = image.unsqueeze(0)
        if len(mask.shape) == 3:
            mask = mask.unsqueeze(0)

        return image, mask

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]


    def interpolate(self, image, type='cubic'):
        image = image.squeeze(0)
        scale_factor = 2.1875
        if type == 'cubic':
            #use cubic interpolation to resize the image along z-axis by scale factor of 2.1875 (not available with pytorch)
            img_resized = scipy.ndimage.zoom(image, (scale_factor, 1, 1), order=3)
            img_resized = torch.from_numpy(img_resized).unsqueeze(0)#convert to tensor, re-add channel dimension
            return img_resized #shape: [1, 112, 139, 140]
        
        if type == 'nearest':
            #use nearest interpolation for resizing mask to avoid having pixels with values between 0 and 1
            img_resized = scipy.ndimage.zoom(image, (scale_factor, 1, 1), order=0)
            img_resized = torch.from_numpy(img_resized).unsqueeze(0)#convert to tensor, re-add channel dimension    
            return img_resized #shape: [1, 112, 139, 140]
        if type == 'skimage':
            #this is what they use in the paper (although they use order=1 which is not bicubic)
            D_des = int(scale_factor * image.shape[0])
            img_resized = skimage.transform.resize(image.numpy(), (D_des+1, image.shape[1], image.shape[2]), order=3)
            img_resized = torch.from_numpy(img_resized).unsqueeze(0)
            return img_resized
            
        
    def print_image(self, image, slice_index=0):
        if len(image.shape) == 4:
            image = image.squeeze(0)
        image_slice = image[slice_index]
        plt.imshow(image_slice, cmap='gray')
        plt.show()

    def print_image_3D(self, image, slice_index=0):
        if len(image.shape) == 4:
            image = image.squeeze(0)
        def func(slice_index):
            #returns slics of image
            return image[int(slice_index)]
        n_ind = image.shape[0]
        control = iplt.imshow(func, slice_index=(0, n_ind-1), cmap='gray')
        plt.show()





if __name__ == "__main__":
    images_dir = os.path.join("data", "images", "train", "Images")
    ground_truth_dir = os.path.join("data", "GroundTruth", "train", "GroundTruth_NDN")

    dataset = CellDataset(images_dir=images_dir, masks_dir=ground_truth_dir)
    print(len(dataset))
    max_h, max_w = 0, 0
    
    # fixed ur dataset 
    items = [item for item in dataset]  # load the entire thing into memory
    for item in items[-5:]:             # let's print the last 5

        image, mask = item 
        pprint({'image': image.shape, 'mask': mask.shape})
        #dataset.print_image_3D(mask)

        image_resized, mask_resized = dataset.interpolate(image, type='skimage'), dataset.interpolate(mask, type='nearest')
        pprint({'image_resized_cubic': image_resized.shape, 'mask_resized': mask_resized.shape})
        dataset.print_image_3D(image_resized)
        
        # pprint is a python built-in for fixing dictionary printing
        
        # but it's not really necessary here as the dict is small...
        # (dict joke)
