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



# get monitor res
from screeninfo import get_monitors


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



# --------------------------------------------------



frame = None  # Declare global frame to be accessed in multiple functions
xvec, yvec, zvec, wvec = 0.0, 0.0, 0.0, 0.0 # Initialize gaze vector components to some default values



# convert 15 inch to meters
CSECTION = 13
# 1 inch = 0.0254 meters
COMPUTER_CSECTION = 0.0254 * CSECTION

# --------------------------------------------------

COUNTER = 0
i_IMU = None
c_IMU = None
CACHE_COORDS = [(0,0), (0,0), (0,0), (0,0)]


class FrontendData:
    def __init__(self):
        global xvec, yvec  # Declare these as global
        self._api = adhawkapi.frontend.FrontendApi(ble_device_name='ADHAWK MINDLINK-296')
        self._api.register_stream_handler(adhawkapi.PacketType.EYETRACKING_STREAM, self._handle_et_data)
        self._api.register_stream_handler(adhawkapi.PacketType.EVENTS, self._handle_events)
        self._api.start(tracker_connect_cb=self._handle_tracker_connect,
                        tracker_disconnect_cb=self._handle_tracker_disconnect)

    def shutdown(self):
        self._api.shutdown()

    @staticmethod
    def _handle_et_data(et_data: adhawkapi.EyeTrackingStreamData):
        # Declare these as global
        global COUNTER, xvec, yvec, zvec, wvec, i_IMU
        COUNTER += 1
        if COUNTER % 10 != 0: return
        if et_data.gaze is not None:
            xvec, yvec, zvec, wvec= et_data.gaze
            print(f'Gaze={xvec:.2f},y={yvec:.2f},z={zvec:.2f},vergence={wvec:.2f}')
        if et_data.imu_quaternion is not None:
            if et_data.eye_mask == adhawkapi.EyeMask.BINOCULAR:
                x, y, z, w = et_data.imu_quaternion
                if not i_IMU:
                    i_IMU = (x, y, z, w)
                c_IMU = (i_IMU[0] - x, i_IMU[1] - y, i_IMU[2] - z, i_IMU[3] - w)
                # print(f'IMU: x={x:.2f},y={y:.2f},z={z:.2f},w={w:.2f}')
                print(f"IMU: {c_IMU[0]:.2f},{c_IMU[1]:.2f},{c_IMU[2]:.2f},{c_IMU[3]:.2f}")
        print('-' * 30)


    @staticmethod
    def _handle_events(event_type, timestamp, *args):
        if event_type == adhawkapi.Events.BLINK:
            duration = args[0]
            #print(f'Got blink: {timestamp} {duration}')

    def _handle_tracker_connect(self):
        print("Tracker connected")
        self._api.set_et_stream_rate(60, callback=lambda *args: None)
        self._api.set_et_stream_control([
            adhawkapi.EyeTrackingStreamTypes.GAZE,
            adhawkapi.EyeTrackingStreamTypes.EYE_CENTER,
            adhawkapi.EyeTrackingStreamTypes.PUPIL_DIAMETER,
            adhawkapi.EyeTrackingStreamTypes.IMU_QUATERNION,
        ], True, callback=lambda *args: None)
        self._api.set_event_control(adhawkapi.EventControlBit.BLINK, 1, callback=lambda *args: None)
        self._api.set_event_control(adhawkapi.EventControlBit.EYE_CLOSE_OPEN, 1, callback=lambda *args: None)

    def _handle_tracker_disconnect(self):
        print("Tracker disconnected")


def clamp(_min, _max, val):
    if val < _min:
        return _min
    if val > _max:
        return _max
    if math.isnan(val):
        return 0
    else:
        return val


# HSV_RANGE = [np.array((60, 0, 0)), np.array((85, 100, 100))] # green
HSV_RANGE = [np.array((135, 100, 200)), np.array((155, 160, 255))] # magenta
C_LIMIT = 10


def main():
    ''' App entrypoint '''
    global xvec, yvec, zvec, wvec, CACHE_COORDS # Declare these as global
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

            #TODO: remoeve / fix this cringe
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
            if len(coords) >= 4 and COUNTER%3==0:
                CACHE_COORDS[0] = max(coords[:2], key=lambda x: x[1]) #topleft
                CACHE_COORDS[1] = min(coords[:2], key=lambda x: x[1]) #botleft
                CACHE_COORDS[2] = max(coords[2:], key=lambda x: x[1]) #topright
                CACHE_COORDS[3] = min(coords[2:], key=lambda x: x[1]) #botright

                print(CACHE_COORDS)

                #---------
            
                # krish stuff -- keep commented for now
                # cv2.line(frame, topleft, botleft, (0, 0, 255), 2)
                # cv2.line(frame, topright, botright, (0, 0, 255), 2)
                # cv2.line(frame, topleft, topright, (0, 0, 255), 2)
                # cv2.line(frame, botleft, botright, (0, 0, 255), 2)
                # cv2.line(frame, botleft, topright, (0, 255, 0), 2)

                cv2.circle(frame, (x_point, y_point), 5, (255, 255, 255), -1)

                # diagonal line
                cv2.line(result, CACHE_COORDS[1], CACHE_COORDS[2], (0, 255, 0), 2)
                d_length = np.sqrt((CACHE_COORDS[1][0] - CACHE_COORDS[2][0])**2 + (CACHE_COORDS[1][1] - CACHE_COORDS[2][1])**2) # pixels
                
                # calculate focal length - m/pix
                focal = COMPUTER_CSECTION / d_length
                # homographic mapping (3d point -> 2d)
                ngaze = np.linalg.norm(np.array([xvec, yvec, zvec]))
                # find the 'center' of the image (average center lol)
                ccd = (CACHE_COORDS[0][0] + CACHE_COORDS[3][0]) / 2, (CACHE_COORDS[0][1] + CACHE_COORDS[3][1]) / 2 # center of computer display
                
                # convert quat -> axis angle -> rodrigues angle -> 3x3 rot matrix -> 4x4 rot matrix
                # rmat = np.ndarray([
                #     [1 - 2 * yvec*yvec - 2 * zvec*zvec, 2 * xvec *yvec-2*zvec*wvec, 2*xvec*zvec+2*yvec*wvec],
                #     [2*xvec*yvec+2*zvec*wvec, 1-2*xvec*xvec-2*zvec*zvec, 2*yvec*zvec-2*xvec*wvec],
                #     [2*xvec*zvec-2*yvec*wvec, 2*yvec*zvec+2*xvec*wvec, 1-2*xvec*xvec-2*yvec*yvec]
                # ])
                mat1 = np.array([
                    [wvec, zvec, -yvec, xvec],
                    [-zvec, wvec, xvec, yvec],
                    [yvec, -xvec, wvec, zvec],
                    [-xvec, -yvec, -zvec, wvec]
                ])
                mat2 = np.array([
                    [wvec, zvec, -yvec, -xvec],
                    [-zvec, wvec, xvec, -yvec],
                    [yvec, -xvec, wvec, -zvec],
                    [xvec, yvec, zvec, wvec]
                ])
                rmat = np.matmul(mat1, mat2)
                # print(rmat)

                # now we do some math


                # print(scale_factor)
            else:
                # you are outside of the screen //  not focused ons creen
                print("you are not focused on the window")
                pass

            # draw the rectnagle
            # cv2.line(result, coords[0], coords[1], (0, 0, 255), 2) # top line
            # cv2.line(result, coords[2], coords[3], (0, 0, 255), 2) # bot line
            # cv2.line(result, coords[0], coords[2], (0, 0, 255), 2) # left line
            # cv2.line(result, coords[1], coords[3], (0, 0, 255), 2) # right line
            cv2.line(frame, CACHE_COORDS[0], CACHE_COORDS[1], (0, 0, 255), 2)
            cv2.line(frame, CACHE_COORDS[2], CACHE_COORDS[3], (0, 0, 255), 2)
            cv2.line(frame, CACHE_COORDS[0], CACHE_COORDS[2], (0, 0, 255), 2)
            cv2.line(frame, CACHE_COORDS[1], CACHE_COORDS[3], (0, 0, 255), 2)
            

            # show frame
            # cv2.imshow('frame', frame)
            # cv2.imshow('hsv', hsv)
            # cv2.imshow('mask', mask)

            # Draw a circle on the gaze point
            cv2.circle(frame, (x_point, y_point), 5, (255, 255, 255), -1)
            # cv2.imshow('result', result)
            cv2.imshow('frame', frame)

            # wait for key press
            if cv2.waitKey(1) == ord('q'):
                break

    except (KeyboardInterrupt, SystemExit) as e:
        print(e)
        frontend.shutdown()
        cap.release()
        cv2.destroyAllWindows()
    except Exception as e:
        print(e)
        frontend.shutdown()
        cap.release()
        cv2.destroyAllWindows()

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