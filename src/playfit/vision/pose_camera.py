import threading

import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


class PoseCamera:
    """Reads the webcam and runs pose estimation on a background thread,
    so a slow camera or model never stalls the game loop."""

    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index) #capturing video from the default camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640) #setting width of the frame
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) #setting height of the frame
        self.cap.set(cv2.CAP_PROP_FPS, 30) #setting frames per second

        self.lock = threading.Lock()
        self.latest = None #(image, landmarks) not yet handed to the game
        self.running = True
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def worker(self):
        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5, model_complexity=0) as pose:
            while self.running:
                ret, frame = self.cap.read() #reading the frame from the webcam
                if not ret: #no webcam, or it stopped delivering frames
                    break

                frame = cv2.flip(frame, 1) #flipping the frame horizontally for a mirror effect
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) #converting the frame from BGR to RGB
                image.flags.writeable = False #setting the image to non-writeable to improve performance
                results = pose.process(image)

                landmarks = None
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    mp_drawing.draw_landmarks(frame,
                                              results.pose_landmarks,
                                              mp_pose.POSE_CONNECTIONS,
                                              mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                                              mp_drawing.DrawingSpec(color=(0,0,255), thickness=2, circle_radius=2))

                with self.lock:
                    self.latest = (frame, landmarks)
        self.cap.release()

    def poll(self):
        """Returns (image, landmarks) for a frame the game has not seen yet, else None."""
        with self.lock:
            latest, self.latest = self.latest, None
        return latest

    def close(self):
        self.running = False
        self.thread.join(timeout=2)
