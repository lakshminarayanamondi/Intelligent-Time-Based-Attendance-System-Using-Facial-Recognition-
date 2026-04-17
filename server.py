"""
Flask Server for Smart Attendance System
Connects the frontend (HTML/CSS/JS) with the backend Python scripts
"""

from flask import Flask, render_template, request, jsonify, Response
import os
from datetime import datetime
import sys
import subprocess
import csv
import datetime
import pandas as pd
import calendar
import json
from threading import Thread
import sqlite3

app = Flask(__name__, static_folder='statics', static_url_path='/static')

# for landing page route
@app.route('/')
def home():
    """Renders the Professional Landing Page"""
    return render_template('index.html')

@app.route('/login_page')
def login_page():
    """Renders the Login Form"""
    return render_template('login.html')


# Set the path to the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Working days storage - Now with Year and Branch support
WORKING_DAYS_FILE = os.path.join(PROJECT_ROOT, "working_days.json")


# Teacher credentials (Dynamic)
TEACHERS_FILE = os.path.join(PROJECT_ROOT, "teachers.json")

# Admin credentials (Hardcoded)
ADMIN_USER = {
    "admin": {"password": "admin123", "role": "admin"}
}

def load_teachers():
    """Load teacher accounts from JSON"""
    if os.path.exists(TEACHERS_FILE):
        try:
            with open(TEACHERS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    # Default fallback if file doesn't exist
    return {"teacher": {"password": "teacher123", "role": "teacher", "branch": ""}}

def save_teachers(teachers_dict):
    """Save teacher accounts to JSON"""
    with open(TEACHERS_FILE, 'w') as f:
        json.dump(teachers_dict, f, indent=2)

# Backwards-compatible alias used throughout the file
TEACHER_USER = load_teachers()

# Store registered students (loaded from CSV)
students_db = {}
STUDENTS_FILE = os.path.join(PROJECT_ROOT, "StudentDetails", "StudentDetails.csv")

def load_students():
    """Load students from the CSV file and create login credentials"""
    students = {}
    if os.path.exists(STUDENTS_FILE):
        try:
            df = pd.read_csv(STUDENTS_FILE)
            df.columns = df.columns.str.strip()
            for _, row in df.iterrows():
                raw_id = row['Id']
                if pd.isna(raw_id) or str(raw_id).strip() == '':
                    continue
                student_id = str(raw_id).strip()
                raw_name = row['Name']
                if pd.isna(raw_name) or str(raw_name).strip() == '':
                    continue
                student_name = str(raw_name).strip()
                student_year = str(row['Year']) if 'Year' in df.columns and pd.notna(row.get('Year')) else ''
                student_branch = str(row['Branch']).strip() if 'Branch' in df.columns and pd.notna(row.get('Branch')) else ''
                key = student_name.lower()
                # One login per name: keep first row if CSV had duplicates
                if key in students:
                    continue
                students[key] = {
                    "password": student_id,
                    "role": "student",
                    "id": student_id,
                    "name": student_name,
                    "year": student_year,
                    "branch": student_branch,
                }
        except Exception as e:
            print(f"Error loading students: {e}")
    return students

# Load students on startup and combine with teacher
USERS = {}
USERS.update(ADMIN_USER)
USERS.update(TEACHER_USER)
USERS.update(load_students())

def load_working_days():
    """Load working days from JSON file"""
    if os.path.exists(WORKING_DAYS_FILE):
        try:
            with open(WORKING_DAYS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading working days: {e}")
    return {}

def save_working_days(working_days):
    """Save working days to JSON file"""
    try:
        with open(WORKING_DAYS_FILE, 'w') as f:
            json.dump(working_days, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving working days: {e}")
        return False

def get_working_days_for_month(year, month, branch='', year_select=''):
    """Get working days for a specific month and branch
    
    Returns working days only for the exact branch/year combination.
    If no working days exist for the specific combination, returns empty list.
    No fallback to generic entries to prevent showing wrong branch's working days.
    """
    working_days = load_working_days()
    
    # Format 1: year-month-year_select-branch (e.g., "2026-02-4th Year-CSE")
    # This is the most specific key - prioritize this
    if branch and year_select:
        key1 = f"{year}-{month:02d}-{year_select}-{branch}"
        if key1 in working_days:
            return working_days[key1]
    
    # Format 2: year-month-branch (e.g., "2026-02-CSE")
    # Use this if year_select is not provided but branch is
    if branch:
        key2 = f"{year}-{month:02d}-{branch}"
        if key2 in working_days:
            return working_days[key2]
    
    # Return empty list if no exact match found
    # DO NOT fall back to generic year-month entries to prevent showing wrong data
    return []


def calculate_working_days_in_range(start_date, end_date, working_days_list):
    """Calculate how many working days fall within a date range"""
    count = 0
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        if date_str in working_days_list:
            count += 1
        current += datetime.timedelta(days=1)
    return count



# ==================== ROUTES ====================

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')

# Static files are now served automatically by Flask with the configured static_url_path


# ==================== API ENDPOINTS ====================

@app.route('/login', methods=['POST'])
def login():
    """Handle login request"""
    data = request.get_json()
    username = data.get('username', '').lower()
    password = data.get('password', '')
    
    # Reload students dynamically to include newly registered students
    current_users = {}
    current_users.update(ADMIN_USER)
    current_users.update(load_teachers())
    current_users.update(TEACHER_USER)
    current_users.update(load_students())
    
    if username in current_users and current_users[username]['password'] == password:
        user = current_users[username].copy()
        user['username'] = username
        return jsonify({
            'status': 'success',
            'role': user['role'],
            'id': user.get('id', ''),
            'name': user.get('name', ''),
            'year': user.get('year', ''),
            'branch': user.get('branch', ''),
            'message': 'Login successful'
        })
    
    return jsonify({
        'status': 'error',
        'message': 'Invalid credentials'
    }), 401


@app.route('/start_register', methods=['POST'])
def start_register():
    """Start the student registration process - capture face images"""
    data = request.get_json()
    student_id = str(data.get('id', ''))  # Keep as string for alphanumeric
    name = data.get('name', '')
    year = data.get('year', '')
    branch = data.get('branch', '')
    
    if not student_id or not name or not year or not branch:
        return jsonify({
            'status': 'error',
            'message': 'ID, Name, Year, and Branch are required'
        })
    
    try:
        # Run the capture_image.py script in a separate thread
        # This will open a camera window for capturing face images
        capture_script = os.path.join(PROJECT_ROOT, 'capture_image.py')
        
        # Run in a separate process - this will open the camera window
        subprocess.Popen(
            [sys.executable, capture_script, student_id, name, year, branch],
            cwd=PROJECT_ROOT
        )
        
        return jsonify({
            'status': 'success',
            'message': f'Camera opened for {name} (ID: {student_id}). Capture face images and close the camera when done.'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })

@app.route('/start_train', methods=['POST'])
def start_train():
    """Train the face recognition model"""
    try:
        train_script = os.path.join(PROJECT_ROOT, 'train_image.py')
        
        # Run training and wait for it to complete
        result = subprocess.run(
            [sys.executable, train_script],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': 'Model trained successfully!'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Training failed: {result.stderr}'
            })
    except subprocess.TimeoutExpired:
        return jsonify({
            'status': 'error',
            'message': 'Training timeout - took too long'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })

@app.route('/start_attendance', methods=['POST'])
def start_attendance():
    """Start the attendance system - opens camera for face recognition"""
    try:
        # First, check if required dependencies are installed
        missing_deps = []
        try:
            import cv2
            # Check if opencv-contrib-python is installed (has LBPHFaceRecognizer)
            if not hasattr(cv2, 'face'):
                missing_deps.append('opencv-contrib-python')
        except ImportError:
            missing_deps.append('opencv-python')
        
        try:
            import numpy
        except ImportError:
            missing_deps.append('numpy')
        
        try:
            import pandas
        except ImportError:
            missing_deps.append('pandas')
        
        if missing_deps:
            return jsonify({
                'status': 'error',
                'message': f'Missing dependencies: {", ".join(missing_deps)}. Please install them: pip install ' + ' '.join(missing_deps)
            })
        
        # Check if model exists
        model_path = os.path.join(PROJECT_ROOT, "TrainingImageLabel", "Trainner.yml")
        if not os.path.exists(model_path):
            return jsonify({
                'status': 'error',
                'message': 'Model not trained. Please train the model first by clicking "Train Images".'
            })
        
        # Check if students are registered
        if not os.path.exists(STUDENTS_FILE):
            return jsonify({
                'status': 'error',
                'message': 'No students registered. Please register students first.'
            })
        
        recognize_script = os.path.join(PROJECT_ROOT, 'recognize.py')
        
        # Create log file for debugging
        log_file = os.path.join(PROJECT_ROOT, 'attendance.log')
        
        # Run in a separate process - this will open the camera for recognition
        # Using Popen with output redirected to a log file for debugging
        with open(log_file, 'a') as log:
            log.write(f"\n--- Attendance started at {datetime.datetime.now()} ---\n")
            process = subprocess.Popen(
                [sys.executable, recognize_script],
                cwd=PROJECT_ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                bufsize=1
            )
        
        return jsonify({
            'status': 'success',
            'message': 'Attendance camera opened. Close the window when done. Check attendance.log for debug info.'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })

@app.route('/upload_attendance', methods=['POST'])
def upload_attendance():
    """Handle attendance via image upload"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'})
        
    if file:
        try:
            from werkzeug.utils import secure_filename
            import recognize
            
            filename = secure_filename(file.filename)
            temp_path = os.path.join(PROJECT_ROOT, filename)
            file.save(temp_path)
            
            result = recognize.recognize_from_image(temp_path)
            
            if os.path.exists(temp_path): os.remove(temp_path)
            return jsonify(result)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

@app.route('/get_analytics', methods=['GET'])
def get_analytics():
    """Get attendance analytics for the chart"""
    attendance_dir = os.path.join(PROJECT_ROOT, 'Attendance')
    analytics = {}
    
    if os.path.exists(attendance_dir):
        try:
            # Get all attendance CSV files
            csv_files = [f for f in os.listdir(attendance_dir) if f.endswith('.csv')]
            
            for csv_file in csv_files:
                file_path = os.path.join(attendance_dir, csv_file)
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip()
                
                # Count unique students per day
                date = csv_file.replace('Attendance_', '').replace('.csv', '')
                analytics[date] = len(df['Id'].unique())
        except Exception as e:
            print(f"Error reading analytics: {e}")
    
    return jsonify({
        'status': 'success',
        'data': analytics
    })

@app.route('/student_stats', methods=['POST'])
def student_stats():
    """Get attendance statistics for a specific student"""
    data = request.get_json()
    student_id = str(data.get('id', ''))  # Keep as string
    
    attendance_dir = os.path.join(PROJECT_ROOT, 'Attendance')
    present = 0
    total_days = 0
    
    # Load student details
    students = load_students()
    student_name = "Unknown"
    for user_key, user_data in students.items():
        if user_data.get('id') == student_id:
            student_name = user_data.get('name', 'Unknown')
            break
    
    if os.path.exists(attendance_dir):
        try:
            csv_files = [f for f in os.listdir(attendance_dir) if f.endswith('.csv')]
            total_days = len(csv_files)
            
            for csv_file in csv_files:
                file_path = os.path.join(attendance_dir, csv_file)
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip()
                
                # Check if student was present (compare as string)
                df['Id'] = df['Id'].astype(str)
                if str(student_id) in df['Id'].values:
                    present += 1
        except Exception as e:
            print(f"Error reading student stats: {e}")
    
    percentage = round((present / total_days) * 100, 1) if total_days > 0 else 0
    
    return jsonify({
        'status': 'success',
        'present': present,
        'total': total_days,
        'percentage': percentage,
        'name': student_name
    })

@app.route('/check_camera', methods=['POST'])
def check_camera():
    """Test if camera is working"""
    try:
        check_script = os.path.join(PROJECT_ROOT, 'check_camera.py')
        
        # Run camera check
        subprocess.Popen(
            [sys.executable, check_script],
            cwd=PROJECT_ROOT
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Camera check window opened'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })

# ==================== WORKING DAYS API (Now with Year/Branch support) ====================

@app.route('/get_working_days', methods=['GET'])
def get_working_days():
    """Get working days for a specific month, year, and branch"""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    branch = request.args.get('branch', '')  # Optional branch filter
    year_select = request.args.get('year_select', '')  # Optional year filter
    
    if not year or not month:
        return jsonify({
            'status': 'error',
            'message': 'Year and month are required'
        }), 400
    
    working_days = get_working_days_for_month(year, month, branch, year_select)

    
    # Get all days in month for calendar display
    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(year, month)

    
    return jsonify({
        'status': 'success',
        'year': year,
        'month': month,
        'branch': branch,
        'working_days': working_days,
        'calendar': month_days,
        'month_name': calendar.month_name[month]
    })

@app.route('/set_working_days', methods=['POST'])
def set_working_days():
    """Set working days for a specific month, year, and branch"""
    data = request.get_json()
    year = data.get('year')
    month = data.get('month')
    branch = data.get('branch', '')  # Optional branch
    year_select = data.get('year_select', '')  # Academic year (1st, 2nd, 3rd, 4th)
    days = data.get('days', [])  # List of dates in 'YYYY-MM-DD' format
    
    if not year or not month or not days:
        return jsonify({
            'status': 'error',
            'message': 'Year, month, and days are required'
        }), 400
    
    working_days = load_working_days()
    
    # Key format: year-month-branch (e.g., "2026-02-CSE")
    # Include year_select in the key if provided for more specific grouping
    if branch:
        if year_select:
            key = f"{year}-{month:02d}-{year_select}-{branch}"
        else:
            key = f"{year}-{month:02d}-{branch}"
    else:
        key = f"{year}-{month:02d}"
    
    working_days[key] = days
    
    if save_working_days(working_days):
        branch_text = f" for {branch}" if branch else ""
        year_text = f" ({year_select})" if year_select else ""
        return jsonify({
            'status': 'success',
            'message': f'Working days set for {calendar.month_name[month]} {year}{branch_text}{year_text}',
            'count': len(days)
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to save working days'
        }), 500

@app.route('/get_all_working_days', methods=['GET'])
def get_all_working_days():
    """Get all working days data"""
    return jsonify({
        'status': 'success',
        'data': load_working_days()
    })

def is_working_day(date_str, branch=''):
    """Check if a specific date is a working day for a branch"""
    working_days = load_working_days()
    for month_key, days in working_days.items():
        if date_str in days:
            # Check if it matches the branch or is a general day
            if not branch or month_key.endswith(branch):
                return True
    return False

@app.route('/is_today_working_day', methods=['GET'])
def check_today_working():
    """Check if today is a working day"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    branch = request.args.get('branch', '')
    return jsonify({
        'status': 'success',
        'is_working_day': is_working_day(today, branch),
        'date': today
    })

@app.route('/student_stats_working_days', methods=['POST'])
def student_stats_working_days():
    """Get attendance statistics based on working days - monthly or total
    
    Uses the student's branch to get branch-specific working days.
    No fallback to generic entries - returns 0 if no working days set for branch.
    """
    data = request.get_json()
    student_id = str(data.get('id', ''))  # Keep as string
    year = data.get('year')
    month = data.get('month')
    branch = data.get('branch', '')  # Student's branch
    
    attendance_dir = os.path.join(PROJECT_ROOT, 'Attendance')
    present = 0
    
    # Load student details FIRST to get year and branch
    students = load_students()
    student_name = "Unknown"
    student_year = ""
    student_branch = ""
    for user_key, user_data in students.items():
        if user_data.get('id') == student_id:
            student_name = user_data.get('name', 'Unknown')
            student_year = user_data.get('year', '')
            student_branch = user_data.get('branch', '')
            break
    
    # Use student's branch if not provided in request
    if not branch and student_branch:
        branch = student_branch
    
    # Load working days
    working_days = load_working_days()
    
    # If year and month provided, get working days for that month and branch
    if year and month:
        # Get working days using the same logic as get_working_days_for_month
        month_working_days = []
        if branch:
            # Try with year_select first
            if student_year and student_year != 'all':
                key1 = f"{year}-{month:02d}-{student_year}-{branch}"
                if key1 in working_days:
                    month_working_days = working_days[key1]
            
            # Try branch-only key
            if not month_working_days:
                key2 = f"{year}-{month:02d}-{branch}"
                if key2 in working_days:
                    month_working_days = working_days[key2]
        
        # NO FALLBACK - return empty if no exact match found
        # This ensures branch-specific working days are respected

        total_working_days = len(month_working_days)
        
        # Count present days for this month only
        if os.path.exists(attendance_dir) and total_working_days > 0:
            try:
                for date_str in month_working_days:
                    file_path = os.path.join(attendance_dir, f"Attendance_{date_str}.csv")
                    if os.path.exists(file_path):
                        try:
                            df = pd.read_csv(file_path)
                            df.columns = df.columns.str.strip()
                            df['Id'] = df['Id'].astype(str)
                            if str(student_id) in df['Id'].values:
                                present += 1
                        except Exception as e:
                            print(f"Error reading {date_str}: {e}")
                            continue
            except Exception as e:
                print(f"Error reading student stats: {e}")
    else:
        # Calculate total across all months for this specific year+branch ONLY
        # Must match exact year+branch combination, not just branch suffix
        all_working_days = []
        seen_days = set()  # To avoid duplicates
        
        if branch and student_year:
            # Only get working days for this EXACT year+branch combination
            for month_key, days in working_days.items():
                # Check if this key matches exactly: year-month-year_select-branch
                expected_prefix = f"-{student_year}-{branch}"
                if month_key.endswith(expected_prefix):
                    for day in days:
                        if day not in seen_days:
                            all_working_days.append(day)
                            seen_days.add(day)
        elif branch:
            # If no year, try to get branch-specific (without year) - for backward compatibility
            for month_key, days in working_days.items():
                # Only get entries that end with -branch but DON'T have year prefix
                if month_key.endswith(f"-{branch}") and "-" not in month_key.replace(f"-{branch}", ""):
                    for day in days:
                        if day not in seen_days:
                            all_working_days.append(day)
                            seen_days.add(day)
        
        total_working_days = len(all_working_days)
        
        # Count present days across all working days
        if os.path.exists(attendance_dir) and total_working_days > 0:
            try:
                csv_files = [f for f in os.listdir(attendance_dir) if f.endswith('.csv')]
                
                for csv_file in csv_files:
                    date_str = csv_file.replace('Attendance_', '').replace('.csv', '')
                    if date_str in all_working_days:
                        file_path = os.path.join(attendance_dir, csv_file)
                        try:
                            df = pd.read_csv(file_path)
                            df.columns = df.columns.str.strip()
                            df['Id'] = df['Id'].astype(str)
                            if str(student_id) in df['Id'].values:
                                present += 1
                        except Exception as e:
                            print(f"Error reading {csv_file}: {e}")
                            continue
            except Exception as e:
                print(f"Error reading student stats: {e}")
    
    percentage = round((present / total_working_days) * 100, 1) if total_working_days > 0 else 0
    
    return jsonify({
        'status': 'success',
        'present': present,
        'total_working_days': total_working_days,
        'percentage': percentage,
        'name': student_name,
        'year': student_year,
        'branch': student_branch,
        'month': month if month else 'all',
        'year_param': year if year else 'all'
    })



@app.route('/get_student_attendance_dates', methods=['POST'])
def get_student_attendance_dates():
    """Get all dates a student attended"""
    data = request.get_json()
    student_id = str(data.get('id', ''))  # Keep as string
    
    attendance_dates = []
    attendance_dir = os.path.join(PROJECT_ROOT, 'Attendance')
    
    if os.path.exists(attendance_dir):
        try:
            csv_files = [f for f in os.listdir(attendance_dir) if f.endswith('.csv')]
            for csv_file in sorted(csv_files):
                file_path = os.path.join(attendance_dir, csv_file)
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip()
                df['Id'] = df['Id'].astype(str)
                
                if str(student_id) in df['Id'].values:
                    # Extract date from filename (Attendance_YYYY-MM-DD.csv)
                    date_str = csv_file.replace('Attendance_', '').replace('.csv', '')
                    attendance_dates.append(date_str)
        except Exception as e:
            print(f"Error getting attendance dates: {e}")
    
    return jsonify({
        'status': 'success',
        'attended_dates': attendance_dates
    })

@app.route('/get_all_students', methods=['GET'])
def get_all_students():
    """Get all registered students for teacher analytics"""
    students = []
    
    # Load from StudentDetails.csv
    if os.path.exists(STUDENTS_FILE):
        try:
            df = pd.read_csv(STUDENTS_FILE)
            df.columns = df.columns.str.strip()
            for _, row in df.iterrows():
                students.append({
                    'id': str(row['Id']),  # Keep as string
                    'name': row['Name'],
                    'year': str(row['Year']) if 'Year' in df.columns else '',
                    'branch': row['Branch'] if 'Branch' in df.columns else ''
                })
        except Exception as e:
            print(f"Error loading students: {e}")
    
    return jsonify({
        'status': 'success',
        'students': students
    })

# ==================== ANALYTICS BY YEAR/BRANCH ====================

@app.route('/get_analytics_by_year_branch', methods=['GET'])
def get_analytics_by_year_branch():
    """Get attendance analytics filtered by year and/or branch"""
    year_filter = request.args.get('year', '')
    branch_filter = request.args.get('branch', '')
    
    attendance_dir = os.path.join(PROJECT_ROOT, 'Attendance')
    analytics = {}
    
    # Load student details
    students = load_students()
    
    # Filter students by year and branch
    filtered_students = []
    for user_key, user_data in students.items():
        if user_data.get('role') == 'student':
            if year_filter and user_data.get('year') != year_filter:
                continue
            if branch_filter and user_data.get('branch') != branch_filter:
                continue
            filtered_students.append(user_data.get('id'))
    
    if os.path.exists(attendance_dir):
        try:
            csv_files = [f for f in os.listdir(attendance_dir) if f.endswith('.csv')]
            
            for csv_file in csv_files:
                file_path = os.path.join(attendance_dir, csv_file)
                df = pd.read_csv(file_path)
                df.columns = df.columns.str.strip()
                df['Id'] = df['Id'].astype(str)
                
                # Count filtered students present
                date = csv_file.replace('Attendance_', '').replace('.csv', '')
                present_count = len(set([str(s) for s in df['Id'].unique()]) & set([str(s) for s in filtered_students]))
                analytics[date] = {
                    'present': present_count,
                    'total': len(filtered_students)
                }
        except Exception as e:
            print(f"Error reading analytics: {e}")
    
    return jsonify({
        'status': 'success',
        'data': analytics,
        'filtered_count': len(filtered_students)
    })

@app.route('/get_year_branch_stats', methods=['GET'])
def get_year_branch_stats():
    """Get statistics grouped by year and branch"""
    students = load_students()
    
    years = {}
    branches = {}
    
    for user_key, user_data in students.items():
        if user_data.get('role') == 'student':
            year = user_data.get('year', 'Unknown')
            branch = user_data.get('branch', 'Unknown')
            
            if year:
                years[year] = years.get(year, 0) + 1
            if branch:
                branches[branch] = branches.get(branch, 0) + 1
    
    return jsonify({
        'status': 'success',
        'years': years,
        'branches': branches
    })

# --- 📝 LEAVE MANAGEMENT API ---
@app.route('/apply_leave', methods=['POST'])
def apply_leave():
    try:
        data = request.json
        student_id = data.get('student_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        reason = data.get('reason')
        
        if not all([student_id, start_date, end_date, reason]):
            return jsonify({"status": "error", "message": "Missing fields"}), 400

        # Timestamp for when they applied
        applied_on = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Pending"

        os.makedirs("StudentDetails", exist_ok=True)
        leaves_file = os.path.join("StudentDetails", "leaves.csv")
        file_exists = os.path.isfile(leaves_file)

        with open(leaves_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['ID', 'Start_Date', 'End_Date', 'Reason', 'Status', 'Applied_On'])
            writer.writerow([student_id, start_date, end_date, reason, status, applied_on])
        
        return jsonify({"status": "success", "message": "Leave request submitted successfully!"})
    except Exception as e:
        print(f"Error applying leave: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/get_all_leaves', methods=['GET'])
def get_all_leaves():
    """Fetch all leave requests for the teacher dashboard"""
    leaves_file = os.path.join("StudentDetails", "leaves.csv")
    leaves = []
    
    if os.path.exists(leaves_file):
        try:
            with open(leaves_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    leaves.append(row)
        except Exception as e:
            print(f"Error reading leaves: {e}")
            return jsonify({"status": "error", "message": "Failed to read leaves"}), 500
            
    return jsonify({"status": "success", "leaves": leaves})

@app.route('/update_leave_status', methods=['POST'])
def update_leave_status():
    """Approve or Reject a student's leave request"""
    try:
        data = request.json
        row_index = data.get('row_index')
        new_status = data.get('status')
        
        if row_index is None or not new_status:
            return jsonify({"status": "error", "message": "Missing data"}), 400
            
        leaves_file = os.path.join("StudentDetails", "leaves.csv")
        
        if not os.path.exists(leaves_file):
            return jsonify({"status": "error", "message": "No leave records found"}), 404
            
        # Read all current rows
        with open(leaves_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
        # row_index from frontend is 0-based for the data.
        # rows[0] is the header, so the actual row to update is row_index + 1
        actual_index = row_index + 1
        
        if actual_index < len(rows):
            # Column index 4 is the 'Status' column (ID, Start_Date, End_Date, Reason, Status, Applied_On)
            rows[actual_index][4] = new_status
            
            # Write the updated rows back to the CSV
            with open(leaves_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
                
            return jsonify({"status": "success", "message": f"Leave successfully {new_status}!"})
        else:
            return jsonify({"status": "error", "message": "Invalid request index"}), 400
    except Exception as e:
        print(f"Error updating leave status: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

# ==================== 🤖 ADVANCED AI CHATBOT API ====================
@app.route('/chatbot', methods=['POST'])
def chatbot():
    try:
        data = request.json
        user_message = data.get('message', '').lower()
        student_id = str(data.get('student_id', ''))
        
        # 1. Identify the Student logging in
        students = load_students()
        student_name = "Student"
        student_branch = ""
        for _, u in students.items():
            if u.get('id') == student_id:
                student_name = u.get('name', 'Student').title()
                student_branch = u.get('branch', '')
                break
                
        # 2. Calculate their real-time live attendance stats
        attendance_dir = os.path.join(PROJECT_ROOT, 'Attendance')
        present = 0
        working_days = load_working_days()
        all_working_days = []
        
        if student_branch:
            for k, days in working_days.items():
                if k.endswith(f"-{student_branch}"):
                    all_working_days.extend(days)
        
        all_working_days = list(set(all_working_days))
        total_wd = len(all_working_days)
        
        if os.path.exists(attendance_dir) and total_wd > 0:
            for d in all_working_days:
                fp = os.path.join(attendance_dir, f"Attendance_{d}.csv")
                if os.path.exists(fp):
                    df = pd.read_csv(fp)
                    df.columns = df.columns.str.strip()
                    if str(student_id) in df['Id'].astype(str).values:
                        present += 1
                        
        perc = round((present / total_wd) * 100, 1) if total_wd > 0 else 0

        # 3. Dynamic AI Response Engine
        reply = f"I'm sorry {student_name}, I didn't quite catch that. You can ask me things like 'What is my attendance?', 'How do I take leave?', or 'Are there holidays?'"
        
        # Attendance Logic
        if any(word in user_message for word in ['my attendance', 'percentage', 'present', 'stats', 'how many days']):
            reply = f"Hello {student_name}! Your current overall attendance is **{perc}%**. You have been present for {present} out of {total_wd} working days."
            if perc < 60:
                reply += " 🔴 You are in the High-Risk category. You need to attend classes immediately!"
            elif perc < 75:
                reply += " 🟠 You are slightly below the 75% requirement. Be careful with taking leaves."
            else:
                reply += " 🟢 Great job! You are maintaining excellent attendance."
                
        # Leave Logic
        elif any(word in user_message for word in ['leave', 'absent', 'sick', 'holiday']):
            reply = "If you are sick or need a holiday, you can apply for official leave using the 'Request Leave' form on your dashboard. Once your teacher approves it, it will be registered. Note: Approved leaves protect your percentage!"
            
        # Calendar Logic
        elif any(word in user_message for word in ['working days', 'calendar', 'schedule']):
            reply = f"Your branch ({student_branch}) currently has {total_wd} official working days registered in our system. Sundays are automatically excluded from attendance penalties."
            
        # Greetings
        elif any(word in user_message for word in ['hello', 'hi', 'hey', 'who are you']):
            reply = f"Hi {student_name}! I am your SmartAttend AI Assistant. I have direct access to your database records. Try asking me: 'What is my attendance?'"
            
        elif 'thank' in user_message:
            reply = f"You're very welcome, {student_name}! Keep up the good work."

        return jsonify({"reply": reply})
        
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return jsonify({"reply": "Sorry, I am having trouble connecting to the database right now."}), 500


# ==================== MAIN ====================



@app.route('/teacher')
def teacher_page():
    """Serve the teacher dashboard page"""
    return render_template('teacher.html')

@app.route('/student')
def student_page():
    """Serve the student dashboard page"""
    return render_template('student.html')

@app.route('/student_card')
def student_card_page():
    """Serve the student ID card page (for QR code scanning)"""
    student_id = request.args.get('id', '')
    if not student_id:
        return "<h1>Error: No student ID provided</h1>", 400
    
    # Load student details
    students = load_students()
    student_name = "Unknown"
    student_year = "Unknown"
    student_branch = "Unknown"
    for user_key, user_data in students.items():
        if user_data.get('id') == student_id:
            student_name = user_data.get('name', 'Unknown')
            student_year = user_data.get('year', 'Unknown')
            student_branch = user_data.get('branch', 'Unknown')
            break
    
    # Find student image folder
    student_folder = None
    training_dir = os.path.join(PROJECT_ROOT, "TrainingImage")
    if os.path.exists(training_dir):
        for folder in os.listdir(training_dir):
            folder_path = os.path.join(training_dir, folder)
            if os.path.isdir(folder_path) and folder.startswith(f"{student_name.lower()}_{student_id}"):
                student_folder = folder_path
                break
    
    # Get first image if available
    student_image = None
    if student_folder:
        images = [f for f in os.listdir(student_folder) if f.endswith('.jpg')]
        if images:
            student_image = f"/training_images/{student_name.lower()}_{student_id}/{images[0]}"
    
    # Get attendance stats
    stats_res = student_stats_working_days_internal(student_id, student_branch)
    stats = stats_res.get_json()
    
    # Get current date
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    
    # Generate HTML for the card
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Student ID Card - {student_name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            .id-card {{
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
                max-width: 400px;
                width: 100%;
            }}
            .card-header {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 25px;
                text-align: center;
            }}
            .card-header h1 {{
                font-size: 1.5em;
                margin-bottom: 5px;
            }}
            .card-header p {{
                opacity: 0.9;
                font-size: 0.9em;
            }}
            .photo-section {{
                padding: 30px;
                text-align: center;
                background: #f8f9fa;
            }}
            .photo-frame {{
                width: 150px;
                height: 150px;
                border-radius: 50%;
                border: 5px solid #1e3c72;
                overflow: hidden;
                margin: 0 auto;
                background: white;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            }}
            .photo-frame img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
            }}
            .photo-placeholder {{
                width: 100%;
                height: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
                font-size: 4em;
                background: #e9ecef;
            }}
            .info-section {{
                padding: 25px;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #eee;
            }}
            .info-row:last-child {{
                border-bottom: none;
            }}
            .info-label {{
                color: #666;
                font-weight: 500;
            }}
            .info-value {{
                color: #333;
                font-weight: 600;
            }}
            .status-present {{
                color: #28a745;
                font-weight: bold;
            }}
            .card-footer {{
                background: #f8f9fa;
                padding: 15px;
                text-align: center;
                color: #666;
                font-size: 0.8em;
            }}
            .qr-badge {{
                background: #28a745;
                color: white;
                padding: 8px 20px;
                border-radius: 20px;
                display: inline-block;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="id-card">
            <div class="card-header">
                <h1>🎓 Smart Attendance</h1>
                <p>Student Identity Card</p>
            </div>
            
            <div class="photo-section">
                <div class="photo-frame">
    """
    
    if student_image:
        html += f'<img src="{student_image}" alt="{student_name}">'
    else:
        html += '<div class="photo-placeholder">👤</div>'
    
    html += f"""
                </div>
            </div>
            
            <div class="info-section">
                <div class="info-row">
                    <span class="info-label">Name</span>
                    <span class="info-value">{student_name}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Student ID</span>
                    <span class="info-value">#{student_id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Year</span>
                    <span class="info-value">{student_year}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Branch</span>
                    <span class="info-value">{student_branch}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Attendance</span>
                    <span class="info-value status-present">{stats.get('percentage', 0)}%</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Days Present</span>
                    <span class="info-value">{stats.get('present', 0)} / {stats.get('total_working_days', 0)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Date</span>
                    <span class="info-value">{current_date}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Time</span>
                    <span class="info-value">{current_time}</span>
                </div>
            </div>
            
            <div class="card-footer">
                <p>Verified by Smart Attendance System</p>
                <div class="qr-badge">✓ Attendance Verified</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

# Internal function for student stats (to avoid duplicate code)
def student_stats_working_days_internal(student_id, branch=''):
    """Internal function to get student stats
    
    Uses branch-specific working days only. No fallback to generic entries.
    """
    attendance_dir = os.path.join(PROJECT_ROOT, 'Attendance')
    present = 0
    
    working_days = load_working_days()
    all_working_days = []
    
    # Filter by branch if provided - must end with branch
    if branch:
        for month_key, days in working_days.items():
            if month_key.endswith(branch):
                all_working_days.extend(days)
    else:
        # If no branch specified, only get entries without branch suffix (backward compat)
        for month_key, days in working_days.items():
            if not any(k.endswith(branch_suffix) for branch_suffix in ['-CSE', '-IT', '-ECE', '-EEE', '-ME', '-CE']):
                all_working_days.extend(days)
    
    # Remove duplicates while preserving order
    all_working_days = list(dict.fromkeys(all_working_days))
    total_working_days = len(all_working_days)
    
    if os.path.exists(attendance_dir) and total_working_days > 0:
        try:
            csv_files = [f for f in os.listdir(attendance_dir) if f.endswith('.csv')]
            
            for csv_file in csv_files:
                date_str = csv_file.replace('Attendance_', '').replace('.csv', '')
                if date_str in all_working_days:
                    file_path = os.path.join(attendance_dir, csv_file)
                    try:
                        df = pd.read_csv(file_path)
                        df.columns = df.columns.str.strip()
                        df['Id'] = df['Id'].astype(str)
                        if str(student_id) in df['Id'].values:
                            present += 1
                    except:
                        continue
        except:
            pass
    
    percentage = round((present / total_working_days) * 100, 1) if total_working_days > 0 else 0
    
    return jsonify({
        'status': 'success',
        'present': present,
        'total_working_days': total_working_days,
        'percentage': percentage
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    # Note: Avoid emojis here to prevent Windows console encoding issues
    print("Smart Attendance System")
    print("="*50)
    print("\nOpen your browser and go to:")
    print("   http://127.0.0.1:5000")
    print("\nLogin Credentials:")
    print("   Teacher: username='teacher', password='teacher123'")
    print("   Students: username='studentname', password='ID'")
    print("   Example: username='gana', password='4224'")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)