import cv2
import mediapipe as mp
import pyautogui

def is_closed_fist(hand_landmarks):
    # Assume the landmarks have attributes x, y
    tip_x = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x
    pip_x = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].x
    
    # Add more conditions
    if tip_x < pip_x:
        return True
    return False

def scroll_up():
    pyautogui.scroll(1)

def scroll_down():
    pyautogui.scroll(-1)

def minecraft_left_click():
    pyautogui.mouseDown(button='left')

def minecraft_left_release():
    pyautogui.mouseUp(button='left')

def minecraft_right_click():
    pyautogui.mouseDown(button='right')

def minecraft_right_release():
    pyautogui.mouseUp(button='right')

def is_two_finger_scroll(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    
    # Check if index and middle finger are extended and others are folded
    # You might also want to check y-coordinates to decide scroll direction
    # Here we just return True for demonstration
    
    return True
def is_zoom_gesture(hand_landmarks):
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    
    distance = calculate_distance(thumb_tip, index_finger_tip)
    
    # You can decide on a threshold distance for zoom action here
    return True if distance > SOME_THRESHOLD else False

def is_thumb_up(hand_landmarks):
    # Similar to is_closed_fist, but for thumb up gesture
    return True if CONDITION else False
def is_rock_sign(hand_landmarks):
    # Logic to detect rock sign based on landmark positions
    return True if CONDITION else False
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

cap = cv2.VideoCapture(0)
hands = mp_hands.Hands()

hand_state = "open"

while True:
    ret, frame = cap.read()
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            if is_closed_fist(hand_landmarks):
                if hand_state != "closed":
                    print("Closed Fist")
                    hand_state = "closed"
                    
            elif is_two_finger_scroll(hand_landmarks):
                if hand_state != "scroll":
                    print("Two Finger Scroll")
                    hand_state = "scroll"
                    
            elif is_zoom_gesture(hand_landmarks):
                if hand_state != "zoom":
                    print("Zoom Gesture")
                    hand_state = "zoom"
                    
            elif is_thumb_up(hand_landmarks):
                if hand_state != "thumb_up":
                    print("Thumb Up")
                    hand_state = "thumb_up"
                    
            elif is_rock_sign(hand_landmarks):
                if hand_state != "rock":
                    print("Rock Sign")
                    hand_state = "rock"
                    
            else:
                if hand_state != "open":
                    print("Open Fist")
                    hand_state = "open"

            
    cv2.imshow('Hand Tracking', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
