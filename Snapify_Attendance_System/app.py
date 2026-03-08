import sqlite3
import db_manager
from datetime import datetime
import csv
import io
import os
import json
import sys
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response, jsonify

app = Flask(__name__)

# ── Parse teacher email from CLI args ──
parser = argparse.ArgumentParser(description='Attendance Dashboard')
parser.add_argument('--teacher', type=str, default='', help='Teacher email for data isolation')
args, _ = parser.parse_known_args()
TEACHER_EMAIL = args.teacher

# ── Database migration: ensure table has correct schema ──
db_manager.init_db()

@app.route('/')
def index():
    # Get all unique class names for the dropdown (filtered by teacher)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT class_name FROM attendance WHERE class_name != '' AND teacher_email = ? ORDER BY class_name", (TEACHER_EMAIL,))
    classes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return render_template('index.html', selected_date='', selected_class='', classes=classes, no_data=False, teacher_email=TEACHER_EMAIL)

@app.route('/attendance', methods=['POST'])
def attendance():
    selected_date = request.form.get('selected_date')
    selected_class = request.form.get('selected_class', '')
    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    formatted_date = selected_date_obj.strftime('%Y-%m-%d')

    conn = db_manager.get_connection()
    cursor = conn.cursor()

    # Get all unique class names for the dropdown (filtered by teacher)
    cursor.execute("SELECT DISTINCT class_name FROM attendance WHERE class_name != '' AND teacher_email = ? ORDER BY class_name", (TEACHER_EMAIL,))
    classes = [row[0] for row in cursor.fetchall()]

    # Filter by date, class, and teacher
    if selected_class and selected_class != 'All':
        cursor.execute("SELECT roll_number, name, class_name, time, date FROM attendance WHERE date = ? AND class_name = ? AND teacher_email = ? ORDER BY name",
                       (formatted_date, selected_class, TEACHER_EMAIL))
    else:
        cursor.execute("SELECT roll_number, name, class_name, time, date FROM attendance WHERE date = ? AND teacher_email = ? ORDER BY class_name, name",
                       (formatted_date, TEACHER_EMAIL))

    attendance_data = cursor.fetchall()
    conn.close()

    if not attendance_data:
        return render_template('index.html', selected_date=selected_date, selected_class=selected_class,
                               classes=classes, no_data=True, teacher_email=TEACHER_EMAIL)

    return render_template('index.html', selected_date=selected_date, selected_class=selected_class,
                           classes=classes, attendance_data=attendance_data, teacher_email=TEACHER_EMAIL)

@app.route('/delete_attendance', methods=['POST'])
def delete_attendance():
    selected_date = request.form.get('selected_date')
    selected_class = request.form.get('selected_class', '')
    if not selected_date:
        return "No date selected", 400

    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    formatted_date = selected_date_obj.strftime('%Y-%m-%d')

    conn = db_manager.get_connection()
    cursor = conn.cursor()

    # Filter deletion by date, class, and teacher
    if selected_class and selected_class != 'All':
        cursor.execute("DELETE FROM attendance WHERE date = ? AND class_name = ? AND teacher_email = ?",
                       (formatted_date, selected_class, TEACHER_EMAIL))
    else:
        cursor.execute("DELETE FROM attendance WHERE date = ? AND teacher_email = ?",
                       (formatted_date, TEACHER_EMAIL))
    
    conn.commit()

    # Get all unique class names for the dropdown (filtered by teacher)
    cursor.execute("SELECT DISTINCT class_name FROM attendance WHERE class_name != '' AND teacher_email = ? ORDER BY class_name", (TEACHER_EMAIL,))
    classes = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template('index.html', selected_date=selected_date, selected_class=selected_class,
                           classes=classes, no_data=True, teacher_email=TEACHER_EMAIL)

@app.route('/download_csv', methods=['POST'])
def download_csv():
    selected_date = request.form.get('selected_date')
    selected_class = request.form.get('selected_class', '')
    if not selected_date:
        return "No date selected", 400

    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    formatted_date = selected_date_obj.strftime('%Y-%m-%d')

    conn = db_manager.get_connection()
    cursor = conn.cursor()

    # Get all registered students for this teacher
    cursor.execute("SELECT roll_number, name FROM students WHERE teacher_email = ? ORDER BY roll_number", (TEACHER_EMAIL,))
    all_students = cursor.fetchall()

    # Get attendance records for this date and class (if specified)
    if selected_class and selected_class != 'All':
        cursor.execute("SELECT roll_number, class_name, time, date FROM attendance WHERE date = ? AND class_name = ? AND teacher_email = ?",
                       (formatted_date, selected_class, TEACHER_EMAIL))
    else:
        cursor.execute("SELECT roll_number, class_name, time, date FROM attendance WHERE date = ? AND teacher_email = ?",
                       (formatted_date, TEACHER_EMAIL))

    attendance_records = {row[0]: row for row in cursor.fetchall()}
    conn.close()

    # Process records
    processed_data = []
    
    for student in all_students:
        roll_number, name = student
        
        # Check if student was present
        if roll_number in attendance_records:
            # They are present
            att_record = attendance_records[roll_number]
            curr_class_name = att_record[1]
            curr_time = att_record[2]
            curr_date = att_record[3]
            status = 'P'
        else:
            # They are absent
            curr_class_name = selected_class if selected_class and selected_class != 'All' else 'All'
            curr_time = '—'
            curr_date = formatted_date
            status = 'A'
            
        processed_data.append((roll_number, name, curr_class_name, curr_time, curr_date, status))

    # Sort: Present ('P') first, then Absent ('A')
    processed_data.sort(key=lambda x: (x[5] != 'P', x[1]))

    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Roll Number', 'Name', 'Class/Period', 'Time', 'Date', 'Status'])
    for row in processed_data:
        writer.writerow(row)

    csv_content = output.getvalue()
    output.close()

    class_suffix = f"_{selected_class}" if selected_class and selected_class != 'All' else ""
    filename = f"attendance_{formatted_date}{class_suffix}.csv"
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/email_config', methods=['GET'])
def get_email_config():
    """Return saved email sender credentials (if any)."""
    config_path = os.path.join(os.path.dirname(__file__), 'email_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            data = json.load(f)
            # Default sender to teacher email
            if not data.get('sender_email'):
                data['sender_email'] = TEACHER_EMAIL
            return jsonify(data)
    return jsonify({'sender_email': TEACHER_EMAIL, 'sender_password': ''})


@app.route('/send_emails', methods=['POST'])
def send_emails():
    """Bulk email: send Present/Absent status to every registered student."""
    date            = request.form.get('date', '').strip()
    class_name      = request.form.get('class_name', '').strip()
    sender_email    = request.form.get('sender_email', '').strip()
    sender_password = request.form.get('sender_password', '').strip()

    if not date:
        return jsonify({'error': 'Date is required.'}), 400
    if not sender_email:
        return jsonify({'error': 'Sender Gmail is required.'}), 400
    if not sender_password:
        return jsonify({'error': 'Gmail App Password is required.'}), 400

    conn   = db_manager.get_connection()
    cursor = conn.cursor()

    # All registered students with emails (filtered by teacher)
    cursor.execute("SELECT roll_number, name, email FROM students WHERE email IS NOT NULL AND email != '' AND teacher_email = ?", (TEACHER_EMAIL,))
    all_students = cursor.fetchall()  # [(roll, name, email), ...]

    # Who was present for this date + class?
    if class_name and class_name != 'All':
        cursor.execute(
            "SELECT roll_number FROM attendance WHERE date = ? AND class_name = ? AND teacher_email = ?",
            (date, class_name, TEACHER_EMAIL)
        )
    else:
        cursor.execute("SELECT roll_number FROM attendance WHERE date = ? AND teacher_email = ?", (date, TEACHER_EMAIL))
    present_rolls = {row[0] for row in cursor.fetchall()}
    conn.close()

    if not all_students:
        return jsonify({'error': 'No registered students with email addresses found.'}), 404

    period_label = class_name if class_name and class_name != 'All' else 'All Periods'

    # ── Open SMTP connection once ─────────────────────────────────────────
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(sender_email, sender_password)
        # ✅ Save credentials so the user doesn't have to re-enter them
        config_path = os.path.join(os.path.dirname(__file__), 'email_config.json')
        with open(config_path, 'w') as f:
            json.dump({'sender_email': sender_email, 'sender_password': sender_password}, f)
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            'total': 0, 'sent': 0, 'failed': 0,
            'details': [{'name': '', 'email': '', 'status': 'error',
                         'message': '❌ Gmail authentication failed. Make sure you are using an App Password '
                                    '(not your regular password) and that 2-Step Verification is enabled.'}]
        }), 200
    except Exception as e:
        return jsonify({
            'total': 0, 'sent': 0, 'failed': 0,
            'details': [{'name': '', 'email': '', 'status': 'error', 'message': str(e)}]
        }), 200

    # ── Send one email per student ────────────────────────────────────────
    details = []
    sent = failed = 0

    for roll, name, email in all_students:
        is_present = roll in present_rolls
        status_word  = 'Present ✅' if is_present else 'Absent ❌'
        status_color = '#2ecc71'    if is_present else '#e74c3c'
        bg_accent    = 'rgba(46,204,113,0.08)' if is_present else 'rgba(231,76,60,0.08)'

        html_body = f"""
        <div style="font-family:Inter,Arial,sans-serif;background:#0f1117;padding:32px;max-width:560px;margin:auto;">
          <h2 style="color:#6c63ff;margin-bottom:4px;">📊 Attendance Report</h2>
          <p style="color:#8b8da3;margin-top:0;font-size:13px;">
            {date} &nbsp;·&nbsp; {period_label}
          </p>
          <div style="background:{bg_accent};border:1px solid {status_color}33;
                      border-radius:12px;padding:24px 28px;margin:20px 0;text-align:center;">
            <div style="font-size:13px;color:#8b8da3;margin-bottom:6px;">Hello, <strong style="color:#e8e8f0;">{name}</strong></div>
            <div style="font-size:38px;margin:8px 0;">{('✅' if is_present else '❌')}</div>
            <div style="font-size:22px;font-weight:700;color:{status_color};">{status_word}</div>
            <div style="font-size:13px;color:#8b8da3;margin-top:8px;">
              Your attendance has been {'recorded' if is_present else 'marked as absent'} for
              <strong style="color:#e8e8f0;">{period_label}</strong> on <strong style="color:#e8e8f0;">{date}</strong>.
            </div>
          </div>
          <p style="color:#8b8da3;font-size:11px;margin-top:20px;">
            Roll No: {roll} &nbsp;·&nbsp; Generated by Snapify Attendance System
          </p>
        </div>
        """

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'Attendance – {date} | {period_label} | {status_word}'
            msg['From']    = sender_email
            msg['To']      = email
            msg.attach(MIMEText(html_body, 'html'))
            server.sendmail(sender_email, [email], msg.as_string())
            details.append({'name': name, 'email': email,
                            'status': 'present' if is_present else 'absent',
                            'message': f'Email sent successfully'})
            sent += 1
        except Exception as e:
            details.append({'name': name, 'email': email, 'status': 'error', 'message': str(e)})
            failed += 1

    server.quit()

    return jsonify({'total': len(all_students), 'sent': sent, 'failed': failed, 'details': details})


# ── Email Report ────────────────────────────────────────────────────────────
@app.route('/send_email_report', methods=['POST'])
def send_email_report():
    selected_date  = request.form.get('selected_date', '')
    selected_class = request.form.get('selected_class', '')
    recipient      = request.form.get('recipient_email', '').strip()

    if not selected_date:
        return jsonify({'error': 'No date selected'}), 400
    if not recipient:
        return jsonify({'error': 'No recipient email provided'}), 400

    sender   = os.environ.get('SMTP_SENDER', '')
    password = os.environ.get('SMTP_PASSWORD', '')
    if not sender or not password:
        return jsonify({'error': 'SMTP credentials not configured (set SMTP_SENDER and SMTP_PASSWORD env vars)'}), 500

    # ── Query attendance (filtered by teacher) ──
    formatted_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')
    conn   = db_manager.get_connection()
    cursor = conn.cursor()
    if selected_class and selected_class != 'All':
        cursor.execute(
            "SELECT roll_number, name, class_name, time, date FROM attendance "
            "WHERE date = ? AND class_name = ? AND teacher_email = ? ORDER BY name",
            (formatted_date, selected_class, TEACHER_EMAIL)
        )
    else:
        cursor.execute(
            "SELECT roll_number, name, class_name, time, date FROM attendance "
            "WHERE date = ? AND teacher_email = ? ORDER BY class_name, name",
            (formatted_date, TEACHER_EMAIL)
        )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({'error': 'No attendance data for the selected filters'}), 404

    # ── Build HTML email body ─────────────────────────────────────────────
    period_label = selected_class if selected_class and selected_class != 'All' else 'All Periods'
    table_rows   = ''.join(
        f'<tr style="background:{ "#1e2130" if i % 2 == 0 else "#181c2b" };">' 
        f'<td style="padding:10px 14px;">{i+1}</td>'
        f'<td style="padding:10px 14px;"><strong>{r[0]}</strong></td>'
        f'<td style="padding:10px 14px;">{r[1]}</td>'
        f'<td style="padding:10px 14px;">{r[2]}</td>'
        f'<td style="padding:10px 14px;">{r[3]}</td>'
        f'<td style="padding:10px 14px;">{r[4]}</td>'
        '</tr>'
        for i, r in enumerate(rows)
    )

    html_body = f"""
    <div style="font-family:Inter,Arial,sans-serif;background:#0f1117;padding:32px;">
      <h2 style="color:#6c63ff;margin-bottom:4px;">📊 Attendance Report</h2>
      <p style="color:#8b8da3;margin-top:0;">
        Date: <strong style="color:#e8e8f0;">{formatted_date}</strong> &nbsp;·&nbsp;
        Period: <strong style="color:#e8e8f0;">{period_label}</strong>
      </p>
      <table style="width:100%;border-collapse:collapse;background:#1a1d27;border-radius:10px;overflow:hidden;">
        <thead>
          <tr style="background:rgba(108,99,255,0.15);">
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">#</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Roll No</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Name</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Class / Period</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Time</th>
            <th style="padding:12px 14px;color:#6c63ff;text-align:left;font-size:12px;text-transform:uppercase;">Date</th>
          </tr>
        </thead>
        <tbody style="color:#e8e8f0;font-size:14px;">
          {table_rows}
        </tbody>
      </table>
      <p style="color:#8b8da3;font-size:12px;margin-top:20px;">
        Total students present: <strong style="color:#6c63ff;">{len(rows)}</strong><br>
        Generated by Snapify Attendance System
      </p>
    </div>
    """

    # ── Send via Gmail SMTP ───────────────────────────────────────────────
    try:
        msg                     = MIMEMultipart('alternative')
        msg['Subject']          = f'Attendance Report – {formatted_date} ({period_label})'
        msg['From']             = sender
        msg['To']               = recipient
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())

        return jsonify({'success': True, 'message': f'Report sent to {recipient}'})
    except smtplib.SMTPAuthenticationError:
        return jsonify({'error': 'SMTP authentication failed. Check SMTP_SENDER and SMTP_PASSWORD.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Student List ────────────────────────────────────────────────────────────
@app.route('/students')
def students_list():
    """Show all registered students with optional search (filtered by teacher)."""
    search = request.args.get('q', '').strip()

    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")

    if search:
        like = f'%{search}%'
        cursor.execute(
            "SELECT roll_number, name, phone, email FROM students "
            "WHERE teacher_email = ? AND (roll_number LIKE ? OR name LIKE ? OR phone LIKE ? OR email LIKE ?) "
            "ORDER BY roll_number",
            (TEACHER_EMAIL, like, like, like, like)
        )
    else:
        cursor.execute("SELECT roll_number, name, phone, email FROM students WHERE teacher_email = ? ORDER BY roll_number", (TEACHER_EMAIL,))

    students = cursor.fetchall()
    conn.close()
    return render_template('students.html', students=students, search=search, teacher_email=TEACHER_EMAIL)

# ── Client-Server API Endpoints ──────────────────────────────────────────────
import numpy as np
import cv2

recognizers = {}

def get_recognizer(teacher, class_name):
    key = (teacher, class_name)
    if key not in recognizers:
        from attendance_taker import Face_Recognizer
        rec = Face_Recognizer(class_name=class_name, teacher_email=teacher)
        rec.get_face_database() # Load CSV
        recognizers[key] = rec
    return recognizers[key]

@app.route('/api/login', methods=['POST'])
def api_login():
    email = request.form.get('email')
    password = request.form.get('password')
    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400
    
    # Check backwards compatible teachers.json
    project_dir = os.path.dirname(os.path.abspath(__file__))
    teachers_file = os.path.join(project_dir, 'teachers.json')
    try:
        with open(teachers_file, 'r') as f:
            teachers = json.load(f)
        if email in teachers and teachers[email].get('password') == password:
            return jsonify({'success': True})
    except Exception:
        pass
    
    # Check sqlite
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers WHERE email = ? AND password_hash = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/signup', methods=['POST'])
def api_signup():
    email = request.form.get('email')
    password = request.form.get('password')
    name = request.form.get('name', '')
    
    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400
        
    # Also save to backwards compatible teachers.json
    project_dir = os.path.dirname(os.path.abspath(__file__))
    teachers_file = os.path.join(project_dir, 'teachers.json')
    teachers = {}
    if os.path.exists(teachers_file):
        try:
            with open(teachers_file, 'r') as f:
                teachers = json.load(f)
        except Exception: pass
        
    if email in teachers:
        return jsonify({'error': 'Email already exists'}), 400
        
    teachers[email] = {'name': name, 'password': password}
    try:
        with open(teachers_file, 'w') as f:
            json.dump(teachers, f)
    except Exception: pass
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teachers WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Email already exists'}), 400
        
    cursor.execute("INSERT INTO teachers (email, password_hash) VALUES (?, ?)", (email, password))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/load_student', methods=['POST'])
def api_load_student():
    teacher_email = request.form.get('teacher_email')
    roll_number = request.form.get('roll_number')
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, email FROM students WHERE roll_number = ? AND teacher_email = ?", (roll_number, teacher_email))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({'success': True, 'name': row[0], 'phone': row[1], 'email': row[2]})
    else:
        return jsonify({'error': 'Student not found'}), 404

@app.route('/api/delete_student', methods=['POST'])
def api_delete_student():
    teacher_email = request.form.get('teacher_email')
    roll_number = request.form.get('roll_number')
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE roll_number = ? AND teacher_email = ?", (roll_number, teacher_email))
    conn.commit()
    conn.close()
    
    # Try to delete face folder
    base_path = f"data/data_faces_from_camera/{teacher_email}"
    if os.path.exists(base_path):
        for folder in os.listdir(base_path):
            parts = folder.split('_')
            if len(parts) >= 3 and parts[2] == str(roll_number):
                import shutil
                shutil.rmtree(os.path.join(base_path, folder))
                break
                
    return jsonify({'success': True})

@app.route('/api/process_frame', methods=['POST'])
def api_process_frame():
    teacher_email = request.form.get('teacher_email')
    class_name = request.form.get('class_name', 'General')
    frame_file = request.files.get('frame')
    
    if not teacher_email or not frame_file:
        return jsonify({'error': 'Missing teacher_email or frame'}), 400
        
    # Read image from request
    img_bytes = frame_file.read()
    import numpy as np
    import cv2
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_rd = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img_rd is None:
        return jsonify({'error': 'Invalid image format'}), 400
        
    try:
        rec = get_recognizer(teacher_email, class_name)
        # Reset lists for new frame
        rec.current_frame_face_name_list = []
        rec.process_frame(img_rd)
        
        recognized_rolls = [name for name in rec.current_frame_face_name_list if name != "unknown"]
        recognized_names = []
        for roll in recognized_rolls:
            name = rec.roll_to_name.get(roll, roll)
            recognized_names.append(name)
            
        return jsonify({'success': True, 'recognized': recognized_names})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/video_process_attendance', methods=['POST'])
def api_video_process_attendance():
    teacher_email = request.form.get('teacher_email')
    class_name = request.form.get('class_name', 'General')
    frame_file = request.files.get('frame')
    
    if not teacher_email or not frame_file:
        return jsonify({'error': 'Missing teacher_email or frame'}), 400
        
    # Read image from request
    img_bytes = frame_file.read()
    import numpy as np
    import cv2
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_rd = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img_rd is None:
        return jsonify({'error': 'Invalid image format'}), 400
        
    try:
        rec = get_recognizer(teacher_email, class_name)
        annotated_img = rec.process_frame(img_rd)
        
        # encode to base64 jpeg
        _, buffer = cv2.imencode('.jpg', annotated_img)
        b64_str = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({'success': True, 'annotated_b64': b64_str})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/video_process_registration', methods=['POST'])
def api_video_process_registration():
    frame_file = request.files.get('frame')
    
    if not frame_file:
        return jsonify({'error': 'Missing frame'}), 400
        
    img_bytes = frame_file.read()
    import numpy as np
    import cv2
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_rd = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img_rd is None:
        return jsonify({'error': 'Invalid image format'}), 400
        
    try:
        # We need dlib which is imported in attendance_taker
        from attendance_taker import detector
        faces = detector(img_rd, 0)
        face_count = len(faces)
        out_of_range = False
        warning_text = ""
        
        if face_count > 0:
            for k, d in enumerate(faces):
                face_roi_height = (d.bottom() - d.top())
                face_roi_width = (d.right() - d.left())
                hh = int(face_roi_height / 2)
                ww = int(face_roi_width / 2)
                
                # Check if out of range for 640x480
                if (d.right() + ww) > 640 or (d.bottom() + hh > 480) or (d.left() - ww < 0) or (d.top() - hh < 0):
                    warning_text = '⚠️ OUT OF RANGE'
                    out_of_range = True
                    color = (0, 0, 255)  # Red (BGR)
                else:
                    out_of_range = False
                    warning_text = '✓ Face in range'
                    color = (255, 255, 255)  # White
                
                # Draw rectangle
                img_rd = cv2.rectangle(
                    img_rd,
                    tuple([d.left() - ww, d.top() - hh]),
                    tuple([d.right() + ww, d.bottom() + hh]),
                    color, 2
                )
        else:
            warning_text = ''
            out_of_range = False
            
        cv2.putText(img_rd, f'Faces: {face_count}', (20, 60), cv2.FONT_ITALIC, 0.8, (0, 255, 0), 1, cv2.LINE_AA)
        if warning_text:
            warning_color = (0, 0, 255) if '⚠️' in warning_text else (0, 255, 0)
            cv2.putText(img_rd, warning_text, (20, 90), cv2.FONT_ITALIC, 0.8, warning_color, 1, cv2.LINE_AA)
            
        _, buffer = cv2.imencode('.jpg', img_rd)
        b64_str = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True, 
            'annotated_b64': b64_str, 
            'faces': face_count,
            'out_of_range': out_of_range,
            'warning_text': warning_text
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/register_student', methods=['POST'])
def api_register_student():
    teacher_email = request.form.get('teacher_email')
    roll_number = request.form.get('roll_number')
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    
    if not all([teacher_email, roll_number, name, email]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    photos = request.files.getlist('photos')
    # Can optionally update student metadata over API without uploading photos
    
    # Save student to database
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")
    cursor.execute("INSERT OR REPLACE INTO students (roll_number, name, phone, email, teacher_email) VALUES (?, ?, ?, ?, ?)",
                   (roll_number, name, phone, email, teacher_email))
    conn.commit()
    conn.close()
    
    if photos and len(photos) > 0 and photos[0].filename != '':
        # Save photos
        base_path = f"data/data_faces_from_camera/{teacher_email}"
        
        # Delete old folder if exists by searching
        if os.path.exists(base_path):
            for folder in os.listdir(base_path):
                parts = folder.split('_')
                if len(parts) >= 3 and parts[2] == str(roll_number):
                    import shutil
                    shutil.rmtree(os.path.join(base_path, folder))
                    break
                    
        folder_name = f"person_1_{roll_number}_{name}"
        full_path = os.path.join(base_path, folder_name)
        os.makedirs(full_path, exist_ok=True)
        
        # Save uploaded files
        for idx, photo in enumerate(photos):
            filename = f"img_face_{idx}.jpg"
            photo.save(os.path.join(full_path, filename))
            
        # Trigger feature extraction
        import subprocess
        try:
            subprocess.run([sys.executable, "features_extraction_to_csv.py", "--teacher", teacher_email], check=True)
            # Clear the cached recognizers to force reload on the next attendance
            keys_to_delete = [k for k in recognizers.keys() if k[0] == teacher_email]
            for k in keys_to_delete:
                del recognizers[k]
        except Exception as e:
            return jsonify({'error': f'Failed to extract features: {str(e)}'}), 500
            
    return jsonify({'success': True, 'message': f'Student {name} registered successfully.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
