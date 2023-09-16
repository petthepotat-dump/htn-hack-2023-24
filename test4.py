import cv2
import numpy as np
import adhawkapi
import adhawkapi.frontend

class GazeTracker:
    def __init__(self):
        # Initialize the Adhawk frontend
        self.frontend = adhawkapi.frontend.FrontendApi(ble_device_name='ADHAWK MINDLINK-296')
        self.frontend.register_stream_handler(adhawkapi.PacketType.EYETRACKING_STREAM, self.handle_et_data)
        self.frontend.start(tracker_connect_cb=self.handle_tracker_connect)

        # Define a transformation matrix (you need to populate this with calibration data)
        self.transformation_matrix = np.identity(3)

    def handle_et_data(self, et_data: adhawkapi.EyeTrackingStreamData):
        if et_data.gaze is not None:
            xvec, yvec, zvec, vergence = et_data.gaze

            # Apply the transformation matrix to map gaze to camera view
            gaze_camera_coords = np.dot(self.transformation_matrix, np.array([xvec, yvec, zvec]))

            # Draw a visual indicator (e.g., a red dot) at the gaze position on the camera frame
            gaze_x, gaze_y = int(gaze_camera_coords[0]), int(gaze_camera_coords[1])
            cv2.circle(self.frame, (gaze_x, gaze_y), 10, (0, 0, 255), -1)

    def handle_tracker_connect(self):
        print("Tracker connected")
        self.frontend.set_et_stream_rate(60, callback=lambda *args: None)
        self.frontend.set_et_stream_control([
            adhawkapi.EyeTrackingStreamTypes.GAZE,
        ], True, callback=lambda *args: None)

    # def calibrate(self):
    #     # Implement your calibration process here
    #     # This should involve having the user focus their gaze on specific points
    #     # and recording the corresponding gaze vectors and camera positions for each point.
    #     # Then, use this calibration data to compute the transformation matrix.

    def start_tracking(self):
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Cannot open camera")
            return

        try:
            while True:
                ret, self.frame = cap.read()

                # Handle gaze data in the _handle_et_data method

                cv2.imshow('frame', self.frame)

                if cv2.waitKey(1) == ord('q'):
                    break

        except (KeyboardInterrupt, SystemExit):
            self.frontend.shutdown()
            cap.release()
            cv2.destroyAllWindows()

if __name__ == '__main__':
    gaze_tracker = GazeTracker()
    gaze_tracker.calibrate()  # Perform calibration before starting tracking
    gaze_tracker.start_tracking()
