import cv2
import numpy as np
import os
from PIL import Image

store_folder = "/Users/goki.minegishi/Desktop/first_miniproject/fusion/HMDB_fusion2/clap"
path2cat = "/Users/goki.minegishi/Desktop/first_miniproject/fusion/HMDB_CNNdata/clap"

imgs = []

listofts = os.listdir(path2cat)

if '.DS_Store' in listofts:
        listofts.remove('.DS_Store')
print(len(listofts))
for i,ts in enumerate(listofts):
        
    path2ts = os.path.join(path2cat,ts)
    listofimgs = os.listdir(path2ts)
    if '.DS_Store' in listofimgs:
        listofimgs.remove('.DS_Store')

    for m in listofimgs:
        path2img = os.path.join(path2ts,m)
        img = cv2.imread(path2img)
        im_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        im_gray = cv2.resize(im_gray,(224,224))
        imgs.append(im_gray)
        
    if len(imgs) == 16:

        print(len(imgs))
        im = cv2.merge(imgs)
        
        np.save(store_folder + '/test' + str(i),im)
        imgs = []
    else:
        print(len(imgs))
        imgs = []
        
        


        
            
