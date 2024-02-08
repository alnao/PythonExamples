#
# FACE DETECTOR from Video with OpenCV library
# see https://en.wikipedia.org/wiki/OpenCV
# see https://github.com/opencv/opencv
# 
# example from 
# see https://www.youtube.com/watch?v=i3sLv1sus0I
# see https://learnopencv.com/read-write-and-display-a-video-using-opencv-cpp-python/
# 
import cv2 # pip install opencv-python ( "python3-opencv" in debian )
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

#haarcascade_frontalface_default.xml from
#https://github.com/kipr/opencv/blob/master/data/haarcascades/haarcascade_frontalface_default.xml
face_cassifier = cv2.CascadeClassifier('./haarcascade_frontalface_default.xml')

def detect_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cassifier.detectMultiScale(gray, 1.3, 5)
    except Exception as e:
        print ("Errore downloading")
        print (e)
        return img
    if faces == ():
        return img
    for (x,y,w,h) in faces:
        cv2.rectangle( img , (x,y) , (x+w,y+h) , (255,0,0) , 2)
    return img
cap=cv2.VideoCapture('./Download.mp4')
#while True:
while(cap.isOpened()):
    ret,frame = cap.read()
    frame = detect_faces(frame)
    cv2.imshow ('Video face detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    if cv2.waitKey(25) & 0xFF == ord('q'):
      break
    
# When everything done, release the video capture object
cap.release()
# Closes all the frames
cv2.destroyAllWindows()