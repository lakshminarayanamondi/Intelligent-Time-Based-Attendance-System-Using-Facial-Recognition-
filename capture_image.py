import cv2
import os
import time
import sys
import sqlite3 # Import SQLite

def is_number(s):
    """Checks if the input string is a valid number."""
    try:
        float(s)
        return True
    except ValueError:
        return False

def takeImages(Id=None, name=None, year=None, branch=None):
    """Captures face samples and organizes them into 'Name_ID' folders."""
    
    # Ensure base directories exist
    if not os.path.exists("TrainingImage"):
        os.makedirs("TrainingImage")

    # If arguments weren't passed (running from terminal), ask for them
    if Id is None or name is None:
        Id = input("Enter Your Id: ")
        name = input("Enter Your Name: ")
        print("Select Year:")
        print("1. First Year (1st Year)")
        print("2. Second Year (2nd Year)")
        print("3. Third Year (3rd Year)")
        print("4. Fourth Year (4th Year)")
        year_choice = input("Enter Year (1-4): ")
        year_map = {'1': '1st Year', '2': '2nd Year', '3': '3rd Year', '4': '4th Year'}
        year = year_map.get(year_choice, '1st Year')
        
        print("\nSelect Branch:")
        print("1. Computer Science Engineering (CSE)")
        print("2. Information Technology (IT)")
        print("3. Electronics and Communication Engineering (ECE)")
        print("4. Electrical and Electronics Engineering (EEE)")
        print("5. Mechanical Engineering (ME)")
        print("6. Civil Engineering (CE)")
        branch_choice = input("Enter Branch (1-6): ")
        branch_map = {'1': 'CSE', '2': 'IT', '3': 'ECE', '4': 'EEE', '5': 'ME', '6': 'CE'}
        branch = branch_map.get(branch_choice, 'CSE')

    # Validation - Allow alphanumeric IDs (e.g., CSE2024001)
    if Id and name.isalpha():
        cam = cv2.VideoCapture(0)
        harcascadePath = "haarcascade_default.xml"
        
        if not os.path.exists(harcascadePath):
            print(f"Error: {harcascadePath} not found.")
            return "Error: Haarcascade not found"

        detector = cv2.CascadeClassifier(harcascadePath)
        sampleNum = 0

        # Create Subfolder
        student_folder = os.path.join("TrainingImage", f"{name}_{Id}")
        if not os.path.exists(student_folder):
            os.makedirs(student_folder)
        
        print(f"Saving images to: {student_folder}")
        print("Tip: Turn your head slightly Left, Right, Up, and Down.")
        print("Press ENTER to stop early.")

        while True:
            ret, img = cam.read()
            if not ret:
                print("Failed to grab frame.")
                break
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray) # Histogram Equalization

            faces = detector.detectMultiScale(gray, 1.3, 5, minSize=(30, 30))
            
            for (x, y, w, h) in faces:
                # Add 20% padding to capture the full head
                padding_x = int(w * 0.2)
                padding_y = int(h * 0.2)
                
                # Update coordinates (ensure they don't go off-screen)
                x = max(0, x - padding_x)
                y = max(0, y - padding_y)
                w = w + (padding_x * 2)
                h = h + (padding_y * 2)

                cv2.rectangle(img, (x, y), (x + w, y + h), (10, 159, 255), 2)
                sampleNum += 1
                
                # Save INSIDE the subfolder
                file_name = f"{name}.{Id}.{sampleNum}.jpg"
                img_path = os.path.join(student_folder, file_name)
                
                try:
                    cv2.imwrite(img_path, gray[y:y+h, x:x+w])
                except Exception:
                    pass # Skip frames where the box is off-screen

                cv2.imshow('Face Capturing', img)

            # Slower Capture - gives time to rotate head.
            if cv2.waitKey(30) & 0xFF == 13: # 13 is Enter Key
                break
            elif sampleNum >= 50:
                break
        
        cam.release()
        cv2.destroyAllWindows()
        
        # ==========================================
        # NEW: SECURE SQLITE DATABASE SAVING LOGIC
        # ==========================================
        db_status = ""
        try:
            # Connect to attendance.db located in the same folder as this script
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attendance.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if student already exists
            cursor.execute("SELECT * FROM students WHERE student_id=?", (Id,))
            existing = cursor.fetchone()
            
            if existing:
                db_status = "duplicate_id"
                print(f"[INFO] Student ID '{Id}' is already in Database. Updating records.")
            
            # Insert or replace into the database. 
            # Note: We use their ID as their default password!
            cursor.execute('''
                INSERT OR REPLACE INTO students (student_id, name, password, year, branch) 
                VALUES (?, ?, ?, ?, ?)
            ''', (Id, name, Id, year, branch))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Database Error: {e}")
            return f"Error saving to database: {e}"
        # ==========================================

        msg = f"Saved {sampleNum} images in folder '{name}_{Id}'"
        if db_status == 'duplicate_id':
            msg += ". Student record updated in Database."
        else:
            msg += ". Student added to Database successfully."
            
        print(msg)
        return msg
        
    else:
        if not Id:
            print("Error: ID cannot be empty.")
            return "Error: ID cannot be empty"
        if not name.isalpha():
            print("Error: Enter an alphabetical Name.")
            return "Error: Name must be alphabetic"

if __name__ == "__main__":
    # Parse command-line arguments if provided
    if len(sys.argv) >= 4:
        # Called from Flask server with arguments: python capture_image.py Id Name Year Branch
        Id = sys.argv[1]
        name = sys.argv[2]
        year = sys.argv[3] if len(sys.argv) > 3 else ''
        branch = sys.argv[4] if len(sys.argv) > 4 else ''
        takeImages(Id, name, year, branch)
    else:
        # Called directly without arguments - ask for input
        takeImages()