import cv2
import os

def camer():
    # Load the cascade
    harcascadePath = 'haarcascade_default.xml'
    
    # Check if cascade file exists to avoid crashes
    if not os.path.exists(harcascadePath):
        print(f"Error: {harcascadePath} not found in the directory.")
        return
        
    cascade_face = cv2.CascadeClassifier(harcascadePath)

    # To capture video from webcam.
    cap = cv2.VideoCapture(0)

    print("Camera Check Active: Press ENTER to exit.")

    while True:
        # Read the frame
        ret, img = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect the faces
        faces = cascade_face.detectMultiScale(
            gray, 
            1.3, 
            5, 
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        # Draw the rectangle around each face
        for (a, b, c, d) in faces:
            cv2.rectangle(img, (a, b), (a + c, b + d), (10, 159, 255), 2)

        # Display
        cv2.imshow('Webcam Check', img)

        # UPDATED: 13 is the Enter key. Use this to close the window.
        if cv2.waitKey(1) & 0xFF == 13:
            break

    # Release the captureVideo object
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    camer()