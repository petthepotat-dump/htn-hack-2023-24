import cv2
from roboflow import Roboflow

# Initialize Roboflow
rf = Roboflow(api_key="x")
project = rf.workspace().project("screen-detector-v")
model = project.version(1).model

def main():
    # Open the camera
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

if __name__ == '__main__':
    main()
