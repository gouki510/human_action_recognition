# -*- coding: utf-8 -*-
"""Deploy_model.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1_RLU7ESROlc6zvtKa784vMYRmt2kGiI6
"""

from google.colab import drive
drive.mount('/content/drive')

!pip install youtube-dl
import youtube_dl

def videodl(url:str):
    vdl_opts = {'outtmpl':'/content/drive/My Drive/deploy/%(title)s_video.%(ext)s','format':'bestvideo'}

    vdl = youtube_dl.YoutubeDL(vdl_opts)
    vdl.extract_info(url,download=True)

run_url = "https://www.youtube.com/watch?v=21CgGwRp69Y"

videodl(run_url)

"""# data preprocessing

"""

import numpy as np
import cv2
import os
def get_frames(filename, n_frames = 1):
    frames = []
    v_cap = cv2.VideoCapture(filename)
    v_len = int(v_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_list= np.linspace(0, v_len-1, n_frames+1, dtype=np.int16)
    for fn in range(v_len):
        success, frame = v_cap.read()
        if success is False:
            continue
        if (fn in frame_list):
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
            frames.append(frame)
    v_cap.release()
    return frames

def store_frames(frames, path2store):
    for ii, frame in enumerate(frames):
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  
        path2img = os.path.join(path2store, "frame"+str(ii)+".jpg")
        cv2.imwrite(path2img, frame)

video_path = '/content/drive/MyDrive/deploy/ロンドンオリンピック 男子100m決勝_video.mp4'
path2store = '/content/drive/MyDrive/deploy/frames'
frames = get_frames(video_path,16)
store_frames(frames,path2store)

from natsort import natsorted
import glob
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from IPython.display import HTML
from IPython.display import IFrame
from IPython.display import display

def makeAnimation(frames):
    plt.figure(figsize=(frames[0].shape[1]/72.0, frames[0].shape[0]/72.0), dpi=72)
    patch = plt.imshow(frames[0])
    plt.axis('off')

    def animate(i):
        patch.set_data(frames[i])

    anim = FuncAnimation(plt.gcf(), animate, frames=len(frames), interval=1000/30.0)
    display(HTML(anim.to_jshtml()))

path2frames = '/content/drive/MyDrive/deploy/frames'
listofframes = natsorted(glob.glob(path2frames + '/*.jpg'))
frames = []
for frame in listofframes:
  path2frame = os.path.join(path2frames,frame)
  frames.append(cv2.imread(path2frame))

makeAnimation(frames)

"""# single frame

"""

import random
path2frames = "/content/drive/MyDrive/deploy/frames"
path2store = "/content/drive/MyDrive/deploy/sigle_frame/test"
listofimgs = os.listdir(path2frames)
img = random.choice(listofimgs)
path2img = os.path.join(path2frames,img)
image = cv2.imread(path2img)
path2store = os.path.join(path2store + '.jpg')
cv2.imwrite(path2store,image)

"""# Early fusion"""

import os
import cv2
import glob
import numpy as np
import torchvision.transforms.functional as TF
from natsort import natsorted

path2frames = '/content/drive/MyDrive/deploy/frames'
path2store = '/content/drive/MyDrive/deploy/early_fusion/test'

imgs = []
listofimgs_sorted = natsorted(glob.glob(path2frames + '/*.jpg'))
print(len(listofimgs_sorted))
for path2img in listofimgs_sorted[:16]:
    img = cv2.imread(path2img)
    im_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    im_gray = cv2.resize(im_gray,(224,224))
    imgs.append(im_gray)
if len(imgs) == 16:
    im = cv2.merge(imgs)
    np.save(path2store,im)
else:
    print("frame数が異なります")

"""# late_fusion, cnn_lstm"""

path2frames = '/content/drive/MyDrive/deploy/frames'
path2store = '/content/drive/MyDrive/deploy/late_fusion/test'
listofimgs_sorted = natsorted(glob.glob(path2frames + '/*.jpg'))
data = []
for path2img in listofimgs_sorted[:16]:
    img = cv2.imread(path2img)
    img = cv2.resize(img,(224,224))
    data.append(img)
    data = random.sample(data,4)
data = np.array(data)
if data.shape == (4,224,224,3):
    
    np.save(path2store,data)
else:
    print('data_sizeが異なります')

"""# 3dcnn"""

path2frames = '/content/drive/MyDrive/deploy/frames'
path2store = '/content/drive/MyDrive/deploy/3d_cnn/test'
listofimgs_sorted = natsorted(glob.glob(path2frames + '/*.jpg'))
data = []
for path2img in listofimgs_sorted[:16]:
    img = cv2.imread(path2img)
    img = cv2.resize(img,(224,224))
    data.append(img)
    data = random.sample(data,8)
data = np.array(data)
if data.shape == (8,224,224,3):
    
    np.save(path2store,data)
else:
    print('data_sizeが異なります')

"""# predict

"""

import sys
sys.path.append('/content/drive/MyDrive/model')
import single_frame_cnn

from torchvision import models
#学習済みのresnet18を使用
cnn = models.resnet18(pretrained=True)
#device=torch.device('cuda')
#cnn.cuda()
# cnnは学習させない
for param in cnn.parameters():
    param.requires_grad = False

from torch import nn
class late_fusion(nn.Module):

  def __init__(self):
    super(late_fusion,self).__init__()

    #各timestepのframeをcnnに入力
    self.timestep0 = cnn
    self.timestep1 = cnn
    self.timestep2 = cnn
    self.timestep3 = cnn

    #特徴量をflatにしてFCLに入力
    self.fc1 = nn.Linear(4000,1024)
    self.dropout1 = torch.nn.Dropout2d(p=0.5)
    self.fc2 = nn.Linear(1024,512)
    self.dropout2 = torch.nn.Dropout(p=0.5) 
    self.fc3 = nn.Linear(512,64)
    self.dropout3 = torch.nn.Dropout(p=0.5) 
    self.fc4 = nn.Linear(64,4)
    self.relu = nn.ReLU()

  def forward(self,x):

    t0 = self.timestep0(x[:,0,:,:])
    t0 = t0.reshape(t0.size(0),-1)
    t1 = self.timestep1(x[:,1,:,:])
    t1 = t1.reshape(t1.size(0),-1)
    t2 = self.timestep2(x[:,2,:,:])
    t2 = t2.reshape(t2.size(0),-1)
    t3 = self.timestep3(x[:,3,:,:])
    t3 = t3.reshape(t3.size(0),-1)
    
    x = torch.stack([t0,t1,t2,t3])
    x = x.permute(1,0,2)
    flatten = nn.Flatten()
    x = flatten(x)
    
    
    x = self.fc1(x)
    x = self.relu(x)
    x = self.dropout1(x)
    x = self.fc2(x)
    x = self.relu(x)
    x = self.dropout2(x)
    x = self.fc3(x)
    x = self.relu(x)
    x = self.dropout3(x)
    x = self.fc4(x)


    return x

import torch
single_data = '/content/drive/MyDrive/deploy/sigle_frame/test.jpg'
early_data = '/content/drive/MyDrive/deploy/early_fusion/test.npy'
late_data = '/content/drive/MyDrive/deploy/late_fusion/test.npy'

datas = {
    0:single_data ,
    1:early_data ,
    2:late_data,
    3:late_data,
    4:late_data
}
models = {
    0:"sigle_frame_cnn",
    1:"early_fusion",
    2:"late_fusion",
    3:"3dcnn",
    4:"cnn_lstm"
}
target = {
    0:'brush_hair',
    1:'clap',
    2:'smoke',
    3:'run'
}

single_path = '/content/drive/MyDrive/model/singlecnn.pth'
early_path = '/content/drive/MyDrive/model/early_fusion.pth'
late_path =  '/content/drive/MyDrive/model/late_fusion.pth'
cnn3d_path = '/content/drive/MyDrive/model/3dcnn.pth'
cnnlstm_path = '/content/drive/MyDrive/model/cnn_lstm.pth'

#sigle_net = torch.load(single_path)

nets = []
"""single_net = models.resnet18(pretrained=True)
single_net.load_state_dict(torch.load(single_path))
nets.append(single_net)
early_net = models.resnet18(pretrained=True)
early_net.load_state_dict(torch.load(early_path))
nets.append(early_net)"""
late_net = late_fusion()
late_net.load_state_dict(torch.load(late_path))
nets.append(late_net)
"""cnn3d_net = TheModelClass(*args, **kwargs)
cnn3d_net.load_state_dict(torch.load(cnn3d_path))
nets.append(cnn3d_net)
cnnlstm_net = TheModelClass(*args, **kwargs)
cnnlstm_net.load_state_dict(torch.load(cnnlstm_path))
nets.append(cnnlstm_net)"""
data = np.load(late_data)
data = torch.from_numpy(data)
late_net()

"""for i,net in enumerate(nets):
  if net == single_net:
    image = cv2.imread(single_data)
    data = TF.to_tensor(image)
    output  = net(data)
    print("{}:{}".format(models[i],target[output.max(1[1])]))
  else:
    data = np.load(datas[i])
    output = net(data)
    print("{}:{}".format(models[i],target[output.max(1[1])]))
break"""

