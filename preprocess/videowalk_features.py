import argparse
import os
import torch
import random
import sys
import numpy as np
import cv2
from pathlib import Path
from typing import Tuple

from sklearn.decomposition import PCA

from videodepth_video import VideoData

# from videowalk.code.model import CRW
sys.path.append(str((Path(__file__).resolve().parent / 'videowalk' / 'code')))
from model import CRW

checkpoint_file_path = str((Path(__file__).resolve().parent / 'videowalk' / 'pretrained.pth'))

### COPY PASTED AND ADAPTED FROM VIDEOWALK CODE

def common_args(parser):
    return parser

def test_args(args=None):
    # Parse arguments
    parser = argparse.ArgumentParser(description='Label Propagation')

    # Datasets
    parser.add_argument('--workers', default=4, type=int, metavar='N',
                        help='number of data loading workers (default: 4)')
    parser.add_argument('--resume', default='', type=str, metavar='PATH',
                        help='path to latest checkpoint (default: none)')
    parser.add_argument('--manualSeed', type=int, default=777, help='manual seed')

    #Device options
    parser.add_argument('--gpu-id', default='0', type=str,
                        help='id(s) for CUDA_VISIBLE_DEVICES')
    parser.add_argument('--batchSize', default=1, type=int,
                        help='batchSize')
    parser.add_argument('--temperature', default=0.07, type=float,
                        help='temperature')
    parser.add_argument('--topk', default=10, type=int,
                        help='k for kNN')
    parser.add_argument('--radius', default=12, type=float,
                        help='spatial radius to consider neighbors from')
    parser.add_argument('--videoLen', default=20, type=int,
                        help='number of context frames')

    parser.add_argument('--cropSize', default=320, type=int,
                        help='resizing of test image, -1 for native size')

    parser.add_argument('--filelist', default='/scratch/ajabri/data/davis/val2017.txt', type=str)
    parser.add_argument('--save-path', default='./results', type=str)

    parser.add_argument('--visdom', default=False, action='store_true')
    parser.add_argument('--visdom-server', default='localhost', type=str)

    # Model Details
    parser.add_argument('--model-type', default='scratch', type=str)
    parser.add_argument('--head-depth', default=-1, type=int,
                        help='depth of mlp applied after encoder (0 = linear)')

    parser.add_argument('--remove-layers', default=['layer4'], help='layer[1-4]')
    parser.add_argument('--no-l2', default=False, action='store_true', help='')

    parser.add_argument('--long-mem', default=[0], type=int, nargs='*', help='')
    parser.add_argument('--texture', default=False, action='store_true', help='')
    parser.add_argument('--round', default=False, action='store_true', help='')

    parser.add_argument('--norm_mask', default=False, action='store_true', help='')
    parser.add_argument('--finetune', default=0, type=int, help='')
    parser.add_argument('--pca-vis', default=False, action='store_true')

    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)

    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu_id
    use_cuda = torch.cuda.is_available()
    if use_cuda:
        print('Using GPU', args.gpu_id)
        args.device = 'cuda'
    else:
        print('Using cpu')
        args.device = 'cpu'

    # Set seed
    random.seed(args.manualSeed)
    torch.manual_seed(args.manualSeed)
    if use_cuda:
        torch.cuda.manual_seed_all(args.manualSeed)

    return args



def partial_load(pretrained_dict, model, skip_keys=[]):
    model_dict = model.state_dict()

    # 1. filter out unnecessary keys
    filtered_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict and not any([sk in k for sk in skip_keys])}
    skipped_keys = [k for k in pretrained_dict if k not in filtered_dict]
    
    # 2. overwrite entries in the existing state dict
    model_dict.update(filtered_dict)

    # 3. load the new state dict
    model.load_state_dict(model_dict)

    # print('\nSkipped keys: ', skipped_keys)
    # print('\nLoading keys: ', filtered_dict.keys())

def to_numpy(tensor):
    if torch.is_tensor(tensor):
        return tensor.cpu().numpy()
    elif type(tensor).__module__ != 'numpy':
        raise ValueError("Cannot convert {} to numpy array"
                         .format(type(tensor)))
    return tensor

def to_torch(ndarray):
    if type(ndarray).__module__ == 'numpy':
        return torch.from_numpy(ndarray)
    elif not torch.is_tensor(ndarray):
        raise ValueError("Cannot convert {} to torch tensor"
                         .format(type(ndarray)))
    return ndarray

def im_to_numpy(img):
    img = to_numpy(img)
    img = np.transpose(img, (1, 2, 0)) # H*W*C
    return img

def im_to_torch(img):
    img = np.transpose(img, (2, 0, 1)) # C*H*W
    img = to_torch(img).float()
    return img

def color_normalize(x, mean, std):
    if x.size(0) == 1:
        x = x.repeat(3, 1, 1)
    for t, m, s in zip(x, mean, std):
        t.sub_(m)
        t.div_(s)
    return x

def resize(img, owidth, oheight):
    img = im_to_numpy(img)
    img = cv2.resize( img, (owidth, oheight) )
    img = im_to_torch(img)
    return img


# Video's features
def pca_feats(ff, K=1, solver='auto', whiten=True, img_normalize=True):
    ## expect ff to be   N x C x H x W

    N, C, H, W = ff.shape
    pca = PCA(
        n_components=3*K,
        svd_solver=solver,
        whiten=whiten
    )

    ff = ff.transpose(1, 2).transpose(2, 3)
    ff = ff.reshape(N*H*W, C).numpy()
    
    pca_ff = torch.Tensor(pca.fit_transform(ff))
    pca_ff = pca_ff.view(N, H, W, 3*K)
    pca_ff = pca_ff.transpose(3, 2).transpose(2, 1)

    pca_ff = [pca_ff[:, kk:kk+3] for kk in range(0, pca_ff.shape[1], 3)]

    if img_normalize:
        pca_ff = [(x - x.min()) / (x.max() - x.min()) for x in pca_ff]

    return pca_ff[0] if K == 1 else pca_ff





def init_net():

    # Create resnet model
    args = test_args([])
    # Make sure we use the CPU
    args.device = 'cpu'
    # print(args)
    model = CRW(args, vis=False).to(args.device)

    # Load weights from checkpoint
    print('==> Resuming from checkpoint..')
    checkpoint = torch.load(checkpoint_file_path, map_location=torch.device('cpu'))

    state = {}
    for k,v in checkpoint['model'].items():
        if 'conv1.1.weight' in k or 'conv2.1.weight' in k:
            state[k.replace('.1.weight', '.weight')] = v
        else:
            state[k] = v
    partial_load(state, model, skip_keys=['head'])

    del checkpoint

    model.eval()

    return model

def eval(model, video : VideoData, target_in_height : int = None):
    ims = []
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    for t in range(video.first_frame_idx, video.last_frame_idx + 1):
        # input_image = frame_archive[f"frame_{t:05d}"][:,:,::-1]
        input_image = video.get_frame(t)
        # Reverse channels order
        input_image = input_image[:,:,::-1]
        # im = Image.fromarray(np.uint8(input_image)[:,:,::-1])
        # im.show()
        # Image has to be loaded with values in [0, 1]
        im = im_to_torch(input_image / 255)
        # print("not normalized", np.max(input_image / 255), np.min(input_image / 255))
        _, height, width = im.shape
        # print(width, height)
        if target_in_height is not None and height > target_in_height:
            down_scale_factor = target_in_height / height
            im = resize(color_normalize(im, mean, std), int(width * down_scale_factor), target_in_height)
        # im = color_normalize(im, mean, std)
        # print(im.shape)
        ims.append(im)

    imgs = torch.stack(ims).unsqueeze(0)

    print("Video frames tensor shape: ", imgs.shape)

    # Run model to get pixel features

    bsize = 5   # minibatch size for computing features
    feats = []
    for b in range(0, imgs.shape[1], bsize):
        print("Batch", b, b + bsize)
        # print(imgs[:, b:b+bsize].transpose(1,2).shape)
        feat = model.encoder(imgs[:, b:b+bsize].transpose(1,2).to('cpu'))
        # feats.append(feat.cpu())
        feats.append(feat.cpu().detach().numpy())
    # features = torch.cat(feats, dim=2).squeeze(1)
    features = np.concatenate(feats, axis=2)
    # print(features.shape)

    # _, C, T, H, W = features.shape
    
    return features

### END COPY PASTE FROM VIDEOWALK CODE


def prepare_features(
        video            : VideoData,
        backend_data_path: str
    ) -> Tuple[int, int]:
    model = init_net()

    features = eval(model, video, target_in_height=480)

    print(features.shape)

    features_array = np.transpose(features[0], (1, 2, 3, 0))

    print(features_array.shape)

    if not os.path.exists(os.path.join(backend_data_path, video.video_name)):
        os.makedirs(os.path.join(backend_data_path, video.video_name))

    # Save
    # np.save(os.path.join(out_folder, vid, "videowalk_features.npy"), features_array)

    T, res_y, res_x, d_feat = features_array.shape
    all_frames_features = features_array.swapaxes(1,2).reshape((T, res_x * res_y, d_feat))

    np.save(
        os.path.join(backend_data_path, video.video_name, "features_dim.npy"),
        np.array([T, res_x, res_y, d_feat], dtype=np.uint64)
    )

    feat_memmap = np.memmap(
        os.path.join(backend_data_path, video.video_name, "features.memmap"), 
        dtype=all_frames_features.dtype,
        mode="w+",
        shape=all_frames_features.shape
    )
    # print(all_frames_features.dtype)
    feat_memmap[:] = all_frames_features[:]
    feat_memmap.flush()

    return (res_x, res_y)