# -*- coding: utf-8 -*-
"""CNN3D.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1u4hYWDbD-0OWYgWVR86fIVDOv7mYtdAe
"""

from google.colab import drive
drive.mount('/content/drive')

import os
import glob
from torch.utils.data import Dataset
import torch
import torchvision.transforms as transforms
from torchvision import models
import numpy as np
import torch.nn as nn
import torch.optim as optim
import torchvision
import torch.nn.functional as F
import torchvision.transforms.functional as TF
import shutil
import random
import cv2
from tqdm import tqdm
import itertools
import math

"""# Data

---


"""

original_dir = 'drive/MyDrive/latefusion'

train_data_list = []
test_data_list = []
target_train = []
#train data
listofcats = ['brush_hair','clap','smoke','run']
for i,cat in enumerate(listofcats):
  path2cat = os.path.join(original_dir + '/' + 'train' + '/' + str(cat))
  listofdatas = os.listdir(path2cat)
  print("{}:{}".format(cat,len(listofdatas)))
  for data in listofdatas:
    path2data = os.path.join(original_dir + '/' + 'train' + '/' + str(cat) + '/' + str(data))
    d = np.load(path2data)
    train_data_list.append(random.sample(d,8))
  target_train.append([i]*len(listofdatas))

#test data
target_test = []
for j,cat in enumerate(listofcats):
  path2cat = os.path.join(original_dir + '/' + 'test' + '/' + str(cat))
  listofdatas = os.listdir(path2cat)
  print("{}:{}".format(cat,len(listofdatas)))
  for data in listofdatas:
    path2data = os.path.join(original_dir + '/' + 'test' + '/' + str(cat) + '/' + str(data))
    d = np.load(path2data)
    test_data_list.append(random.sample(d,8))
  target_test.append([j]*len(listofdatas))

target_train2 = list(itertools.chain.from_iterable(target_train))
target_test2 = list(itertools.chain.from_iterable(target_test))

"""# Tensorに変換

---


"""

# (T,W,H,C) -> (C,T,W,H)
train_data_list2 = []
for ts in train_data_list:
  #print(ts.shape)
  ts = torch.from_numpy(ts.transpose(3,0,1,2))
  #print(ts.shape)
  train_data_list2.append(ts)
X_train = torch.stack(train_data_list2)
X_train = X_train
print("X_train_size=",X_train.shape)
Y_train = torch.tensor([torch.from_numpy(np.array(i)) for i in target_train2])
print(type(Y_train))
Y_train = Y_train
print("Y_train_size=",Y_train.shape)
test_data_list2 = []
for ts in test_data_list:
  #print(ts.shape)
  ts = torch.from_numpy(ts.transpose(3,0,1,2))
  #print(ts.shape)
  test_data_list2.append(ts)
X_test = torch.stack(test_data_list2)
print("X_test_size=",X_test.shape)
Y_test = torch.stack([torch.from_numpy(np.array(i)) for i in target_test2])
print("Y_test_size=",Y_test.shape)

"""# Torchにload

---


"""

train_dataset = torch.utils.data.TensorDataset(X_train, Y_train)
train_loader = torch.utils.data.DataLoader(train_dataset,batch_size=4,shuffle=True)
test_dataset = torch.utils.data.TensorDataset(X_test, Y_test)
test_loader = torch.utils.data.DataLoader(test_dataset,batch_size=4,shuffle=True)

"""# Model

---


"""

class C3D(nn.Module):
    def __init__(self):

        super(C3D, self).__init__()
        self.group1 = nn.Sequential(
            nn.Conv3d(3, 64, kernel_size=3, padding=2),
            nn.BatchNorm3d(64),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(2, 2, 2), stride=(1, 2, 2)))
        self.group2 = nn.Sequential(
            nn.Conv3d(64, 128, kernel_size=3, padding=2),
            nn.BatchNorm3d(128),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(2, 2, 2), stride=(2, 2, 2)))
        self.group3 = nn.Sequential(
            nn.Conv3d(128, 256, kernel_size=3, padding=2),
            nn.BatchNorm3d(256),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(2, 2, 2), stride=(2, 2, 2)))
        self.group4 = nn.Sequential(
            nn.Conv3d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm3d(512),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(2, 2, 2), stride=(2, 2, 2)))
        self.group5 = nn.Sequential(
            nn.Conv3d(512, 512, kernel_size=3, padding=1),
            nn.BatchNorm3d(512),
            nn.ReLU(),
            nn.MaxPool3d(kernel_size=(1, 2, 2), stride=(2, 2, 2), padding=(0, 1, 1)))
        self.fc1 = nn.Sequential(
            nn.Linear(32768, 4096),
            nn.ReLU(),
            nn.Dropout(0.5))
        self.fc2 = nn.Sequential(
            nn.Linear(4096, 2048),
            nn.ReLU(),
            nn.Dropout(0.5))
        self.fc = nn.Sequential(
            nn.Linear(2048, 4))         

      
    def forward(self, x):
        out = self.group1(x)
        out = self.group2(out)
        out = self.group3(out)
        out = self.group4(out)
        out = self.group5(out)
        out = out.view(out.size(0), -1)
        out = self.fc1(out)

        out = self.fc2(out)
        out = self.fc(out)
        return out

device = torch.device('cuda')
net = C3D()
net.cuda()

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=0.0001, momentum=0.9)

class EarlyStopping:

    def __init__(self, patience=5, verbose=False, path='checkpoint_model.pth'):
    
        self.patience = patience    #設定ストップカウンタ
        self.verbose = verbose      #表示の有無
        self.counter = 0            #現在のカウンタ値
        self.best_score = None      #ベストスコア
        self.early_stop = False     #ストップフラグ
        self.val_loss_min = np.Inf   #前回のベストスコア記憶用
        self.path = path             #ベストモデル格納path

    def __call__(self, val_loss, model):
        
        score = -val_loss

        if self.best_score is None:  #1Epoch目の処理
            self.best_score = score   #1Epoch目はそのままベストスコアとして記録する
            self.checkpoint(val_loss, model)  #記録後にモデルを保存してスコア表示する
        elif score < self.best_score:  # ベストスコアを更新できなかった場合
            self.counter += 1   #ストップカウンタを+1
            if self.verbose:  #表示を有効にした場合は経過を表示
                print(f'EarlyStopping counter: {self.counter} out of {self.patience}')  #現在のカウンタを表示する 
            if self.counter >= self.patience:  #設定カウントを上回ったらストップフラグをTrueに変更
                self.early_stop = True
        else:  #ベストスコアを更新した場合
            self.best_score = score  #ベストスコアを上書き
            self.checkpoint(val_loss, model)  #モデルを保存してスコア表示
            self.counter = 0  #ストップカウンタリセット

    def checkpoint(self, val_loss, model):

        if self.verbose:  #表示を有効にした場合は、前回のベストスコアからどれだけ更新したか？を表示
            print(f'Validation loss decreased ({self.val_loss_min:.6f} --> {val_loss:.6f}).  Saving model ...')
        torch.save(model.state_dict(), self.path)  #ベストモデルを指定したpathに保存
        self.val_loss_min = val_loss  #その時のlossを記録する

#loss,accuracyを格納
train_loss_list = []
train_acc_list = []
val_loss_list = []
val_acc_list = []

nb_epoch = 10
early_stopping = EarlyStopping(patience=30, verbose=True,path='drive/MyDrive/model/cnn_3d.pth')
for epoch in range(nb_epoch):
    train_loss = 0
    train_acc = 0
    val_loss = 0
    val_acc = 0

    #train
    net.train()
    for i, (data, labels) in enumerate(train_loader):
      
      data, labels = data.to(device), labels.to(device)
      data = data.float()
      labels = labels.long()
      #print("labels",labels.shape)
      optimizer.zero_grad()
      outputs = net(data)
      loss = criterion(outputs, labels)
      train_loss += loss.item()
      train_acc += (outputs.max(1)[1] == labels).sum().item()
      loss.backward()
      optimizer.step()
    avg_train_loss = train_loss / len(train_loader.dataset)
    avg_train_acc = train_acc / len(train_loader.dataset)

    train_loss_list.append(avg_train_loss)
    train_acc_list.append(avg_train_acc)
    print ('Epoch [{}/{}], loss: {loss:.4f} train_loss: {train_loss:.4f}, train_acc: {train_acc:.4f}' 
                   .format(epoch+1, nb_epoch, i+1, loss=avg_train_loss, train_loss=avg_train_loss, train_acc=avg_train_acc))
    #val
    net.eval()
    with torch.no_grad():
     for data, labels in test_loader:
      data = data.to(device)
      data = data.float()
      labels = labels.to(device)
      labels = labels.long()
      outputs = net(data)
      loss = criterion(outputs, labels)
      val_loss += loss.item()
      val_acc += (outputs.max(1)[1] == labels).sum().item()
    avg_val_loss = val_loss / len(test_loader.dataset)
    avg_val_acc = val_acc / len(test_loader.dataset)

    print ('Epoch [{}/{}], loss: {loss:.4f} val_loss: {val_loss:.4f}, val_acc: {val_acc:.4f}' 
                   .format(epoch+1, nb_epoch, i+1, loss=avg_train_loss, val_loss=avg_val_loss, val_acc=avg_val_acc))
    early_stopping(avg_val_loss, net)
    if early_stopping.early_stop:
            print("Early stopping")
            break
    val_loss_list.append(avg_val_loss)
    val_acc_list.append(avg_val_acc)

import matplotlib.pyplot as plt

plt.figure(figsize=(8,6))
plt.plot(train_loss_list,label='train', lw=3, c='b')
plt.plot(val_loss_list,label='test',lw=3,c = 'r')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('3DCNN')
plt.xticks(size=14)
plt.yticks(size=14)
plt.grid(lw=2)
plt.legend(fontsize=14)
plt.show()

plt.figure(figsize=(8,6))
plt.plot(train_acc_list,label='train', lw=3, c='b')
plt.plot(val_acc_list,label='test',lw=3,c = 'r')
plt.xlabel('Epoch')
plt.ylabel('accuracy')
plt.title('3DCNN')
plt.xticks(size=14)
plt.yticks(size=14)
plt.grid(lw=2)
plt.legend(fontsize=14)
plt.show()

