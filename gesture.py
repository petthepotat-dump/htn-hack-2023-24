import cv2
from mc_controller import minecraft_controller
from websurfing_controller import websurfing_controller
import keyboard

active_mode = 'minecraft'  # default to web mode

def toggle_mode(e):
    global active_mode
    if active_mode == 'web':
        print("Switching to Minecraft Mode")
        active_mode = 'minecraft'
    else:
        print("Switching to Web Surfing Mode")
        active_mode = 'web'

keyboard.on_press_key("f4", toggle_mode)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    if active_mode == 'minecraft':
        minecraft_controller(frame, active_mode)
    elif active_mode == 'web':
        websurfing_controller(frame, active_mode)

    # Display the frame (you can add conditions to display based on the mode)
    cv2.imshow("Controller", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
