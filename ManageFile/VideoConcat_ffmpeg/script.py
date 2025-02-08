#!/usr/bin/env python3
# chmod +x script.py
# ./script

# SCRIPT TO CONCAT VIDEO with MPEG, source must be in MKV format, output will be in out.mp4 file

from tkinter import filedialog
from tkinter import *
import os
from os import listdir
from os.path import isfile, join

#import ffmpeg                           #   pip install ffmpeg  --break-system-packages
#see https://github.com/kkroening/ffmpeg-python

C_MP4=".mp4"
C_MKV=".mkv"
C_OGV=".ogv"

# SEE https://www.educative.io/answers/how-to-run-a-python-script-in-linux
# https://stackoverflow.com/questions/11295917/how-to-select-a-directory-and-store-the-location-using-tkinter-in-python


def selectExtension(fileName):
    if fileName.endswith(C_MP4) or fileName.endswith(C_MKV):
        return True
    else:
        return False

def selectFolder():
    root = Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    print("Folder, ",folder_selected)
    return folder_selected

def filesInFolder(folder):
    only_files = [f for f in listdir(folder) if isfile(join(folder, f)) and selectExtension(f)  ]
    return only_files

def concatVideo(folder,files):
    list_ts=[]
    #ffmpeg -i aaaaaaa.ogv -vcodec libx264 "B_Vivian_tetteMutande.mp4"
    for file in files:
        print("--------------------")
        print("Inizio a processare il video " , file)
        com="ffmpeg -i "+folder+"/"+ file + " -c copy -bsf:v h264_mp4toannexb -f mpegts " +folder+ "/fileIntermediate"+str(len(list_ts))+ ".ts"
        list_ts.append(folder+ "/fileIntermediate"+str(len(list_ts))+ ".ts")
        print(com)
        os.system(com)
    #cat fileIntermediate3.ts  fileIntermediate1.ts fileIntermediate2.ts > output.ts
        #list_ts_str=" ".join( list_ts )
        #com="cat " + list_ts_str + " > " +folder+"\output.ts"
        #print(com)
        #os.system(com)
    #ffmpeg -i "concat:fileIntermediate3.ts|fileIntermediate1.ts|fileIntermediate2.ts" -c copy -bsf:a aac_adtstoasc mergedVideo.mp4
    print("--------------------")
    print("FInito il ciclo, inizio ad unire i video")

    list_ts_str="|".join( list_ts )
    com="ffmpeg -i \"concat:"+list_ts_str+"\" -c copy -bsf:a aac_adtstoasc "+folder+"/out.mp4"
    print(com)
    os.system(com)
    for file in list_ts:
        os.remove(file)
    return folder+"/out.mp4"

def concertOgvToMkv(folder):
    files = [f for f in listdir(folder) if isfile(join(folder, f)) and f.endswith(C_OGV)  ]
    for file in files:
        #ffmpeg -i M_Vivian_Best_figa.ogv -i M_Vivian_Best_vestitoSpogliaTette.ogv -filter_complex "[0:v] [1:v] concat=n=3:v=1:a=0 [vv] " -map "[vv]" output.mkv
        com="ffmpeg -i "+folder +"/"+file+" -vcodec libx264 "+folder+ "/"+file.replace(C_OGV,C_MP4)
        print(com)
        os.system(com)

if __name__ == '__main__':
    folder=selectFolder()
    concertOgvToMkv(folder)
    files=filesInFolder(folder)
    out = concatVideo(folder,files)
    print ( out )
    print("DONE")
    