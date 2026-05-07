import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

_face_mesh = None
_face_cascade = None
_last_mesh_results = None
_mesh_frame_count = 0

CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

KEY_LANDMARKS = [133, 362, 1, 61, 291, 10]


def _get_face_mesh():
    global _face_mesh
    if _face_mesh is None:
        _face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=3,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
    return _face_mesh


def _get_cascade():
    global _face_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    return _face_cascade


def detect_and_annotate(frame, emotion_text="", deepface_info=None):
    global _last_mesh_results, _mesh_frame_count
    _mesh_frame_count += 1

    annotated = frame.copy()
    h, w = frame.shape[:2]

    coords = []

    if _mesh_frame_count % 3 == 0:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        face_mesh = _get_face_mesh()
        results = face_mesh.process(rgb)
        rgb.flags.writeable = True
        _last_mesh_results = results
    else:
        results = _last_mesh_results

    if results is not None and results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            mp_drawing.draw_landmarks(
                image=annotated,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing.DrawingSpec(
                    color=(0, 255, 255), thickness=1
                ),
            )

            for idx in KEY_LANDMARKS:
                lm = face_landmarks.landmark[idx]
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(annotated, (cx, cy), 5, (0, 255, 255), -1)

            x_min = w
            y_min = h
            x_max = 0
            y_max = 0
            for lm in face_landmarks.landmark:
                px, py = int(lm.x * w), int(lm.y * h)
                if px < x_min:
                    x_min = px
                if px > x_max:
                    x_max = px
                if py < y_min:
                    y_min = py
                if py > y_max:
                    y_max = py

            x_min = max(x_min - 10, 0)
            y_min = max(y_min - 15, 0)
            x_max = min(x_max + 10, w)
            y_max = min(y_max + 10, h)

            coords.append((x_min, y_min, x_max - x_min, y_max - y_min))

            cv2.rectangle(annotated, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

            label = ""
            if deepface_info and deepface_info.get("emotion"):
                emotion = deepface_info["emotion"]
                conf = deepface_info.get("confidence", 0)
                if conf:
                    label = f"{emotion} ({conf:.0%})"
                else:
                    label = emotion
            elif emotion_text:
                label = str(emotion_text)

            if label:
                (tw, th), tb = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(annotated,
                              (x_min, y_min - 5 - th - tb - 4),
                              (x_min + tw + 6, y_min - 5 + tb + 2),
                              (0, 0, 0), -1)
                cv2.putText(
                    annotated, label, (x_min + 3, y_min - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
                )
    else:
        cascade = _get_cascade()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        for (x, y, w_box, h_box) in faces:
            coords.append((int(x), int(y), int(w_box), int(h_box)))
            cv2.rectangle(annotated, (x, y), (x + w_box, y + h_box), (0, 255, 0), 2)
            label = ""
            if deepface_info and deepface_info.get("emotion"):
                emotion = deepface_info["emotion"]
                conf = deepface_info.get("confidence", 0)
                if conf:
                    label = f"{emotion} ({conf:.0%})"
                else:
                    label = emotion
            elif emotion_text:
                label = str(emotion_text)
            if label:
                (tw, th), tb = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(annotated,
                              (x, y - 10 - th - tb - 4),
                              (x + tw + 6, y - 10 + tb + 2),
                              (0, 0, 0), -1)
                cv2.putText(
                    annotated, label, (x + 3, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
                )

    return annotated, coords
