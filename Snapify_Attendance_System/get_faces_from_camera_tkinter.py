import dlib
import numpy as np
import cv2
import os
import shutil
import time
import logging
import sqlite3
import db_manager
import argparse
import tkinter as tk
from tkinter import font as tkFont, messagebox
from PIL import Image, ImageTk

# Use frontal face detector of Dlib
detector = dlib.get_frontal_face_detector()

# ─── Color Palette ────────────────────────────────────────────────
BG_DARK       = "#0f1117"
BG_CARD       = "#1a1d27"
ACCENT        = "#0078D7"
ACCENT_HOVER  = "#005b9f"
SUCCESS       = "#2ea043"
WARNING       = "#f39c12"
ERROR         = "#e74c3c"
TEXT_PRIMARY  = "#e8e8f0"
TEXT_SECONDARY= "#8b8da3"
BORDER_COLOR  = "#2a2d3a"

# ─── Fonts ────────────────────────────────────────────────────────
FONT_TITLE    = ("Segoe UI", 20, "bold")
FONT_SUB      = ("Segoe UI", 11)
FONT_BTN      = ("Segoe UI", 10, "bold")
FONT_LOG      = ("Consolas", 9)


class Face_Register:
    def __init__(self, teacher_email=""):

        self.teacher_email = teacher_email
        self.current_frame_faces_cnt = 0  #  cnt for counting faces in current frame
        self.existing_faces_cnt = 0  # cnt for counting saved faces
        self.ss_cnt = 0  #  cnt for screen shots

        # Tkinter GUI
        self.win = tk.Tk()
        self.win.title("Snapify - Face Registration")
        self.win.geometry("1000x550")
        self.win.configure(bg=BG_DARK)
        
        # Set window icon 
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Snapify_Logo.jpeg")
            img = Image.open(icon_path)
            photo = ImageTk.PhotoImage(img)
            self.win.iconphoto(False, photo)
        except Exception:
            pass

        # GUI left part (Camera)
        self.frame_left_camera = tk.Frame(self.win, bg=BG_DARK)
        self.frame_left_camera.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.label = tk.Label(self.frame_left_camera, bg=BG_DARK)
        self.label.pack()

        # GUI right part (Info & Forms) with Scrollbar
        self.frame_right_wrapper = tk.Frame(self.win, bg=BG_DARK)
        self.frame_right_wrapper.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.canvas_right = tk.Canvas(self.frame_right_wrapper, bg=BG_DARK, highlightthickness=0)
        self.scrollbar_right = tk.Scrollbar(self.frame_right_wrapper, orient=tk.VERTICAL, command=self.canvas_right.yview)
        
        self.canvas_right.configure(yscrollcommand=self.scrollbar_right.set)
        self.scrollbar_right.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame_right_info = tk.Frame(self.canvas_right, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=10)
        self.canvas_window = self.canvas_right.create_window((0, 0), window=self.frame_right_info, anchor=tk.NW)

        def on_frame_configure(event):
            # Update scrollregion and canvas width to match frame
            self.canvas_right.configure(scrollregion=self.canvas_right.bbox("all"))
        self.frame_right_info.bind("<Configure>", on_frame_configure)
        
        # Mousewheel scrolling (Windows mostly uses delta 120)
        def _on_mousewheel(event):
            self.canvas_right.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas_right.bind_all("<MouseWheel>", _on_mousewheel)

        # Helpers for labels
        def _make_label(parent, text, font=FONT_SUB, fg=TEXT_PRIMARY):
            return tk.Label(parent, text=text, font=font, bg=BG_CARD, fg=fg)

        def _make_entry(parent):
            return tk.Entry(parent, font=FONT_SUB, bg="#12122a", fg=TEXT_PRIMARY,
                           insertbackground=TEXT_PRIMARY, relief="flat", highlightthickness=1,
                           highlightcolor=ACCENT, highlightbackground=BORDER_COLOR)

        self.label_cnt_face_in_database = _make_label(self.frame_right_info, str(self.existing_faces_cnt))
        self.label_fps_info = _make_label(self.frame_right_info, "")
        
        self.input_name = _make_entry(self.frame_right_info)
        self.input_name_char = ""
        self.input_roll = _make_entry(self.frame_right_info)
        self.input_roll_char = ""
        self.input_phone = _make_entry(self.frame_right_info)
        self.input_phone_char = ""
        self.input_email = _make_entry(self.frame_right_info)
        self.input_email_char = ""
        
        self.label_warning = tk.Label(self.frame_right_info, font=FONT_SUB, bg=BG_CARD, fg=WARNING)
        self.label_face_cnt = _make_label(self.frame_right_info, "Faces in current frame: ")
        self.log_all = tk.Label(self.frame_right_info, font=FONT_LOG, bg=BG_CARD, fg=SUCCESS)

        # Teacher-specific face data folder
        if self.teacher_email:
            self.path_photos_from_camera = f"data/data_faces_from_camera/{self.teacher_email}/"
        else:
            self.path_photos_from_camera = "data/data_faces_from_camera/"
        self.current_face_dir = ""
        self.font = cv2.FONT_ITALIC

        # Current frame and face ROI position
        self.current_frame = np.ndarray
        self.face_ROI_image = np.ndarray
        self.face_ROI_width_start = 0
        self.face_ROI_height_start = 0
        self.face_ROI_width = 0
        self.face_ROI_height = 0
        self.ww = 0
        self.hh = 0

        self.out_of_range_flag = False
        self.face_folder_created_flag = False

        # FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0
        self.fps_show = 0
        self.start_time = time.time()

        self.cap = cv2.VideoCapture(0)  # Get video stream from camera

        # self.cap = cv2.VideoCapture("test.mp4")   # Input local video

    #  Delete old face folders
    def GUI_clear_data(self):
        #  "/data_faces_from_camera/person_x/"...
        if os.path.isdir(self.path_photos_from_camera):
            folders_rd = os.listdir(self.path_photos_from_camera)
            for i in range(len(folders_rd)):
                shutil.rmtree(self.path_photos_from_camera + folders_rd[i])
        # Remove teacher-specific CSV
        if self.teacher_email:
            csv_path = f"data/features_{self.teacher_email}.csv"
        else:
            csv_path = "data/features_all.csv"
        if os.path.isfile(csv_path):
            os.remove(csv_path)
        self.label_cnt_face_in_database['text'] = "0"
        self.existing_faces_cnt = 0
        self.log_all["text"] = "Face images and `features_all.csv` removed!"

    def GUI_get_input_name(self):
        self.input_name_char = self.input_name.get().strip()
        self.input_roll_char = self.input_roll.get().strip()
        self.input_phone_char = self.input_phone.get().strip()
        self.input_email_char = self.input_email.get().strip()

        # Validate all fields
        if not self.input_name_char:
            self.log_all["text"] = "\u26a0 Please enter student Name!"
            return
        if not self.input_roll_char:
            self.log_all["text"] = "\u26a0 Please enter Roll Number!"
            return
        if not self.input_phone_char:
            self.log_all["text"] = "\u26a0 Please enter Phone Number!"
            return
        if not self.input_email_char:
            self.log_all["text"] = "\u26a0 Please enter Email!"
            return

        # Save student info to database
        self._save_student_to_db()
        self.create_face_folder()
        self.label_cnt_face_in_database['text'] = str(self.existing_faces_cnt)

        db_manager.init_db()
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR REPLACE INTO students (roll_number, name, phone, email, teacher_email) VALUES (?, ?, ?, ?, ?)",
                           (self.input_roll_char, self.input_name_char, self.input_phone_char, self.input_email_char, self.teacher_email))
            conn.commit()
            self.log_all["text"] = f"Student '{self.input_name_char}' (Roll: {self.input_roll_char}) saved!"
            messagebox.showinfo("Registration Successful",
                                f"\u2705 Student '{self.input_name_char}' (Roll: {self.input_roll_char}) registered successfully!\n\nNow capture face images using Step 3.")
        except Exception as e:
            self.log_all["text"] = f"DB Error: {str(e)}"
            messagebox.showerror("Registration Failed",
                                 f"\u274c Failed to register student.\n\nError: {str(e)}")
        finally:
            conn.close()

    # ─── Edit Existing Student (opens a popup window) ─────────────────────

    def _open_edit_window(self):
        """Open a separate popup window for editing an already-registered student."""
        edit_win = tk.Toplevel(self.win)
        edit_win.title("Snapify - Edit Student Details")
        edit_win.geometry("480x420")
        edit_win.resizable(False, False)
        edit_win.configure(bg=BG_DARK)
        edit_win.grab_set()  # Make it modal

        # Container card
        card = tk.Frame(edit_win, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # State for this popup
        loaded_roll = [None]  # Use list so inner functions can mutate
        status_label = tk.Label(card, text="Enter Roll Number and click Load", fg=TEXT_SECONDARY, bg=BG_CARD, font=FONT_SUB)

        tk.Label(card, text="Edit Student Details", font=FONT_TITLE, bg=BG_CARD, fg=TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=3, padx=15, pady=(15, 10), sticky=tk.W)

        def _make_label(text):
            return tk.Label(card, text=text, font=FONT_SUB, bg=BG_CARD, fg=TEXT_PRIMARY)

        def _make_entry():
            return tk.Entry(card, font=FONT_SUB, bg="#12122a", fg=TEXT_PRIMARY,
                           insertbackground=TEXT_PRIMARY, relief="flat", highlightthickness=1,
                           highlightcolor=ACCENT, highlightbackground=BORDER_COLOR, width=22)

        def _make_button(text, command, bg_color=ACCENT):
            return tk.Button(card, text=text, command=command, font=FONT_BTN, fg="white", bg=bg_color, 
                             activebackground=bg_color, activeforeground="white", bd=0, cursor="hand2", padx=10, pady=4)

        # Roll Number + Load
        _make_label("Roll No:").grid(row=1, column=0, padx=15, pady=8, sticky=tk.W)
        edit_roll = _make_entry()
        edit_roll.grid(row=1, column=1, padx=5, pady=8)

        # Fields
        _make_label("Name:").grid(row=2, column=0, padx=15, pady=8, sticky=tk.W)
        edit_name = _make_entry()
        edit_name.grid(row=2, column=1, padx=5, pady=8)

        _make_label("Phone:").grid(row=3, column=0, padx=15, pady=8, sticky=tk.W)
        edit_phone = _make_entry()
        edit_phone.grid(row=3, column=1, padx=5, pady=8)

        _make_label("Email:").grid(row=4, column=0, padx=15, pady=8, sticky=tk.W)
        edit_email = _make_entry()
        edit_email.grid(row=4, column=1, padx=5, pady=8)

        status_label.grid(row=7, column=0, columnspan=3, padx=15, pady=(20, 10), sticky=tk.W)

        # ── Load button callback ──
        def load_student():
            roll = edit_roll.get().strip()
            if not roll:
                status_label["text"] = "⚠️ Enter a Roll Number!"
                status_label["fg"] = ERROR
                return
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name, phone, email FROM students WHERE roll_number = ? AND teacher_email = ?", (roll, self.teacher_email))
            result = cursor.fetchone()
            conn.close()
            if result:
                name, phone, email = result
                edit_name.delete(0, tk.END)
                edit_name.insert(0, name or "")
                edit_phone.delete(0, tk.END)
                edit_phone.insert(0, phone or "")
                edit_email.delete(0, tk.END)
                edit_email.insert(0, email or "")
                loaded_roll[0] = roll
                status_label["text"] = f"✅ Loaded '{name}'. Edit & Update."
                status_label["fg"] = SUCCESS
            else:
                loaded_roll[0] = None
                status_label["text"] = f"⚠️ No student found with Roll '{roll}'!"
                status_label["fg"] = ERROR

        _make_button("🔍 Load", load_student, bg_color="#555770").grid(row=1, column=2, padx=10, pady=8)

        # ── Update button callback ──
        def update_student():
            if not loaded_roll[0]:
                status_label["text"] = "⚠️ Load a student first!"
                status_label["fg"] = ERROR
                return
            name = edit_name.get().strip()
            phone = edit_phone.get().strip()
            email = edit_email.get().strip()
            if not name:
                status_label["text"] = "⚠️ Name cannot be empty!"
                status_label["fg"] = ERROR
                return
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE students SET name = ?, phone = ?, email = ? WHERE roll_number = ? AND teacher_email = ?",
                               (name, phone, email, loaded_roll[0], self.teacher_email))
                conn.commit()
                status_label["text"] = f"✅ '{name}' updated!"
                status_label["fg"] = SUCCESS
                self.log_all["text"] = f"Student '{name}' updated via Edit window."
            except Exception as e:
                status_label["text"] = f"DB Error: {str(e)}"
                status_label["fg"] = ERROR
            finally:
                conn.close()

        # ── Re-capture button callback ──
        def recapture_face():
            if not loaded_roll[0]:
                status_label["text"] = "⚠️ Load a student first!"
                status_label["fg"] = ERROR
                return
            roll = loaded_roll[0]
            name = edit_name.get().strip() or "unknown"
            # Remove old face folder
            self._remove_old_face_folder(roll)
            # Prepare new capture
            self.input_roll_char = roll
            self.input_name_char = name
            self.create_face_folder()
            self.label_cnt_face_in_database['text'] = str(self.existing_faces_cnt)
            status_label["text"] = f"📷 Ready! Use 'Capture Current Frame' in main window."
            status_label["fg"] = ACCENT
            self.log_all["text"] = f"Re-capture ready for '{name}'. Use 'Capture Current Frame'."
            edit_win.destroy()

        btn_container = tk.Frame(card, bg=BG_CARD)
        btn_container.grid(row=5, column=0, columnspan=3, pady=(20, 0), sticky=tk.W, padx=15)

        _make_button("✓ Update Info", update_student, bg_color=SUCCESS).pack(side=tk.LEFT, padx=(0, 10))
        _make_button("📷 Re-capture Face", recapture_face, bg_color=ACCENT).pack(side=tk.LEFT, padx=(0, 10))
        _make_button("Close", edit_win.destroy, bg_color="#8b8da3").pack(side=tk.LEFT)

    def _remove_old_face_folder(self, roll):
        """Remove the face folder of a student so faces can be re-captured."""
        if os.path.isdir(self.path_photos_from_camera):
            for folder in os.listdir(self.path_photos_from_camera):
                # Folder format: person_X_ROLL_Name
                parts = folder.split('_')
                if len(parts) >= 3 and parts[2] == roll:
                    folder_path = os.path.join(self.path_photos_from_camera, folder)
                    shutil.rmtree(folder_path)
                    logging.info("Removed old face folder: %s", folder_path)
                    break

    # ─── GUI Layout ───────────────────────────────────────────────────────

    def GUI_info(self):
        # ─── Logo and Title ───
        header_frame = tk.Frame(self.frame_right_info, bg=BG_CARD)
        header_frame.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 20))
        
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Snapify_Logo.jpeg")
            img = Image.open(icon_path)
            img = img.resize((50, 50), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            logo_label = tk.Label(header_frame, image=photo, bg=BG_CARD)
            logo_label.image = photo
            logo_label.pack(side=tk.LEFT, padx=(0, 10))
        except Exception:
            tk.Label(header_frame, text="🎯", font=("Segoe UI", 24), bg=BG_CARD).pack(side=tk.LEFT, padx=(0, 10))
            
        tk.Label(header_frame, text="Snapify", font=FONT_TITLE, fg=ACCENT, bg=BG_CARD).pack(anchor="w")
        tk.Label(header_frame, text="Face Registration", font=FONT_SUB, fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w")

        # ─── Stats ───
        tk.Label(self.frame_right_info, text="FPS: ", font=FONT_SUB, bg=BG_CARD, fg=TEXT_SECONDARY).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.label_fps_info.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        tk.Label(self.frame_right_info, text="Registered Faces: ", font=FONT_SUB, bg=BG_CARD, fg=TEXT_SECONDARY).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.label_cnt_face_in_database.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        tk.Label(self.frame_right_info, text="Faces in view: ", font=FONT_SUB, bg=BG_CARD, fg=TEXT_SECONDARY).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        self.label_face_cnt.grid(row=3, column=2, columnspan=3, sticky=tk.W, padx=5, pady=2)
        self.label_warning.grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)

        # Helper for modern buttons
        def _make_button(parent, text, command, bg_color=ACCENT, hover_color=ACCENT_HOVER, fg_color="white", width=20):
            btn = tk.Button(parent, text=text, command=command, font=FONT_BTN, fg=fg_color, bg=bg_color, 
                            activebackground=hover_color, activeforeground="white", bd=0, cursor="hand2", width=width, pady=6)
            return btn

        def _make_section_title(text, row):
            tk.Label(self.frame_right_info, text=text, font=("Segoe UI", 12, "bold"), bg=BG_CARD, fg=TEXT_PRIMARY).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(20, 10))

        # ─── Step 1: Clear ───
        _make_section_title("Step 1: Clear local cache", 5)
        _make_button(self.frame_right_info, "🗑️ Clear Cache", self.GUI_clear_data, bg_color="#555770", hover_color=ERROR).grid(row=6, column=0, columnspan=3, sticky=tk.W, padx=5)

        # ─── Step 2: Details ───
        _make_section_title("Step 2: Student Details", 7)
        
        lbl_kw = {"font": FONT_SUB, "bg": BG_CARD, "fg": TEXT_PRIMARY}
        tk.Label(self.frame_right_info, text="Roll No: ", **lbl_kw).grid(row=8, column=0, sticky=tk.W, padx=5, pady=4)
        self.input_roll.grid(row=8, column=1, sticky=tk.W, padx=0, pady=4)

        tk.Label(self.frame_right_info, text="Name: ", **lbl_kw).grid(row=9, column=0, sticky=tk.W, padx=5, pady=4)
        self.input_name.grid(row=9, column=1, sticky=tk.W, padx=0, pady=4)

        tk.Label(self.frame_right_info, text="Phone: ", **lbl_kw).grid(row=10, column=0, sticky=tk.W, padx=5, pady=4)
        self.input_phone.grid(row=10, column=1, sticky=tk.W, padx=0, pady=4)

        tk.Label(self.frame_right_info, text="Email: ", **lbl_kw).grid(row=11, column=0, sticky=tk.W, padx=5, pady=4)
        self.input_email.grid(row=11, column=1, sticky=tk.W, padx=0, pady=4)

        _make_button(self.frame_right_info, "✓ Register", self.GUI_get_input_name, bg_color=SUCCESS, width=25).grid(row=12, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        # ─── Step 3: Capture ───
        _make_section_title("Step 3: Capture Face", 13)
        _make_button(self.frame_right_info, "📷 Capture Current Frame", self.save_current_face, bg_color=ACCENT, width=25).grid(row=14, column=0, columnspan=3, sticky=tk.W, padx=5)

        # ─── Edit Student ───
        _make_button(self.frame_right_info, "✏️ Edit Existing Student", self._open_edit_window, bg_color="#8b8da3", hover_color="#555770", width=25).grid(row=15, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(30, 0))

        # ─── Log ───
        self.log_all.grid(row=16, column=0, columnspan=3, sticky=tk.W, padx=5, pady=20)

    # Mkdir for saving photos and csv
    def pre_work_mkdir(self):
        # Create folders to save face images and csv
        if not os.path.isdir(self.path_photos_from_camera):
            os.makedirs(self.path_photos_from_camera, exist_ok=True)

    # Start from person_x+1
    def check_existing_faces_cnt(self):
        if os.path.isdir(self.path_photos_from_camera) and os.listdir(self.path_photos_from_camera):
            # Get the order of latest person
            person_list = os.listdir(self.path_photos_from_camera)
            person_num_list = []
            for person in person_list:
                parts = person.split('_')
                if len(parts) >= 2:
                    try:
                        person_num_list.append(int(parts[1]))
                    except ValueError:
                        pass
            self.existing_faces_cnt = max(person_num_list) if person_num_list else 0

        # Start from person_1
        else:
            self.existing_faces_cnt = 0

    # Update FPS of Video stream
    def update_fps(self):
        now = time.time()
        #  Refresh fps per second
        if str(self.start_time).split(".")[0] != str(now).split(".")[0]:
            self.fps_show = self.fps
        self.start_time = now
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

        self.label_fps_info["text"] = str(self.fps.__round__(2))

    def create_face_folder(self):
        #  Create the folders for saving faces
        self.existing_faces_cnt += 1
        if self.input_roll_char and self.input_name_char:
            # Folder format: person_X_ROLL_Name
            self.current_face_dir = self.path_photos_from_camera + \
                                    "person_" + str(self.existing_faces_cnt) + "_" + \
                                    self.input_roll_char + "_" + self.input_name_char
        elif self.input_name_char:
            self.current_face_dir = self.path_photos_from_camera + \
                                    "person_" + str(self.existing_faces_cnt) + "_" + \
                                    self.input_name_char
        else:
            self.current_face_dir = self.path_photos_from_camera + \
                                    "person_" + str(self.existing_faces_cnt)
        os.makedirs(self.current_face_dir)
        self.log_all["text"] = "\"" + self.current_face_dir + "/\" created!"
        logging.info("\n%-40s %s", "Create folders:", self.current_face_dir)

        self.ss_cnt = 0  #  Clear the cnt of screen shots
        self.face_folder_created_flag = True  # Face folder already created

    def save_current_face(self):
        if self.face_folder_created_flag:
            if self.current_frame_faces_cnt == 1:
                if not self.out_of_range_flag:
                    self.ss_cnt += 1
                    #  Create blank image according to the size of face detected
                    self.face_ROI_image = np.zeros((int(self.face_ROI_height * 2), self.face_ROI_width * 2, 3),
                                                   np.uint8)
                    for ii in range(self.face_ROI_height * 2):
                        for jj in range(self.face_ROI_width * 2):
                            self.face_ROI_image[ii][jj] = self.current_frame[self.face_ROI_height_start - self.hh + ii][
                                self.face_ROI_width_start - self.ww + jj]
                    self.log_all["text"] = "\"" + self.current_face_dir + "/img_face_" + str(
                        self.ss_cnt) + ".jpg\"" + " saved!"
                    self.face_ROI_image = cv2.cvtColor(self.face_ROI_image, cv2.COLOR_BGR2RGB)

                    cv2.imwrite(self.current_face_dir + "/img_face_" + str(self.ss_cnt) + ".jpg", self.face_ROI_image)
                    logging.info("%-40s %s/img_face_%s.jpg", "Save into：",
                                 str(self.current_face_dir), str(self.ss_cnt) + ".jpg")
                    
                    messagebox.showinfo("Registration Complete",
                                        f"✅ Face image #{self.ss_cnt} captured successfully!\n\n"
                                        "Registration for this student is now fully complete.\n\n"
                                        "You may capture more frames for better accuracy, or close this window and proceed to Extract Features.")
                else:
                    self.log_all["text"] = "Please do not out of range!"
                    messagebox.showwarning("Warning", "Face is out of range! Please position yourself clearly in the frame.")
            else:
                self.log_all["text"] = "No face in current frame!"
                messagebox.showerror("Error", "No face detected in the current frame! Please look at the camera.")
        else:
            self.log_all["text"] = "Please run step 2!"
            messagebox.showerror("Registration Failed", "❌ Please complete Step 2 (Student Details) and hit Register first!")

    def get_frame(self):
        try:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                frame = cv2.resize(frame, (640,480))
                return ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except:
            print("Error: No video input!!!")

    #  Main process of face detection and saving
    def process(self):
        ret, self.current_frame = self.get_frame()
        faces = detector(self.current_frame, 0)
        # Get frame
        if ret:
            self.update_fps()
            self.label_face_cnt["text"] = str(len(faces))
            # Draw a permanent guide box to help user alignment
            target_left, target_top, target_right, target_bottom = 170, 90, 470, 390
            cv2.rectangle(self.current_frame, (target_left, target_top), (target_right, target_bottom), (255, 255, 255), 1, cv2.LINE_4)

            #  Face detected
            if len(faces) != 0:
                #   Show the ROI of faces
                for k, d in enumerate(faces):
                    self.face_ROI_width_start = d.left()
                    self.face_ROI_height_start = d.top()
                    #  Compute the size of rectangle box
                    self.face_ROI_height = (d.bottom() - d.top())
                    self.face_ROI_width = (d.right() - d.left())
                    self.hh = int(self.face_ROI_height / 2)
                    self.ww = int(self.face_ROI_width / 2)

                    # Ensure the whole expanded bounding box fits loosely inside or around the target
                    margin = 50
                    if (d.right() > target_right + margin) or (d.bottom() > target_bottom + margin) or \
                       (d.left() < target_left - margin) or (d.top() < target_top - margin):
                        self.label_warning["text"] = "ALIGN FACE IN BOX"
                        self.label_warning['fg'] = 'red'
                        self.out_of_range_flag = True
                        color_rectangle = (255, 0, 0) # Blue-ish (BGR) meaning bad since we use RGB here, actually RGB output: Red is (255, 0, 0)
                    else:
                        self.out_of_range_flag = False
                        self.label_warning["text"] = "GOOD POSITION"
                        self.label_warning['fg'] = 'green'
                        color_rectangle = (0, 255, 0) # Green bounding box

                    self.current_frame = cv2.rectangle(self.current_frame,
                                                       tuple([d.left() - self.ww, d.top() - self.hh]),
                                                       tuple([d.right() + self.ww, d.bottom() + self.hh]),
                                                       color_rectangle, 2)

            self.current_frame_faces_cnt = len(faces)

            # Convert PIL.Image.Image to PIL.Image.PhotoImage
            img_Image = Image.fromarray(self.current_frame)
            img_PhotoImage = ImageTk.PhotoImage(image=img_Image)
            self.label.img_tk = img_PhotoImage
            self.label.configure(image=img_PhotoImage)

        # Refresh frame
        self.win.after(20, self.process)

    def run(self):
        self.pre_work_mkdir()
        self.check_existing_faces_cnt()
        self.GUI_info()
        self.process()
        self.win.mainloop()


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Face Registration')
    parser.add_argument('--teacher', type=str, default='', help='Teacher email for data isolation')
    args = parser.parse_args()
    Face_Register_con = Face_Register(teacher_email=args.teacher)
    Face_Register_con.run()


if __name__ == '__main__':
    main()
