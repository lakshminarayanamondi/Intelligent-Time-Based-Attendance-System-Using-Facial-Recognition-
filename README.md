# 🎓 Smart Attendance System

A Face Recognition-based Attendance Management System with a modern web interface.

## 📁 Project Structure

```
Code/
├── server.py              # Flask server (main entry point)
├── capture_image.py       # Capture student face images
├── train_image.py         # Train face recognition model
├── recognize.py           # Recognize faces and mark attendance
├── check_camera.py        # Test camera functionality
├── main.py                # CLI version (alternative to web)
├── haarcascade_default.xml # Face detection model
├── requirements.txt       # Python dependencies
├── README.md             # This file
│
├── templates/            # HTML templates
│   ├── index.html        # Login page
│   ├── teacher.html      # Teacher dashboard
│   └── student.html      # Student dashboard
│
├── statics/              # CSS and JavaScript
│   ├── style.css         # Styling
│   └── script.js         # Frontend logic
│
├── StudentDetails/       # Student data
│   └── StudentDetails.csv
│
├── TrainingImage/        # Captured face images
├── TrainingImageLabel/   # Trained model
└── Attendance/           # Attendance records
```

## 🚀 How to Run

### Step 1: Install Dependencies

```bash
cd Code
pip install -r requirements.txt
```

### Step 2: Start the Server

```bash
python server.py
```

### Step 3: Open Browser

Go to: **http://127.0.0.1:5000**

## 🔑 Login Credentials

### Teacher Login
- **Username:** `teacher`
- **Password:** `teacher123`

### Student Login
Students use their name and ID as credentials:
- **Username:** `studentname` (lowercase)
- **Password:** `studentname_id`

**Examples:**
- Ganapathi: `ganapathi` / `ganapathi_1`
- Jana: `jana` / `jana_2`
- Padma: `padma` / `padma_3`

## 📋 Features

### Teacher Dashboard
- ✅ Register new students (capture face images)
- 🧠 Train face recognition model
- 📸 Take attendance (launch AI camera)
- 📅 **Working Days Calendar** - Select working days for each month
- 📊 View attendance analytics

### Student Dashboard
- 📈 View attendance percentage (based on working days)
- 📅 Attendance calculator
- 🎯 Set attendance targets


## 🔄 Workflow

1. **Set Working Days:** Teacher selects month/year → Clicks on dates to mark working days → Save
2. **Register Student:** Teacher enters ID and name → Camera opens → Capture 50 face images
3. **Train Model:** Click "Train Images" → System learns faces
4. **Take Attendance:** Click "Launch Camera" → System recognizes faces and marks attendance
5. **View Stats:** Students can check their attendance percentage (calculated based on working days only)

## 📅 Working Days Calendar

The system now includes a **Working Days Calendar** feature:

- Teachers can select which days are working days for each month
- Sundays are automatically excluded (non-selectable)
- Attendance percentage is calculated based on working days only
- Example: If a month has 22 working days and a student attended 20, attendance = 90.9%

### How to Use:
1. Go to Teacher Dashboard
2. Select month and year from dropdown
3. Click on dates to mark/unmark as working days
4. Click "Save Working Days"
5. Student attendance will be calculated based on these working days


## 🛠️ Technical Details

- **Backend:** Flask (Python)
- **Face Recognition:** OpenCV with LBPH algorithm
- **Face Detection:** Haar Cascade + MTCNN
- **Frontend:** HTML, CSS, JavaScript
- **Data Storage:** CSV files

## 📝 Notes

- Make sure your camera is connected before using the system
- The camera windows will open in separate windows (not in browser)
- Close the camera window when done capturing images
- Attendance is saved automatically to CSV files

## 🐛 Troubleshooting

**Camera not working?**
- Run `python check_camera.py` to test
- Make sure no other app is using the camera

**Face not recognized?**
- Make sure you trained the model after registering
- Ensure good lighting when capturing images

**Server won't start?**
- Check if port 5000 is already in use
- Make sure all dependencies are installed
