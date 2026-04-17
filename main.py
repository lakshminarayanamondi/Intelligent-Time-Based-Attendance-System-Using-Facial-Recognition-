import os
import check_camera, capture_image, train_image, recognize

def mainMenu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n***** Face Recognition Attendance System *****")
        print("[1] Check Camera")
        print("[2] Capture Faces")
        print("[3] Train Images")
        print("[4] Recognize & Attendance")
        print("[5] Quit")
        
        choice = input("Enter Choice: ")
        
        if choice == '1':
            check_camera.camer()
        elif choice == '2':
            capture_image.takeImages()
        elif choice == '3':
            train_image.TrainImages()
        elif choice == '4':
            recognize.recognize_attendence()
        elif choice == '5':
            print("Thank You")
            break
        else:
            print("Invalid Choice. Try again.")
        
        input("\nPress Enter to return to main menu...")

if __name__ == "__main__":
    mainMenu()