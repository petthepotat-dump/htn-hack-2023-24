import cv2
from roboflow import Roboflow
import time
import adhawkapi
import adhawkapi.frontend
import numpy as np
import cv2

# Initialize Roboflow
rf = Roboflow(api_key="x")
project = rf.workspace().project("screen-detector-v")
model = project.version(1).model

frame = None  # Declare global frame to be accessed in multiple functions
xvec, yvec = 0.0, 0.0  # Initialize gaze vector components to some default values

COUNTER = 0

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
        global COUNTER, xvec, yvec  # Declare these as global
        COUNTER += 1
        if COUNTER % 10 != 0: return
        if et_data.gaze is not None:
            xvec, yvec, zvec, vergence = et_data.gaze
            # print(f'Gaze={xvec:.2f},y={yvec:.2f},z={zvec:.2f},vergence={vergence:.2f}')


    @staticmethod
    def _handle_events(event_type, timestamp, *args):
        if event_type == adhawkapi.Events.BLINK:
            duration = args[0]
            print(f'Got blink: {timestamp} {duration}')

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


NAN = float('nan')
def clamp(_min, _max, val):
    global NAN
    if val < _min:
        return _min
    if val > _max:
        return _max
    return 0 if val == NAN else val



HSV_RANGE = [(110, 0, 0), (130, 100, 100)]
C_LIMIT = 300


def main():
    ''' App entrypoint '''
    global xvec, yvec  # Declare these as global
    frontend = FrontendData()
    # create an opencv camera instance
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # Predict on the current frame
        predictions = model.predict_from_image(frame, confidence=40, overlap=30)

        # Draw bounding boxes on the frame based on predictions
        for prediction in predictions:
            label = prediction['label']
            confidence = prediction['confidence']
            x, y, w, h = prediction['xmin'], prediction['ymin'], prediction['width'], prediction['height']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"{label}: {confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Show the frame with bounding boxes
        cv2.imshow('Object Detection', frame)

        # Check for user input to exit the loop
        key = cv2.waitKey(1)
        if key == ord('q'):
            break

    # Release the video capture object and close the OpenCV window
    cap.release()
    cv2.destroyAllWindows()

    # Release the video capture object and close the OpenCV window
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()