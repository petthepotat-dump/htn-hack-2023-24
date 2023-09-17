import time
import adhawkapi
import adhawkapi.frontend
import numpy as np
import cv2
import threading
import math
import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QBrush, QColor
import pyautogui
from screeninfo import get_monitors

# ... [Your SmallWindow class remains unchanged]
class SmallWindow(QWidget):
    def __init__(self, title, x, y, w = 40, h = 40):
        super().__init__()

        # Set window title and position
        self.setWindowTitle(title)
        self.setGeometry(x, y, w, h)  # x, y, width, height

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: rgba(255, 0, 255, 255);")

    def keyPressEvent(self, event):
        # check if escape key
        if event.key() == Qt.Key.Key_Escape:
            QApplication.instance().quit()  # Close the application


# Setting up Communication
def on_connect():
    print('Connected to AdHawk Backend Service')

def on_disconnect():
    print('Disconnected from AdHawk Backend Service')

api = adhawkapi.frontend.FrontendApi()
api.start(connect_cb=on_connect, disconnect_cb=on_disconnect)

# Auto-Tune
api.trigger_autotune()

# Calibration
def grid_points(nrows, ncols, xrange=20, yrange=12.5, xoffset=0, yoffset=2.5):
    '''Generates a grid of points based on range and number of rows/cols'''
    zpos = -0.6  # typically 60cm to screen
    xmin, xmax = np.tan(np.deg2rad([xoffset - xrange, xoffset + xrange])) * np.abs(zpos)
    ymin, ymax = np.tan(np.deg2rad([yoffset - yrange, yoffset + yrange])) * np.abs(zpos)

    cal_points = []
    for ypos in np.linspace(ymin, ymax, nrows):
        for xpos in np.linspace(xmin, xmax, ncols):
            cal_points.append((xpos, ypos, zpos))

    print(f'grid_points(): generated {nrows}x{ncols} points'
          f' {xrange}x{yrange} deg box at {zpos}: {cal_points}')

    return cal_points

npoints = 9
nrows = int(np.sqrt(npoints))
reference_points = grid_points(nrows, nrows)

api.start_calibration()
for point in reference_points:
    api.register_calibration_point(*point)
api.stop_calibration()

# Enable Data Streams
def gaze_handler(*data):
    timestamp, xpos, ypos, zpos, vergence = data

api.register_stream_handler(adhawkapi.PacketType.EXTENDED_GAZE, gaze_handler)
api.set_stream_control(adhawkapi.PacketType.EXTENDED_GAZE, 60)

# ... [Rest of your code remains unchanged]

def main():
    ''' App entrypoint '''
    global xvec, yvec  # Declare these as global
    frontend = FrontendData()
    # create an opencv camera instance
    cap = cv2.VideoCapture(0)

    # check if camera is opened
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    try:
        # run the opencv code
        while True:
            # read frame from camera
            ret, frame = cap.read()

            # check if frame is read correctly
            if not ret:
                print("Can't receive frame (stream end?). Exiting ...")
                break

            # Get dimensions
            h, w, c = frame.shape

            # For demonstration: create a point from gaze vector
            xc = (clamp(-3, 3, xvec) + 3) / 6 * w
            x_point = int(clamp(-10000, 10000, xc + (75 + xc/80)))
            y_point = h - int((clamp(-2, 2, yvec) + 2) / 4 * h)
            #if COUNTER % 10 == 0: print(h, w, x_point, y_point)

            # -- 
            # get hsv image
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            # filter out colours within a range
            mask = cv2.inRange(hsv, HSV_RANGE[0], HSV_RANGE[1])
            result = cv2.bitwise_and(frame, frame, mask=mask)
            # # convert result to black and white
            resultbw = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)


            coords = []
            # draw rectangles around each contour
            contours, hierarchy = cv2.findContours(resultbw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w*h > C_LIMIT:
                    coords.append((x, y))
                    cv2.rectangle(result, (x, y), (x+w, y+h), (0, 255, 0), 2)



            # sort coords by x, then by y
            coords = sorted(coords, key=lambda x: (x[0]))
            # draw coords to result (lines)
            if len(coords) >= 4:
                topleft = max(coords[:2], key=lambda x: x[1])
                botleft = min(coords[:2], key=lambda x: x[1])
                topright = max(coords[2:], key=lambda x: x[1])
                botright = min(coords[2:], key=lambda x: x[1])
                print(topleft, botleft, topright, botright, coords)

                # cv2.line(result, coords[0], coords[1], (0, 0, 255), 2) # top line
                # cv2.line(result, coords[2], coords[3], (0, 0, 255), 2) # bot line
                # cv2.line(result, coords[0], coords[2], (0, 0, 255), 2) # left line
                # cv2.line(result, coords[1], coords[3], (0, 0, 255), 2) # right line
                cv2.line(frame, topleft, botleft, (0, 0, 255), 2)
                cv2.line(frame, topright, botright, (0, 0, 255), 2)
                cv2.line(frame, topleft, topright, (0, 0, 255), 2)
                cv2.line(frame, botleft, botright, (0, 0, 255), 2)
                #---------
            
                # krish stuff -- keep commented for now
                # cv2.line(frame, topleft, botleft, (0, 0, 255), 2)
                # cv2.line(frame, topright, botright, (0, 0, 255), 2)
                # cv2.line(frame, topleft, topright, (0, 0, 255), 2)
                # cv2.line(frame, botleft, botright, (0, 0, 255), 2)
                # cv2.line(frame, botleft, topright, (0, 255, 0), 2)

                cv2.circle(frame, (x_point, y_point), 5, (255, 255, 255), -1)

                # diagonal line
                cv2.line(result, botleft, topright, (0, 255, 0), 2)
                d_length = np.sqrt((botleft[0] - topright[0])**2 + (botleft[1] - topright[1])**2) # pixels
                scale_factor = COMPUTER_CSECTION / d_length # meters/pixels

                src_points = [topleft, botleft, topright, botright]
                dst_points = [(0, 0), (0, wmain.height), (wmain.width, 0), (wmain.width, wmain.height)]

                transformed_gaze_point = transform_gaze_to_screen_space((x_point, y_point), src_points, dst_points)
            
                # Draw a circle on the gaze point
                cv2.circle(frame, transformed_gaze_point, 5, (255, 255, 255), -1)

                # print(scale_factor)
            else:
                # you are outside of the screen //  not focused ons creen
                print("you are not focused on the window")

            # show frame
            # cv2.imshow('hsv', hsv)
            # cv2.imshow('mask', mask)
            # cv2.imshow('result', result)

            # cv2.imshow('result', result)
            cv2.imshow('frame', frame)

            # wait for key press
            if cv2.waitKey(1) == ord('q'):
                break

    except (KeyboardInterrupt, SystemExit) as e:
        frontend.shutdown()
        cap.release()
        cv2.destroyAllWindows()
    except Exception as e:
        print(e)

if __name__ == '__main__':
    wmain = get_monitors()[0]
    app = QApplication(sys.argv)
    
    # Create 4 small windows with different titles and positions
    window1 = SmallWindow("Window 1", 0, 0)
    window2 = SmallWindow("Window 2", 0, wmain.height-40)
    window3 = SmallWindow("Window 3", wmain.width - 40, 0)
    window4 = SmallWindow("Window 4", wmain.width - 40, wmain.height - 40)

    

    # Show all the windows
    window1.show()
    window2.show()
    window3.show()
    window4.show()
    main()