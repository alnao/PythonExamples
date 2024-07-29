# how merge 2 video file with ffmpeg in python
#see https://stackoverflow.com/questions/61758480/merge-two-videos-with-python3

import sys
import threading
import os
import ffmpeg
#pip uninstall ffmpeg  --break-system-packages
#pip uninstall ffmpeg-python --break-system-packages
#pip uninstall python-ffmpeg --break-system-packages
#pip install ffmpeg-python --break-system-packages


from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox


class Converter(QtCore.QObject):
    started = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    def concatenate(self, qt_window,inputs, output):
        #for input in inputs:
        #    if len(input)>4:
        #        if input[:-4]==".mkv":
        #            input=self.convert_to_mp4(input)
        threading.Thread(
            target=self._concatenate, args=(qt_window,inputs, output), daemon=True
        ).start()

    def _concatenate(self, qt_window,inputs, output):
        self.started.emit()
        ffmpeg.concat(*[ffmpeg.input(i) for i in inputs]).output(output).run()
        self.finished.emit()
        #dialog to success
        dlg = QMessageBox(qt_window)
        dlg.setWindowTitle("END!")
        dlg.setText("Merge done!")
        button = dlg.exec()
        if button == QMessageBox.Ok:
            qt_window.exit()
            exit()


    #see https://stackoverflow.com/questions/64519818/converting-mkv-files-to-mp4-with-ffmpeg-python
    def convert_to_mp4(mkv_file):#converting-mkv-files-to-mp4
        no_extension = str(os.path.splitext(mkv_file))
        with_mp4 = no_extension + ".mp4"
        ffmpeg.input(mkv_file).output(with_mp4).run()
        #print("Finished converting {}".format(no_extension))
        return with_mp4


class Widget(QtWidgets.QWidget):
    def __init__(self, app, parent=None):
        self.app=app
        super().__init__(parent)

        self.input_1_le = QtWidgets.QLineEdit()
        self.input_1_le.setFixedWidth(400)
        self.input_2_le = QtWidgets.QLineEdit()
        self.input_2_le.setFixedWidth(400)
        self.output_le = QtWidgets.QLineEdit()
        self.output_le.setFixedWidth(400)

        self.load_1_btn = QtWidgets.QPushButton("Select 1 input")
        self.load_2_btn = QtWidgets.QPushButton("Select 2 input")
        self.load_3_btn = QtWidgets.QPushButton("Select output")

        self.start_btn = QtWidgets.QPushButton("Start")

        lay = QtWidgets.QGridLayout(self)

        lay.addWidget(QtWidgets.QLabel("Input 1"), 0, 0)
        lay.addWidget(self.input_1_le, 0, 1)
        lay.addWidget(self.load_1_btn, 0, 2)

        lay.addWidget(QtWidgets.QLabel("Input 2"), 1, 0)
        lay.addWidget(self.input_2_le, 1, 1)
        lay.addWidget(self.load_2_btn, 1, 2)

        lay.addWidget(QtWidgets.QLabel("Output"), 2, 0)
        lay.addWidget(self.output_le, 2, 1)
        lay.addWidget(self.load_3_btn, 2, 2)

        lay.addWidget(self.start_btn, 3, 0, 1, 3)

        self.converter = Converter()

        self.load_1_btn.clicked.connect(self.load_input_1)
        self.load_2_btn.clicked.connect(self.load_input_2)
        self.load_3_btn.clicked.connect(self.load_output)

        self.start_btn.clicked.connect(self.start)
        self.converter.started.connect(lambda: self.start_btn.setEnabled(False))
        self.converter.finished.connect(lambda: self.start_btn.setEnabled(True))

    @QtCore.pyqtSlot()
    def load_input_1(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("Select Video"),
            QtCore.QDir.homePath(),
            #self.tr("Video Files (*.mp4)"),
        )
        if filename:
            self.input_1_le.setText(filename)

    @QtCore.pyqtSlot()
    def load_input_2(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("Select Video"),
            QtCore.QDir.homePath(),
            #self.tr("Video Files (*.mp4)"),
        )
        if filename:
            self.input_2_le.setText(filename)

    @QtCore.pyqtSlot()
    def load_output(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr("Select Video"),
            QtCore.QDir.homePath(),
            self.tr("Video Files (*.mp4)"),
        )
        if filename:
            self.output_le.setText(filename)

    @QtCore.pyqtSlot()
    def start(self):
        if len(self.output_le.text())>4:
            if self.output_le.text()[-4:]==".mp4":
                self.converter.concatenate(self,
                    [self.input_1_le.text(), self.input_2_le.text()], self.output_le.text()
                )
                return 
        dlg = QMessageBox(self)
        dlg.setWindowTitle("ERROR!")
        dlg.setText("output file not mp4!")
        button = dlg.exec()

    def exit(self):
        sys.exit(self.app.exec_())


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = Widget(app)
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()



#see https://stackoverflow.com/questions/56973205/how-to-combine-the-video-and-audio-files-in-ffmpeg-python
#import ffmpeg
#input_video = ffmpeg.input('./test/test_video.webm')
#input_audio = ffmpeg.input('./test/test_audio.webm')
#ffmpeg.concat(input_video, input_audio, v=1, a=1).output('./processed_folder/finished_video.mp4').run()
