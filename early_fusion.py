# -*- coding: utf-8 -*-
"""early_fusion.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1odGnPxolw223nrdX8Ugq_KM-8j3l-SYQ
"""

from google.colab import drive
drive.mount('/content/drive')

import os
import glob
from torch.utils.data import Dataset
import pandas as pd
import os
import torch
import torchvision.transforms as transforms
from torchvision import models
import numpy as np
import torch.nn as nn
import torch.optim as optim
import torchvision
import torch.nn.functional as F
import torchvision.transforms.functional as TF
import random
import itertools

"""# Early fusion
videoを16imagesに変換したデータを16channelのnpyにし、そのnpyをCNNに入力するモデル。

# Data load とラベルの作成
(224,224,16)のnumpy配列
"""

original_dir = 'drive/MyDrive/data_for_early_fusion'
#train data
train_data_list = []
test_data_list = []
listofcats = os.listdir(original_dir + "/train")
target_train = []
for i,cat in enumerate(listofcats):
  path2cat = os.path.join(original_dir + '/train/' + str(cat))
  listofdatas = os.listdir(path2cat)
  print("{}:{}".format(cat,len(listofdatas)))
  for data in listofdatas:
    path2data = os.path.join(original_dir + '/' + 'train' + '/' + str(cat) + '/' + str(data))
    d = np.load(path2data)
    train_data_list.append(d)
  target_train.append([i]*len(listofdatas))

#test data
target_test = []
clistofcats = os.listdir(original_dir +'/'+ 'validation')
for j,cat in enumerate(listofcats):
  path2cat = os.path.join(original_dir + '/' + 'validation' + '/' + str(cat))
  listofdatas = os.listdir(path2cat)
  print("{}:{}".format(cat,len(listofdatas)))
  for data in listofdatas:
    path2data = os.path.join(original_dir + '/' + 'validation' + '/' + str(cat) + '/' + str(data))
    d = np.load(path2data)
    test_data_list.append(d)
  target_test.append([j]*len(listofdatas))

target_train2 = list(itertools.chain.from_iterable(target_train))
target_test2 = list(itertools.chain.from_iterable(target_test))

"""# データ数

|     |  brush_hair  |  clap  |  smoke  |  run  |
|---  |:----:     | :----:   | :--------:|:-------:|
|train|  160         |  196   |   174      |  348     |
|test |  41          |  49    |     44    |    87   |

# tesorに変換
"""

X_train = torch.stack([TF.to_tensor(i) for i in train_data_list])
print("train_data:",X_train.shape)
Y_train = torch.stack([torch.from_numpy(np.array(i)) for i in target_train2])
print("train_target:",Y_train.shape)
X_test  = torch.stack([TF.to_tensor(i) for i in test_data_list])
print("test_size:",X_test.shape)
Y_test = torch.tensor([torch.from_numpy(np.array(i)) for i in target_test2])
print("test_size:",Y_test.shape)

"""# torchにload

"""

train_dataset = torch.utils.data.TensorDataset(X_train, Y_train)
train_loader = torch.utils.data.DataLoader(train_dataset,batch_size=32,shuffle=True,num_workers=2)
test_dataset = torch.utils.data.TensorDataset(X_test, Y_test)
test_loader = torch.utils.data.DataLoader(test_dataset,batch_size=32,shuffle=True,num_workers=2)

"""# Model
CNNはresnetを使用する。  

inputを16channelにし、outputを4クラスにする。
Early fusion は prtrained = Falseにする。

"""

device = torch.device('cuda')
net = models.resnet18(pretrained=True).to(device)
net.conv1 = nn.Conv2d(16, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False) 
net.fc =  nn.Linear(in_features=512, out_features=4, bias=True)
net.cuda()

"""# parameter
lossはCrossEntropyを使用し、optimizerはSGDまたはAdamを使用。


"""

criterion = nn.CrossEntropyLoss()
#optimizer = optim.SGD(net.parameters(), lr=0.001, momentum=0.9)
optimizer = optim.Adam(net.parameters(), lr=0.0001, betas=(0.9, 0.999), eps=1e-08, weight_decay=0.0001)

"""# 学習
100Epoch学習している中でtest datasetのlossが30回連続下がらなかったら、学習を停止しlossが最小値のmodelを保存するEarly stoppingを使う。
"""

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

# lossとaccuracyを格納
train_loss_list = []
train_acc_list = []
val_loss_list = []
val_acc_list = []

nb_epoch = 100
early_stopping = EarlyStopping(patience=30, verbose=True,path='drive/MyDrive/model/early_fusion.pth')
for epoch in range(nb_epoch):
    train_loss = 0
    train_acc = 0
    val_loss = 0
    val_acc = 0

    #train
    net.train()
    for i, (data, labels) in enumerate(train_loader):
      
      data, labels = data.to(device), labels.to(device)

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
    print('Epoch [{}/{}], train_loss: {train_loss:.4f}, train_acc: {train_acc:.4f}' 
                   .format(epoch+1, nb_epoch, i+1,  train_loss=avg_train_loss, train_acc=avg_train_acc))
    #test
    net.eval()
    with torch.no_grad():
     for data, labels in test_loader:
      data = data.to(device)
      labels = labels.to(device)
      outputs = net(data)
      loss = criterion(outputs, labels)
      val_loss += loss.item()
      val_acc += (outputs.max(1)[1] == labels).sum().item()
    avg_val_loss = val_loss / len(test_loader.dataset)
    avg_val_acc = val_acc / len(test_loader.dataset)

    print('Epoch [{}/{}], val_loss: {val_loss:.4f}, val_acc: {val_acc:.4f}' 
                   .format(epoch+1, nb_epoch, i+1,  val_loss=avg_val_loss, val_acc=avg_val_acc))
    early_stopping(avg_val_loss, net)
    if early_stopping.early_stop:
            print("Early stopping")
            break
    val_loss_list.append(avg_val_loss)
    val_acc_list.append(avg_val_acc)

"""# lossを可視化"""

import matplotlib.pyplot as plt

plt.figure(figsize=(8,6))
plt.plot(train_loss_list,label='train', lw=3, c='b')
plt.plot(val_loss_list,label='test',lw=3,c = 'r')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('ResNet')
plt.xticks(size=14)
plt.yticks(size=14)
plt.grid(lw=2)
plt.legend(fontsize=14)
plt.show()

"""# accuracyを可視化"""

plt.figure(figsize=(8,6))
plt.plot(train_acc_list,label='train', lw=3, c='b')
plt.plot(val_acc_list,label='test',lw=3,c = 'r')
plt.xlabel('Epoch')
plt.ylabel('accuracy')
plt.title('ResNet')
plt.xticks(size=14)
plt.yticks(size=14)
plt.grid(lw=2)
plt.legend(fontsize=14)
plt.show()

