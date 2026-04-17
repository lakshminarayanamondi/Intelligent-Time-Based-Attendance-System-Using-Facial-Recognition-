/**
 * Smart Attendance System - Master JavaScript
 */

// ===============================================
// GLOBAL VARIABLES
// ===============================================
let currentUser = { present: 0, total: 0 };
let currentWorkingDays = [];
let calendarData = null;
let currentRiskData = []; // For Excel/PDF export

// ===============================================
// INITIALIZATION & UTILS
// ===============================================
document.addEventListener('DOMContentLoaded', () => {
    loadThemePreference();
    
    // Auto-run Teacher functions if on Teacher page
    if (document.getElementById('teacher-dash')) {
        loadAnalytics();
        loadLeaves();
        const now = new Date();
        const monthEl = document.getElementById('calendar-month');
        const yearEl = document.getElementById('calendar-year');
        if(monthEl) monthEl.value = now.getMonth() + 1;
        if(yearEl) yearEl.value = now.getFullYear();
        loadCalendar();
    }
});

function toggleDarkMode() {
    const isDark = document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', isDark);
    const btn = document.getElementById('theme-btn');
    if(btn) btn.innerText = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
}

function loadThemePreference() {
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        const btn = document.getElementById('theme-btn');
        if(btn) btn.innerText = '☀️ Light Mode';
    }
}

function logout() {
    localStorage.clear();
    sessionStorage.clear();
    window.location.href = '/';
}

// ===============================================
// 👨‍🏫 TEACHER: ACTION BUTTONS (REGISTER, TRAIN, CAMERA)
// ===============================================
async function registerStudent() {
    const id = document.getElementById('reg-id').value;
    const name = document.getElementById('reg-name').value;
    const year = document.getElementById('reg-year').value;
    const branch = document.getElementById('reg-branch').value;
    if(!id || !name || !year || !branch) return alert("Fill all fields!");
    
    try {
        const res = await fetch('/start_register', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, name, year, branch}) });
        const data = await res.json();
        alert(data.message);
    } catch(e) { alert("Registration Error"); }
}

async function trainModel() { 
    try {
        const res = await fetch('/start_train', {method: 'POST'});
        const data = await res.json();
        alert(data.message);
    } catch(e) { alert("Training Error"); }
}

async function startAttendance() { 
    try {
        const response = await fetch('/start_attendance', {method: 'POST'});
        const data = await response.json();
        alert(data.status === 'success' ? "✅ " + data.message : "❌ Error: " + data.message);
    } catch (error) {
        alert("Failed to start attendance. Is the Flask server running?");
    }
}

async function uploadAttendanceImage() {
    const fileInput = document.getElementById('attendance-file');
    const statusEl = document.getElementById('upload-status');
    if (!fileInput || !fileInput.files.length) return alert("Please select an image file first!");

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    statusEl.innerText = "⏳ Processing image...";
    statusEl.style.color = "#d97706";

    try {
        const res = await fetch('/upload_attendance', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.status === 'success') {
            statusEl.innerText = "✅ Attendance marked!";
            statusEl.style.color = "#28a745";
            loadAnalytics();
        } else {
            statusEl.innerText = "❌ Error: " + data.message;
            statusEl.style.color = "#dc3545";
        }
    } catch (error) {
        statusEl.innerText = "❌ Failed to upload. Server error.";
        statusEl.style.color = "#dc3545";
    }
}

// ===============================================
// 👨‍🏫 TEACHER: LEAVE MANAGEMENT
// ===============================================
async function loadLeaves() {
    const tbody = document.getElementById('leave-table-body');
    if(!tbody) return;

    try {
        const res = await fetch('/get_all_leaves');
        const data = await res.json();
        
        if (data.status === 'success' && data.leaves.length > 0) {
            let html = '';
            data.leaves.reverse().forEach((leave, index) => {
                let actionHtml = '';
                if (leave.Status === 'Pending') {
                    actionHtml = `
                        <button onclick="updateLeaveStatus(${data.leaves.length - 1 - index}, 'Approved')" class="btn-success" style="padding: 5px 10px; font-size: 0.8em; width: auto; margin-right: 5px;">Approve</button>
                        <button onclick="updateLeaveStatus(${data.leaves.length - 1 - index}, 'Rejected')" class="btn-danger" style="padding: 5px 10px; font-size: 0.8em; width: auto;">Reject</button>
                    `;
                } else {
                    actionHtml = `<span class="badge-status status-${leave.Status.toLowerCase()}">${leave.Status}</span>`;
                }
                
                html += `
                    <tr>
                        <td><strong>${leave.ID}</strong></td>
                        <td>${leave.Start_Date}</td>
                        <td>${leave.End_Date}</td>
                        <td>${leave.Reason}</td>
                        <td style="font-size: 0.85em; color: #888;">${leave.Applied_On}</td>
                        <td>${actionHtml}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } else {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #666;">No leave requests found.</td></tr>';
        }
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: red;">Error loading requests.</td></tr>';
    }
}

async function updateLeaveStatus(rowIndex, newStatus) {
    try {
        const res = await fetch('/update_leave_status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ row_index: rowIndex, status: newStatus })
        });
        const data = await res.json();
        if (data.status === 'success') {
            loadLeaves(); 
        } else {
            alert("Error updating status: " + data.message);
        }
    } catch (e) {
        alert("Failed to communicate with server.");
    }
}

// ===============================================
// 👨‍🏫 TEACHER: PREDICTIVE ANALYTICS & EXPORTS
// ===============================================
async function loadRiskAnalysis() {
    const year = document.getElementById('filter-year').value;
    const branch = document.getElementById('filter-branch').value;

    document.getElementById('analytics-loading').style.display = 'block';
    document.getElementById('analytics-loading').innerHTML = '🤖 Fetching student list...';
    document.getElementById('risk-alerts').style.display = 'none';
    currentRiskData = []; 

    try {
        const res = await fetch('/get_all_students');
        if (!res.ok) throw new Error("Failed to connect to backend");
        
        const data = await res.json();
        let students = data.students || [];

        if (year) students = students.filter(s => s.year === year);
        if (branch) students = students.filter(s => s.branch === branch);

        if (students.length === 0) {
            document.getElementById('high-risk-list').innerHTML = '<span style="color:#666;">No students found.</span>';
            document.getElementById('medium-risk-list').innerHTML = '<span style="color:#666;">No students found.</span>';
            document.getElementById('low-risk-list').innerHTML = '<span style="color:#666;">No students found.</span>';
            document.getElementById('analytics-loading').style.display = 'none';
            document.getElementById('risk-alerts').style.display = 'block';
            return;
        }

        // Sequential Fetch to prevent server crash
        for (let i = 0; i < students.length; i++) {
            const student = students[i];
            document.getElementById('analytics-loading').innerHTML = `🤖 Analyzing student ${i + 1} of ${students.length}...`;
            
            try {
                const statRes = await fetch('/student_stats_working_days', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: student.id, year: '', month: '', branch: student.branch})
                });
                
                const statData = await statRes.json();
                currentRiskData.push({ 
                    ...student, 
                    percentage: statData.percentage || 0, 
                    present: statData.present || 0, 
                    total: statData.total_working_days || 0 
                });
            } catch (statError) {
                console.error(`Skipping student ${student.id} due to error`);
            }
        }

        let highHTML = '', medHTML = '', lowHTML = '';

        currentRiskData.forEach(s => {
            const text = `<strong>${s.name}</strong> (${s.id}) - ${s.branch} | ${s.percentage}% (${s.present}/${s.total} days)`;
            if (s.percentage < 60) {
                highHTML += `<div style="padding: 5px 0;">${text}</div>`;
            } else if (s.percentage <= 75) {
                medHTML += `<div style="padding: 5px 0;">${text}</div>`;
            } else {
                lowHTML += `<div style="padding: 5px 0;">${text}</div>`;
            }
        });

        document.getElementById('high-risk-list').innerHTML = highHTML || '<span style="color:#666;">No students in this category.</span>';
        document.getElementById('medium-risk-list').innerHTML = medHTML || '<span style="color:#666;">No students in this category.</span>';
        document.getElementById('low-risk-list').innerHTML = lowHTML || '<span style="color:#666;">No students in this category.</span>';

        document.getElementById('analytics-loading').style.display = 'none';
        document.getElementById('risk-alerts').style.display = 'block';

    } catch (e) {
        console.error("Risk Analysis Error:", e);
        alert('Error loading risk analysis.');
        document.getElementById('analytics-loading').style.display = 'none';
    }
}

function exportToExcel() {
    if (!currentRiskData || currentRiskData.length === 0) {
        alert('Please click "Analyze Risk" first to generate the data!');
        return;
    }

    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Student ID,Name,Year,Branch,Attendance %,Days Present,Total Working Days,Risk Level\n";

    currentRiskData.forEach(s => {
        let risk = s.percentage < 60 ? 'High' : (s.percentage <= 75 ? 'Medium' : 'Safe');
        let row = `${s.id},${s.name},${s.year},${s.branch},${s.percentage}%,${s.present},${s.total},${risk}`;
        csvContent += row + "\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Risk_Report_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function exportToPDF() {
    if (!currentRiskData || currentRiskData.length === 0) {
        alert('Please click "Analyze Risk" first to generate the data!');
        return;
    }

    let printWindow = window.open('', '', 'height=800,width=1000');
    printWindow.document.write('<html><head><title>Attendance Risk Report</title>');
    printWindow.document.write(`
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #4e54c8; color: white; }
            .high { color: #d32f2f; font-weight: bold; }
            .med { color: #f57c00; font-weight: bold; }
            .low { color: #388e3c; }
            h2 { color: #333; }
        </style>
    `);
    printWindow.document.write('</head><body>');
    printWindow.document.write(`<h2>🎓 Smart Attendance - Risk Analysis Report</h2>`);
    printWindow.document.write(`<p>Generated on: ${new Date().toLocaleString()}</p>`);
    printWindow.document.write('<table><tr><th>Student ID</th><th>Name</th><th>Branch</th><th>Year</th><th>Attendance</th><th>Status</th></tr>');

    currentRiskData.forEach(s => {
        let riskClass = s.percentage < 60 ? 'high' : (s.percentage <= 75 ? 'med' : 'low');
        let riskText = s.percentage < 60 ? 'High Risk' : (s.percentage <= 75 ? 'Medium Risk' : 'On Track');
        printWindow.document.write(`<tr>
            <td>${s.id}</td>
            <td>${s.name}</td>
            <td>${s.branch}</td>
            <td>${s.year}</td>
            <td class="${riskClass}">${s.percentage}% (${s.present}/${s.total})</td>
            <td class="${riskClass}">${riskText}</td>
        </tr>`);
    });

    printWindow.document.write('</table></body></html>');
    printWindow.document.close();
    
    setTimeout(() => {
        printWindow.print();
    }, 500);
}

async function loadAnalytics() {
    const canvas = document.getElementById('attendanceChart');
    if (!canvas) return; 

    try {
        const res = await fetch('/get_analytics');
        const result = await res.json();
        
        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(result.data),
                datasets: [{
                    label: 'Students Present',
                    data: Object.values(result.data),
                    backgroundColor: '#4e54c8',
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    } catch (error) {
        console.error('Error loading analytics chart:', error);
    }
}

// ===============================================
// 👨‍🏫 TEACHER: CALENDAR LOGIC
// ===============================================
async function loadCalendar() {
    const yearEl = document.getElementById('calendar-year');
    const monthEl = document.getElementById('calendar-month');
    if(!yearEl || !monthEl) return;
    
    const year = parseInt(yearEl.value);
    const month = parseInt(monthEl.value);
    const yearSelect = document.getElementById('calendar-year-select').value;
    const branch = document.getElementById('calendar-branch-select').value;
    
    if (!year || !month) return;
    try {
        const res = await fetch(`/get_working_days?year=${year}&month=${month}&branch=${branch}&year_select=${yearSelect}`);
        const data = await res.json();
        if (data.status === 'success') {
            currentWorkingDays = [...(data.working_days || [])];
            calendarData = data.calendar;
            renderCalendar(data.calendar, currentWorkingDays, year, month);
            document.getElementById('working-days-summary').innerHTML = `<strong>Total Working Days: ${currentWorkingDays.length}</strong>`;
        }
    } catch (e) { console.error(e); }
}

function renderCalendar(calendarData, workingDays, year, month) {
    const container = document.getElementById('calendar-display');
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    let html = '<div class="calendar-header">';
    dayNames.forEach(day => html += `<div class="day-header ${day === 'Sun' ? 'sunday' : ''}">${day}</div>`);
    html += '</div><div class="calendar-body">';
    
    calendarData.forEach(week => {
        html += '<div class="calendar-week">';
        week.forEach((day, index) => {
            if (day === 0) {
                html += '<div class="calendar-day empty"></div>';
            } else {
                const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const isSunday = index === 0;
                const isWorking = workingDays.includes(dateStr);
                const isSelectable = !isSunday;
                html += `<div class="calendar-day ${isSunday ? 'sunday' : ''} ${isWorking ? 'working' : ''} ${isSelectable ? 'selectable' : ''}" 
                          ${isSelectable ? `onclick="toggleDate('${dateStr}')"` : ''}>
                    <span class="day-number">${day}</span>
                    ${isWorking ? '<span class="check">✓</span>' : ''}
                </div>`;
            }
        });
        html += '</div>';
    });
    container.innerHTML = html + '</div>';
}

function toggleDate(dateStr) {
    const index = currentWorkingDays.indexOf(dateStr);
    if (index > -1) currentWorkingDays.splice(index, 1);
    else currentWorkingDays.push(dateStr);
    const year = parseInt(document.getElementById('calendar-year').value);
    const month = parseInt(document.getElementById('calendar-month').value);
    renderCalendar(calendarData, currentWorkingDays, year, month);
    document.getElementById('working-days-summary').innerHTML = `<strong>Total Working Days: ${currentWorkingDays.length}</strong>`;
}

async function saveWorkingDays() {
    const year = parseInt(document.getElementById('calendar-year').value);
    const month = parseInt(document.getElementById('calendar-month').value);
    const yearSelect = document.getElementById('calendar-year-select').value;
    const branch = document.getElementById('calendar-branch-select').value;
    
    try {
        const res = await fetch('/set_working_days', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ year, month, year_select: yearSelect, branch, days: currentWorkingDays })
        });
        const data = await res.json();
        alert(data.message);
    } catch (e) { alert('Failed to save working days'); }
}


// ===============================================
// 👨‍🎓 STUDENT DASHBOARD FUNCTIONS
// ===============================================
async function loadStudentStats(id) {
    const res = await fetch('/student_stats', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id})
    });
    const data = await res.json();
    
    const percEl = document.getElementById('stu-percentage');
    const presEl = document.getElementById('stu-present');
    const totEl = document.getElementById('stu-total');
    
    if (percEl) percEl.innerText = data.percentage + "%";
    if (presEl) presEl.innerText = data.present;
    if (totEl) totEl.innerText = data.total;
    
    currentUser.present = data.present;
    currentUser.total = data.total;
}

function calculateProjection() {
    const targetEl = document.getElementById('target-percent');
    if (!targetEl) return;
    
    const target = parseFloat(targetEl.value);
    const present = parseInt(document.getElementById('stu-present').innerText) || currentUser.present || 0;
    const total = parseInt(document.getElementById('stu-total').innerText) || currentUser.total || 0;
    
    if (total === 0) {
        document.getElementById('calc-result').innerText = "No classes held yet.";
        return;
    }
    
    const currentPercent = (present / total) * 100;
    
    if (currentPercent >= target) {
        const canMiss = Math.floor((present * 100 / target) - total);
        document.getElementById('calc-result').innerHTML = 
            `<span style="color: #28a745;">Great! You are on track. You can miss the next ${canMiss} classes and still maintain ${target}%.</span>`;
    } else {
        const needed = Math.ceil(((target * total) - (100 * present)) / (100 - target));
        document.getElementById('calc-result').innerHTML = 
            `<span style="color: #dc3545;">Warning! You need to attend the next ${needed} classes consecutively to reach ${target}%.</span>`;
    }
}