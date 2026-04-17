import datetime
import os
import time
import cv2
import pandas as pd
import csv
import numpy as np
import pyttsx3  # Text-to-Speech Library
import threading  # To prevent camera freezing while speaking
import json

# Hide TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# --- ID MAPPING ---
# Load the mapping from numeric label to original string ID
def load_id_mapping():
    """Load the ID mapping from numeric label to original string ID"""
    mapping_file = os.path.join("TrainingImageLabel", "id_mapping.json")
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading ID mapping: {e}")
    return {}

# Convert numeric label back to original string ID
def get_original_id(numeric_label):
    """Convert numeric label back to original string ID"""
    mapping = load_id_mapping()
    return mapping.get(str(numeric_label), str(numeric_label))

# --- SAFE MEDIAPIPE IMPORT ---
BLINK_DETECTION_ENABLED = False
face_mesh = None

try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
        
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )
    BLINK_DETECTION_ENABLED = True
    print("[INFO] MediaPipe loaded successfully. Blink Detection: ON")
except (ImportError, AttributeError, ModuleNotFoundError) as e:
    print(f"\n[WARNING] Blink Detection Disabled: {e}")
    BLINK_DETECTION_ENABLED = False
# -----------------------------

# --- VOICE ENGINE GLOBAL REFERENCE ---
# Global voice engine to ensure proper cleanup
_voice_engine = None
_voice_engine_lock = threading.Lock()

def speak(text):
    """Speak text using pyttsx3 in a separate thread"""
    def _run():
        global _voice_engine
        try:
            engine = pyttsx3.init()
            with _voice_engine_lock:
                _voice_engine = engine
            engine.setProperty('rate', 150)  # Speed of speech
            engine.say(text)
            engine.runAndWait()
            with _voice_engine_lock:
                _voice_engine = None
        except Exception as e:
            print(f"Voice error: {e}")
            with _voice_engine_lock:
                _voice_engine = None
    
    threading.Thread(target=_run, daemon=True).start()

def stop_voice():
    """Stop any ongoing voice output"""
    global _voice_engine
    with _voice_engine_lock:
        if _voice_engine is not None:
            try:
                _voice_engine.stop()
                _voice_engine = None
            except:
                pass

# --- FORMAT ID FOR SPEECH (Digit by Digit) ---
def format_id_for_speech(id_value):
    """Convert ID to digit-by-digit speech format"""
    id_str = str(id_value)
    return ' '.join(id_str)

def recognize_attendence():
    print("Loading LBPH face recognizer...")
    recognizer = cv2.face.LBPHFaceRecognizer_create()  
    model_path = os.path.join("TrainingImageLabel", "Trainner.yml")
    
    if not os.path.exists(model_path):
        print("Error: Trained model not found. Please Train Images first.")
        return

    # Load Haar Cascade (Matches capture_image.py)
    harcascadePath = "haarcascade_default.xml"
    if not os.path.exists(harcascadePath):
        print(f"Error: {harcascadePath} not found.")
        return
    faceCascade = cv2.CascadeClassifier(harcascadePath)

    print("Loading trained model...")
    recognizer.read(model_path)
    
    details_path = os.path.join("StudentDetails", "StudentDetails.csv")
    if not os.path.exists(details_path):
        print("Error: StudentDetails.csv missing.")
        return
    
    print("Loading student details...")
    df = pd.read_csv(details_path)
    df.columns = df.columns.str.strip() 
    # IMPORTANT: Ensure ID comparisons work even if CSV stores Id as number
    if 'Id' in df.columns:
        df['Id'] = df['Id'].astype(str).str.strip()
    
    if not os.path.exists("Attendance"):
        os.makedirs("Attendance")

    # Daily File Logic
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    fileName = f"Attendance/Attendance_{current_date}.csv"
    
    # Load Existing - Use string IDs to match our conversion
    recorded_ids = set()
    if os.path.isfile(fileName):
        try:
            with open(fileName, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if row and len(row) > 0:
                        recorded_ids.add(str(row[0]))  # Keep as string
        except: pass

    blink_status = {} 
    last_spoken_time = {} # To control voice frequency per student
    
    # Try multiple camera backends for better compatibility
    print("Initializing camera...")
    cam = None
    
    # Try different backends in order of preference
    backends = [
        (0, cv2.CAP_DSHOW),  # DirectShow (Windows)
        (0, cv2.CAP_MSMF),   # Microsoft Media Foundation (Windows)
        (0, cv2.CAP_ANY),     # Auto-detect
        (0, None)             # Default
    ]
    
    for device_id, backend in backends:
        if backend is None:
            cam = cv2.VideoCapture(device_id)
        else:
            cam = cv2.VideoCapture(device_id, backend)
        
        if cam.isOpened():
            print(f"Camera opened successfully with backend {backend}")
            break
        else:
            print(f"Failed to open camera with backend {backend}")
            cam = None
    
    if cam is None or not cam.isOpened():
        print("ERROR: Could not open camera. Please check:")
        print("  1. Camera is connected and working")
        print("  2. No other application is using the camera")
        print("  3. Camera drivers are installed correctly")
        return
    
    font = cv2.FONT_HERSHEY_SIMPLEX

    print(f"\n--- System Active: Using Daily File '{fileName}' ---")
    print("--- Press ENTER to close ---\n")

    while True:
        ret, im = cam.read()
        if not ret: break
        
        img_gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        img_gray = cv2.equalizeHist(img_gray)
        
        # Use Haar Cascade instead of MTCNN
        faces = faceCascade.detectMultiScale(img_gray, 1.2, 5)

        results = None
        if BLINK_DETECTION_ENABLED:
            rgb_im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_im)

        for (x, y, w, h) in faces:
            
            # --- Bigger Rectangle (Padding) ---
            padding_x = int(w * 0.2)
            padding_y = int(h * 0.2)
            x = max(0, x - padding_x)
            y = max(0, y - padding_y)
            w = w + (padding_x * 2)
            h = h + (padding_y * 2)

            face_roi = img_gray[y:y+h, x:x+w]
            if face_roi.size == 0: continue
            
            numeric_id, conf = recognizer.predict(face_roi)
            # Convert numeric label back to original string ID
            Id = get_original_id(numeric_id)
            match_percentage = max(0, 100 - conf)
            
            # Convert Id to string for comparison
            Id_str = str(Id)
            
            if conf < 85: 
                try:
                    name = df.loc[df['Id'] == Id_str]['Name'].values[0]
                except:
                    name = "Unknown"
                
                # Get student year and branch from CSV
                student_year = ""
                student_branch = ""
                try:
                    student_row = df.loc[df['Id'] == Id_str]
                    if 'Year' in df.columns:
                        student_year = str(student_row['Year'].values[0])
                    if 'Branch' in df.columns:
                        student_branch = str(student_row['Branch'].values[0])
                except:
                    pass
                
                status_txt = "Verifying..."
                color = (0, 165, 255) 

                current_time = time.time()
                should_speak = False
                message = ""

                # --- LOGIC FLOW ---
                if Id_str in recorded_ids:
                    status_txt = "Already Marked"
                    color = (0, 255, 0)
                    
                    # Only speak "Already marked" if we haven't spoken to this person in the last 5 seconds
                    if Id_str not in last_spoken_time or (current_time - last_spoken_time[Id_str] > 5):
                        # Format ID for digit-by-digit speech
                        formatted_id = format_id_for_speech(Id_str)
                        message = f"Already marked your attendance for ID {formatted_id}"
                        should_speak = True
                        last_spoken_time[Id_str] = current_time

                else:
                    # Not marked yet - Verify first
                    should_save = False
                    
                    if BLINK_DETECTION_ENABLED:
                        if results.multi_face_landmarks:
                            for face_landmarks in results.multi_face_landmarks:
                                top = face_landmarks.landmark[159].y
                                bottom = face_landmarks.landmark[145].y
                                if abs(top - bottom) < 0.007: 
                                    blink_status[Id_str] = True
                        
                        if blink_status.get(Id_str):
                            should_save = True
                            status_txt = "Verified (Blink)"
                            color = (0, 255, 0)
                        else:
                            status_txt = "Please Blink"
                            color = (0, 0, 255)
                    else:
                        if conf < 80:
                            should_save = True
                            status_txt = "Verified"
                            color = (0, 255, 0)

                    # Save and Speak - Only save if student is recognized (not Unknown)
                    if should_save and name != "Unknown" and Id_str != "0":
                        ts = time.time()
                        date_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                        time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                        
                        file_exists = os.path.isfile(fileName)
                        with open(fileName, 'a', newline='') as f:
                            writer = csv.writer(f)
                            if not file_exists:
                                # Include Year and Branch columns
                                writer.writerow(['Id', 'Name', 'Date', 'Time', 'Year', 'Branch'])
                            writer.writerow([Id_str, name, date_str, time_str, student_year, student_branch])
                        
                        recorded_ids.add(Id_str)
                        print(f"MARKED: {name} (ID: {Id_str}, Year: {student_year}, Branch: {student_branch})")
                    elif should_save:
                        # Face recognized but not in database - don't save
                        print(f"SKIPPED: Unknown face detected (ID: {Id_str}) - not saved to attendance")
                        status_txt = "Unknown - Not Saved"
                        color = (0, 0, 255)
                        
                        # Format ID for digit-by-digit speech
                        formatted_id = format_id_for_speech(Id_str)
                        message = f"Your attendance with ID {formatted_id} is marked successfully"
                        should_speak = True
                        last_spoken_time[Id_str] = current_time

                # Trigger Voice (Threaded)
                if should_speak:
                    speak(message)

                # Draw UI
                cv2.rectangle(im, (x, y), (x+w, y+h), color, 2)
                label_info = f"ID:{Id} | {name} | {int(match_percentage)}%"
                cv2.putText(im, label_info, (x, y-10), font, 0.6, color, 2)
                cv2.putText(im, status_txt, (x, y+h+25), font, 0.7, color, 2)
            else:
                cv2.rectangle(im, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(im, "Unknown", (x, y-10), font, 0.8, (0, 0, 255), 2)

        cv2.imshow('Attendance System', im)
        if cv2.waitKey(1) & 0xFF == 13: 
            break

    # Stop voice engine before closing
    stop_voice()
    cam.release()
    cv2.destroyAllWindows()

def recognize_from_image(image_path):
    """Recognize faces from a static image file and mark attendance"""
    harcascadePath = "haarcascade_default.xml"
    model_path = os.path.join("TrainingImageLabel", "Trainner.yml")
    details_path = os.path.join("StudentDetails", "StudentDetails.csv")

    if not os.path.exists(harcascadePath): return {'status': 'error', 'message': 'Haarcascade not found'}
    if not os.path.exists(model_path): return {'status': 'error', 'message': 'Model not trained'}
    if not os.path.exists(details_path): return {'status': 'error', 'message': 'Student details not found'}

    faceCascade = cv2.CascadeClassifier(harcascadePath)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(model_path)

    df = pd.read_csv(details_path)
    df.columns = df.columns.str.strip()
    # IMPORTANT: Ensure ID comparisons work even if CSV stores Id as number
    if 'Id' in df.columns:
        df['Id'] = df['Id'].astype(str).str.strip()

    img = cv2.imread(image_path)
    if img is None: return {'status': 'error', 'message': 'Could not read image'}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    
    faces = faceCascade.detectMultiScale(gray, 1.2, 5)
    if len(faces) == 0: return {'status': 'error', 'message': 'No faces detected'}

    # Prepare attendance file
    if not os.path.exists("Attendance"): os.makedirs("Attendance")
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    fileName = f"Attendance/Attendance_{current_date}.csv"
    
    # Load existing recorded IDs - use string IDs
    recorded_ids = set()
    if os.path.isfile(fileName):
        try:
            with open(fileName, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if row and len(row) > 0:
                        recorded_ids.add(str(row[0]))
        except: pass

    marked_names = []
    for (x, y, w, h) in faces:
        face_roi = gray[y:y+h, x:x+w]
        
        numeric_id, conf = recognizer.predict(face_roi)
        # Convert numeric label back to original string ID
        Id = get_original_id(numeric_id)
        Id_str = str(Id)
        
        if conf < 85:
            try: 
                name = df.loc[df['Id'] == Id_str]['Name'].values[0]
            except: 
                name = "Unknown"
            
            # Get student year and branch
            student_year = ""
            student_branch = ""
            try:
                student_row = df.loc[df['Id'] == Id_str]
                if 'Year' in df.columns:
                    student_year = str(student_row['Year'].values[0])
                if 'Branch' in df.columns:
                    student_branch = str(student_row['Branch'].values[0])
            except:
                pass
                
            # Only save if student is recognized (not Unknown)
            if name != "Unknown" and Id_str != "0":
                if Id_str not in recorded_ids:
                    ts = time.time()
                    date_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    time_str = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    
                    file_exists = os.path.isfile(fileName)
                    with open(fileName, 'a', newline='') as f:
                        writer = csv.writer(f)
                        if not file_exists: 
                            writer.writerow(['Id', 'Name', 'Date', 'Time', 'Year', 'Branch'])
                        writer.writerow([Id_str, name, date_str, time_str, student_year, student_branch])
                    recorded_ids.add(Id_str)
                    marked_names.append(name)
                else:
                    if name not in marked_names: marked_names.append(f"{name} (Already Marked)")
            else:
                print(f"SKIPPED: Unknown face in image (ID: {Id_str}) - not saved to attendance")

    if not marked_names: return {'status': 'error', 'message': 'Faces detected but not recognized'}
    return {'status': 'success', 'message': f'Attendance marked for: {", ".join(marked_names)}'}

if __name__ == "__main__":
    recognize_attendence()
