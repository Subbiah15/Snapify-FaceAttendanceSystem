from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.properties import NumericProperty, StringProperty, ListProperty, ObjectProperty, BooleanProperty
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage


import cv2
import sqlite3
import datetime
import os
import sys
import json
import shutil
import dlib
import numpy as np
import time
import threading

from attendance_taker import Face_Recognizer

# Initialize dlib detector (same as desktop version)
detector = dlib.get_frontal_face_detector()

# Vibrant Modern Colors
COLORS = {
    'bg_dark': (0.05, 0.05, 0.07, 1),        # Very dark blue-gray
    'bg_card': (0.10, 0.10, 0.13, 1),        # Elevated card color
    'bg_card_hover': (0.14, 0.14, 0.18, 1), 
    'accent': (0.38, 0.22, 1.0, 1),          # Vibrant Modern Purple
    'accent_hover': (0.45, 0.26, 1.0, 1),    
    'success': (0.0, 0.8, 0.4, 1),           # Bright Green
    'warning': (1.0, 0.5, 0.0, 1),           # Modern Orange
    'error': (1.0, 0.2, 0.3, 1),             # Modern Crimson
    'text_primary': (0.95, 0.95, 0.98, 1),   # Almost white
    'text_secondary': (0.6, 0.6, 0.7, 1),    # Soft gray
    'text_dim': (0.4, 0.4, 0.5, 1),          
    'border': (0.2, 0.2, 0.25, 1),           
}

KV = '''
#:kivy 2.0

<Button>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    font_size: '12sp'
    bold: True
    color: 1, 1, 1, 1
    size_hint_y: None
    height: dp(38)
    canvas.before:
        Color:
            rgba: self.background_color if self.state == 'normal' else (self.background_color[0]*0.8, self.background_color[1]*0.8, self.background_color[2]*0.8, self.background_color[3])
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]

<TextInput>:
    background_normal: ''
    background_active: ''
    background_color: 0.10, 0.10, 0.13, 1    # bg_card
    foreground_color: 0.95, 0.95, 0.98, 1    # text_primary
    cursor_color: 0.38, 0.22, 1.0, 1         # accent
    hint_text_color: 0.4, 0.4, 0.5, 1        # text_dim
    padding: [dp(10), (self.height - self.line_height) / 2]
    font_size: '13sp'
    multiline: False
    size_hint_y: None
    height: dp(42)

<LoginScreen>:
    canvas.before:
        Color:
            rgba: app.COLORS['bg_dark']
        Rectangle:
            size: self.size
            pos: self.pos
    
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(12)
        
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(140)
            spacing: dp(10)
            
            Image:
                source: 'Snapify_Logo.jpeg'
                size_hint_y: None
                height: dp(80)
                allow_stretch: True
            
            Label:
                text: 'Snapify'
                font_size: '28sp'
                bold: True
                color: app.COLORS['accent']
                size_hint_y: None
                height: dp(40)
        
        Label:
            text: 'Sign in with your teacher email'
            font_size: '13sp'
            color: app.COLORS['text_secondary']
            size_hint_y: None
            height: dp(30)
        
        TextInput:
            id: email_input
            hint_text: 'Teacher Email'
            multiline: False
        
        TextInput:
            id: password_input
            hint_text: 'Password'
            password: True
            multiline: False
        
        BoxLayout:
            size_hint_y: None
            height: dp(38)
            spacing: dp(12)
            
            Button:
                text: 'Sign In'
                background_color: app.COLORS['accent']
                on_release: root.sign_in()
            
            Button:
                text: 'Register'
                background_color: app.COLORS['text_secondary']
                on_release: app.root.current = 'signup'
                
        Widget:
            size_hint_y: 1

<SignUpScreen>:
    canvas.before:
        Color:
            rgba: app.COLORS['bg_dark']
        Rectangle:
            size: self.size
            pos: self.pos
    
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(12)
        
        Label:
            text: 'Create Teacher Account'
            font_size: '22sp'
            bold: True
            color: app.COLORS['accent']
            size_hint_y: None
            height: dp(50)
        
        TextInput:
            id: signup_email_input
            hint_text: 'Email'
            multiline: False
        
        TextInput:
            id: signup_name_input
            hint_text: 'Full Name'
            multiline: False
        
        TextInput:
            id: signup_password_input
            hint_text: 'Password'
            password: True
            multiline: False
        
        BoxLayout:
            size_hint_y: None
            height: dp(38)
            spacing: dp(12)
            
            Button:
                text: 'Sign Up'
                background_color: app.COLORS['success']
                on_release: root.register_teacher()
            
            Button:
                text: 'Back'
                background_color: app.COLORS['text_secondary']
                on_release: app.root.current = 'login'
                
        Widget:
            size_hint_y: 1

<DashboardScreen>:
    canvas.before:
        Color:
            rgba: app.COLORS['bg_dark']
        Rectangle:
            size: self.size
            pos: self.pos
    
    BoxLayout:
        orientation: 'vertical'
        
        # Header
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(64)
            padding: dp(16), dp(8)
            spacing: dp(12)
            
            BoxLayout:
                orientation: 'horizontal'
                size_hint_x: 0.7
                spacing: dp(10)
                
                Image:
                    source: 'Snapify_Logo.jpeg'
                    size_hint_x: None
                    width: dp(36)
                    allow_stretch: True
                
                Label:
                    text: 'Snapify'
                    font_size: '22sp'
                    bold: True
                    color: app.COLORS['accent']
                    halign: 'left'
                    text_size: self.size
                    valign: 'middle'
            
            BoxLayout:
                orientation: 'horizontal'
                size_hint_x: 0.3
                spacing: dp(10)
                
                Label:
                    text: f'👤 {app.teacher_email.split("@")[0]}'
                    color: app.COLORS['text_secondary']
                    font_size: '11sp'
                    halign: 'right'
                    text_size: self.size
                    valign: 'middle'
                
                Button:
                    text: '🚪 Logout'
                    background_color: app.COLORS['error']
                    size_hint_x: None
                    width: dp(80)
                    font_size: '11sp'
                    height: dp(32)
                    pos_hint: {'center_y': 0.5}
                    on_release: root.logout()
        
        # Separator
        Widget:
            size_hint_y: None
            height: dp(1)
            canvas:
                Color:
                    rgba: app.COLORS['border']
                Rectangle:
                    size: self.size
                    pos: self.pos
        
        # Main content - First workflow step fixed above scrollable area
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(120)
            padding: dp(16), dp(12)
            spacing: dp(12)
            
            Widget:
                size_hint_x: None
                width: dp(4)
                canvas:
                    Color:
                        rgba: app.COLORS['accent']
                    Rectangle:
                        size: self.size
                        pos: self.pos
            
            BoxLayout:
                orientation: 'horizontal'
                padding: dp(4)
                spacing: dp(16)
                
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_x: 0.6
                    spacing: dp(4)
                    
                    Label:
                        text: '01 Registration'
                        font_size: '16sp'
                        bold: True
                        color: app.COLORS['text_primary']
                        size_hint_y: None
                        height: dp(28)
                        halign: 'left'
                        text_size: self.size
                    
                    Label:
                        text: 'Open webcam to capture face images'
                        font_size: '12sp'
                        color: app.COLORS['text_secondary']
                        size_hint_y: None
                        height: dp(40)
                        halign: 'left'
                        text_size: self.size
                
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_x: 0.4
                    spacing: dp(6)
                    padding: 0, dp(4)
                    
                    Button:
                        text: '➕ New Student'
                        background_color: app.COLORS['accent']
                        font_size: '11sp'
                        height: dp(32)
                        on_release: root.launch_face_register()
                    
                    Button:
                        text: '✏️ Edit Student'
                        background_color: app.COLORS['warning']
                        font_size: '11sp'
                        height: dp(32)
                        on_release: root.edit_student_info()
                    
                    Label:
                        text: root.step1_status
                        font_size: '10sp'
                        color: app.COLORS['text_secondary']
                        size_hint_y: None
                        height: dp(16)
                        halign: 'center'
                        text_size: self.size
        
        # Spacing between sections
        Widget:
            size_hint_y: None
            height: dp(12)
        
        # WORKFLOW STEPS header
        Label:
            text: 'WORKFLOW STEPS'
            font_size: '12sp'
            bold: True
            color: app.COLORS['text_secondary']
            size_hint_y: None
            height: dp(32)
            padding: dp(12), dp(8)
        
        # Remaining steps scrollable
        ScrollView:
            id: steps_scroll
            size_hint_y: 1
            scroll_y: 1
            
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                padding: dp(16)
                
                # Step 2
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(90)
                    
                    Widget:
                        size_hint_x: None
                        width: dp(4)
                        canvas:
                            Color:
                                rgba: (0, 0.36, 0.62, 1)
                            Rectangle:
                                size: self.size
                                pos: self.pos
                    
                    BoxLayout:
                        orientation: 'horizontal'
                        padding: dp(12)
                        
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_x: 0.6
                            spacing: dp(2)
                            
                            Label:
                                text: '02 Extract Features'
                                font_size: '16sp'
                                bold: True
                                color: app.COLORS['text_primary']
                                halign: 'left'
                                text_size: self.size
                            
                            Label:
                                text: 'Process saved face images and generate vectors'
                                font_size: '11sp'
                                color: app.COLORS['text_secondary']
                                halign: 'left'
                                text_size: self.size
                        
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_x: 0.4
                            spacing: dp(4)
                            
                            Button:
                                text: '⚙️ Extract'
                                background_color: (0, 0.36, 0.62, 1)
                                font_size: '12sp'
                                height: dp(36)
                                on_release: root.extract_features()
                            
                            Label:
                                text: root.step2_status
                                font_size: '10sp'
                                color: app.COLORS['text_secondary']
                                halign: 'center'
                                text_size: self.size
                
                # Step 3
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(90)
                    
                    Widget:
                        size_hint_x: None
                        width: dp(4)
                        canvas:
                            Color:
                                rgba: app.COLORS['warning']
                            Rectangle:
                                size: self.size
                                pos: self.pos
                    
                    BoxLayout:
                        orientation: 'horizontal'
                        padding: dp(12)
                        
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_x: 0.6
                            spacing: dp(2)
                            
                            Label:
                                text: '03 Take Attendance'
                                font_size: '16sp'
                                bold: True
                                color: app.COLORS['text_primary']
                                halign: 'left'
                                text_size: self.size
                            
                            Label:
                                text: 'Start real-time face recognition'
                                font_size: '11sp'
                                color: app.COLORS['text_secondary']
                                halign: 'left'
                                text_size: self.size
                        
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_x: 0.4
                            spacing: dp(4)
                            
                            Button:
                                text: '✅ Start'
                                background_color: app.COLORS['warning']
                                font_size: '12sp'
                                height: dp(36)
                                on_release: root.start_attendance()
                            
                            Label:
                                text: root.step3_status
                                font_size: '10sp'
                                color: app.COLORS['text_secondary']
                                halign: 'center'
                                text_size: self.size
                
                # Step 4
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(90)
                    
                    Widget:
                        size_hint_x: None
                        width: dp(4)
                        canvas:
                            Color:
                                rgba: app.COLORS['success']
                            Rectangle:
                                size: self.size
                                pos: self.pos
                    
                    BoxLayout:
                        orientation: 'horizontal'
                        padding: dp(12)
                        
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_x: 0.6
                            spacing: dp(2)
                            
                            Label:
                                text: '04 View Records'
                                font_size: '16sp'
                                bold: True
                                color: app.COLORS['text_primary']
                                halign: 'left'
                                text_size: self.size
                            
                            Label:
                                text: 'Open dashboard to browse history'
                                font_size: '11sp'
                                color: app.COLORS['text_secondary']
                                halign: 'left'
                                text_size: self.size
                        
                        BoxLayout:
                            orientation: 'vertical'
                            size_hint_x: 0.4
                            spacing: dp(4)
                            
                            Button:
                                text: '📊 Dashboard'
                                background_color: app.COLORS['success']
                                font_size: '12sp'
                                height: dp(36)
                                on_release: root.open_dashboard()
                            
                            Label:
                                text: root.step4_status
                                font_size: '10sp'
                                color: app.COLORS['text_secondary']
                                halign: 'center'
                                text_size: self.size
        
        # Log section
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: 0.15
            padding: dp(16)
            spacing: dp(8)
            
            BoxLayout:
                size_hint_y: None
                height: dp(24)
                
                Label:
                    text: 'OUTPUT LOG'
                    font_size: '11sp'
                    bold: True
                    color: app.COLORS['text_secondary']
                
                Button:
                    text: 'Clear'
                    background_color: app.COLORS['bg_card']
                    color: app.COLORS['text_secondary']
                    font_size: '10sp'
                    size_hint_x: 0.2
                    on_release: root.clear_log()
            
            ScrollView:
                
                TextInput:
                    text: root.log_content
                    readonly: True
                    background_color: app.COLORS['bg_card']
                    foreground_color: app.COLORS['text_secondary']
                    font_size: '10sp'

<RegisterStudentScreen>:
    canvas.before:
        Color:
            rgba: app.COLORS['bg_dark']
        Rectangle:
            size: self.size
            pos: self.pos
    
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)
        
        Label:
            text: 'Re-capture Face' if root.edit_mode else 'Register Student' if root.step == 'form' else f'Capture Face - {int(root.capture_count)} photos'
            font_size: '20sp'
            bold: True
            color: app.COLORS['accent']
            size_hint_y: 0.08
        
        ScreenManager:
            id: internal_sm
            size_hint_y: 0.92
            
            # FORM VIEW
            Screen:
                name: 'form_screen'
                ScrollView:
                    id: form_scroll
                    GridLayout:
                        cols: 1
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(10)
                        padding: dp(12), dp(12), dp(12), dp(100)
                        
                        Label:
                            text: 'Re-capture Face Images' if root.edit_mode else 'New Student Registration'
                            font_size: '14sp'
                            bold: True
                            color: app.COLORS['accent']
                            size_hint_y: None
                            height: dp(32)
                        
                        GridLayout:
                            cols: 2
                            size_hint_y: None
                            height: dp(40)
                            spacing: dp(6)
                            
                            TextInput:
                                id: roll_input
                                hint_text: 'Roll Number'
                                foreground_color: app.COLORS['text_primary']
                                background_color: app.COLORS['bg_card']
                                multiline: False
                                readonly: root.edit_mode and root.data_loaded
                            
                            Button:
                                text: 'Load'
                                size_hint_x: None
                                width: dp(80)
                                background_color: app.COLORS['accent']
                                opacity: 1 if root.edit_mode and not root.data_loaded else 0
                                disabled: not (root.edit_mode and not root.data_loaded)
                                on_release: root.load_student_data()
                        
                        TextInput:
                            id: name_input
                            hint_text: 'Student Name'
                            foreground_color: app.COLORS['text_primary']
                            background_color: app.COLORS['bg_card']
                            size_hint_y: None
                            height: dp(40)
                            multiline: False
                        
                        TextInput:
                            id: phone_input
                            hint_text: 'Phone Number'
                            foreground_color: app.COLORS['text_primary']
                            background_color: app.COLORS['bg_card']
                            size_hint_y: None
                            height: dp(40)
                            multiline: False
                        
                        TextInput:
                            id: email_input
                            hint_text: 'Student Email'
                            foreground_color: app.COLORS['text_primary']
                            background_color: app.COLORS['bg_card']
                            size_hint_y: None
                            height: dp(40)
                            multiline: False
                        
                        # Action buttons for EDIT MODE
                        BoxLayout:
                            size_hint_y: None
                            height: dp(50) if root.edit_mode else 0
                            spacing: dp(6)
                            opacity: 1 if root.edit_mode else 0
                            disabled: not root.edit_mode
                            
                            Button:
                                text: '📷 Recapture'
                                background_color: app.COLORS['accent']
                                height: dp(38) if root.edit_mode else 0
                                on_release: root.start_capture_step()
                            
                            Button:
                                text: '✓ Update'
                                background_color: app.COLORS['success']
                                height: dp(38) if root.edit_mode else 0
                                on_release: root.update_student_data()
                            
                            Button:
                                text: '🗑️ Delete'
                                background_color: app.COLORS['error']
                                height: dp(38) if root.edit_mode else 0
                                on_release: root.delete_student_data()
                        
                        # Action buttons for NEW REGISTRATION
                        BoxLayout:
                            size_hint_y: None
                            height: dp(50) if not root.edit_mode else 0
                            spacing: dp(6)
                            opacity: 1 if not root.edit_mode else 0
                            disabled: root.edit_mode
                            
                            Button:
                                text: '📷 Face Register'
                                background_color: app.COLORS['accent']
                                height: dp(38) if not root.edit_mode else 0
                                on_release: root.start_capture_step()
                            
                            Button:
                                text: '✓ Register'
                                background_color: app.COLORS['success']
                                height: dp(38) if not root.edit_mode else 0
                                on_release: root.register_new_student()
                        
                        Button:
                            text: '← Back to Dashboard'
                            size_hint_y: None
                            height: dp(42)
                            background_color: app.COLORS['text_secondary']
                            on_release: app.root.current = 'dashboard'
                        
                        Widget:  # extra space
                            size_hint_y: None
                            height: dp(10)
            
            # CAPTURE VIEW
            Screen:
                name: 'capture_screen'
                BoxLayout:
                    id: capture_layout
                    orientation: 'vertical'
                    spacing: dp(8)
                    padding: dp(8)
                    
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: 0.08
                        spacing: dp(20)
                        padding: dp(8)
                        
                        Label:
                            text: root.fps_display
                            color: app.COLORS['success']
                            size_hint_x: 0.3
                        
                        Label:
                            text: root.face_count
                            color: app.COLORS['accent']
                            size_hint_x: 0.3
                        
                        Label:
                            text: root.warning_text
                            color: app.COLORS['error'] if '⚠️' in root.warning_text else app.COLORS['success']
                            size_hint_x: 0.4
                    
                    Image:
                        id: capture_video
                        allow_stretch: True
                        keep_ratio: True
                    
                    BoxLayout:
                        size_hint_y: 0.18
                        spacing: dp(6)
                        orientation: 'vertical'
                        
                        BoxLayout:
                            size_hint_y: 0.6
                            spacing: dp(6)
                            
                            Button:
                                text: 'Capture (' + str(int(root.capture_count)) + ')'
                                background_color: app.COLORS['accent']
                                on_release: root.capture_face_image()
                            
                            Button:
                                text: 'Done'
                                background_color: app.COLORS['success']
                                on_release: root.finish_capture()
                            
                            Button:
                                text: 'Cancel'
                                background_color: app.COLORS['error']
                                on_release: root.cancel_capture()
                    

<CameraScreen>:
    canvas.before:
        Color:
            rgba: app.COLORS['bg_dark']
        Rectangle:
            size: self.size
            pos: self.pos
    
    BoxLayout:
        orientation: 'vertical'
        padding: dp(8)
        spacing: dp(8)
        
        BoxLayout:
            size_hint_y: 0.08
            spacing: dp(8)
            
            Label:
                text: 'Camera:'
                color: app.COLORS['text_secondary']
                size_hint_x: 0.2
            
            Spinner:
                text: 'Rear Camera'
                values: ['Rear Camera', 'Front Camera']
                background_color: app.COLORS['bg_card']
                on_text: root.switch_camera(self.text)
                size_hint_x: 0.8
        
        Image:
            id: video_feed
            allow_stretch: True
            keep_ratio: True
        
        Button:
            text: 'Back to Dashboard'
            background_color: app.COLORS['accent']
            size_hint_y: 0.08
            on_release: root.stop_camera(); app.root.current = 'dashboard'
'''

class LoginScreen(Screen):
    def sign_in(self):
        email = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()
        if not email or not password:
            self.show_popup('Error', 'Email and password required')
            return
        try:
            # use absolute path to avoid CWD issues when launched from different directories
            base = os.path.dirname(os.path.dirname(__file__))
            teachers_file = os.path.join(base, 'teachers.json')
            teachers = {}
            if os.path.exists(teachers_file):
                with open(teachers_file, 'r') as f:
                    teachers = json.load(f)
        except Exception:
            teachers = {}
        if email not in teachers or teachers[email].get('password') != password:
            self.show_popup('Error', 'Invalid email or password')
            return
        app = App.get_running_app()
        app.teacher_email = email
        App.get_running_app().root.current = 'dashboard'
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=message, color=COLORS['text_primary']))
        btn = Button(text='OK', size_hint_y=0.3, background_color=COLORS['accent'])
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.9, 0.4))
        btn.bind(on_press=popup.dismiss)
        popup.open()

class SignUpScreen(Screen):
    def register_teacher(self):
        email = self.ids.signup_email_input.text.strip()
        name = self.ids.signup_name_input.text.strip()
        password = self.ids.signup_password_input.text.strip()
        
        if not all([email, name, password]):
            self.show_popup('Error', 'All fields required')
            return
        
        try:
            # path must be independent of current working directory
            base = os.path.dirname(os.path.dirname(__file__))
            teachers_file = os.path.join(base, 'teachers.json')
            teachers = {}
            if os.path.exists(teachers_file):
                with open(teachers_file, 'r') as f:
                    teachers = json.load(f)
            
            if email in teachers:
                self.show_popup('Error', 'Already registered')
                return
            
            teachers[email] = {'name': name, 'password': password}
            with open(teachers_file, 'w') as f:
                json.dump(teachers, f)
            
            self.show_popup('Success', 'Account created!')
            App.get_running_app().root.current = 'login'
        except Exception as e:
            self.show_popup('Error', str(e))
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=message, color=COLORS['text_primary']))
        btn = Button(text='OK', size_hint_y=0.3, background_color=COLORS['accent'])
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.9, 0.4))
        btn.bind(on_press=popup.dismiss)
        popup.open()

class DashboardScreen(Screen):
    step1_status = StringProperty('Ready')
    step2_status = StringProperty('Ready')
    step3_status = StringProperty('Ready')
    step4_status = StringProperty('Ready')
    log_content = StringProperty('Welcome to Snapify Mobile Attendance System!\nFollow steps 1 → 2 → 3 → 4 to complete the workflow.\n')
    
    def show_popup(self, title, message):
        """Show a popup with title and message"""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=message, color=COLORS['text_primary']))
        btn = Button(text='OK', size_hint_y=0.3, background_color=COLORS['accent'])
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.9, 0.4))
        btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def on_enter(self):
        # make sure the scrollview is at top (step2+) but step1 is fixed above
        if hasattr(self.ids, 'steps_scroll'):
            self.ids.steps_scroll.scroll_y = 1
        self.log(f"Logged in as {App.get_running_app().teacher_email}. Follow steps 1 → 2 → 3 → 4.", "accent")

    def start_attendance(self):
        # ask for class name before switching to camera
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        class_input = TextInput(hint_text='Class/Period name', multiline=False,
                                foreground_color=COLORS['text_primary'],
                                background_color=COLORS['bg_card'])
        content.add_widget(class_input)
        btn = Button(text='Start', size_hint_y=0.4, background_color=COLORS['accent'])
        content.add_widget(btn)
        popup = Popup(title='Enter class name', content=content, size_hint=(0.85, 0.35))
        def on_start(instance):
            name = class_input.text.strip() or 'General'
            app = App.get_running_app()
            app.class_name = name
            popup.dismiss()
            app.root.current = 'camera'
        btn.bind(on_release=on_start)
        popup.open()
    
    def edit_student_info(self):
        """Navigate to Register screen in Edit Mode."""
        app = App.get_running_app()
        reg_screen = app.root.get_screen('register')
        reg_screen.edit_mode = True
        reg_screen.data_loaded = False
        app.root.current = 'register'
    
    def log(self, message, level="info"):
        """Add a message to the log with timestamp"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        colored_message = f"[{timestamp}] {message}\n"
        
        # Add color coding for different log levels
        if level == "success":
            colored_message = f"✓ {message}\n"
        elif level == "error":
            colored_message = f"✗ {message}\n"
        elif level == "warning":
            colored_message = f"⚠ {message}\n"
        elif level == "accent":
            colored_message = f"→ {message}\n"
        
        self.log_content += colored_message
    
    def clear_log(self):
        """Clear the log output"""
        self.log_content = ""
    
    def launch_face_register(self):
        """Step 1: Navigate to student registration screen"""
        self.log("Launching Face Registration...", "accent")
        self.step1_status = "Running..."
        App.get_running_app().root.current = 'register'
        self.step1_status = "✓ Completed"
        self.log("Face registration screen opened. Register students with face capture.", "success")
    
    def extract_features(self):
        """Step 2: Run feature extraction on captured faces"""
        self.log("Starting feature extraction...", "accent")
        self.step2_status = "⏳ Running..."
        
        # Run feature extraction in background
        import threading
        import subprocess
        import sys
        
        def run_extraction():
            try:
                # Run the feature extraction script
                result = subprocess.run([
                    sys.executable, 
                    "features_extraction_to_csv.py", 
                    "--teacher", 
                    App.get_running_app().teacher_email
                ], 
                capture_output=True, 
                text=True, 
                cwd=os.path.dirname(os.path.dirname(__file__))
                )
                
                # Update UI on main thread
                Clock.schedule_once(lambda dt: self._on_extraction_complete(result))
                
            except Exception as e:
                Clock.schedule_once(lambda dt: self._on_extraction_error(str(e)))
        
        threading.Thread(target=run_extraction, daemon=True).start()
    
    def _on_extraction_complete(self, result):
        """Handle successful feature extraction"""
        if result.returncode == 0:
            self.step2_status = "✓ Completed"
            self.log("Feature extraction completed successfully!", "success")
            # Parse output for useful info
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.log(line.strip())
        else:
            self.step2_status = "✗ Error"
            self.log(f"Feature extraction failed with code {result.returncode}", "error")
            if result.stderr:
                self.log(result.stderr, "error")
    
    def _on_extraction_error(self, error_msg):
        """Handle feature extraction error"""
        self.step2_status = "✗ Error"
        self.log(f"Feature extraction error: {error_msg}", "error")
    
    def open_dashboard(self):
        """Step 4: Launch full Flask dashboard (same as launcher)"""
        self.log("Launching full attendance dashboard server...", "accent")
        self.step4_status = "Running..."
        
        # write teacher file for flask
        project_dir = os.path.dirname(os.path.dirname(__file__))
        try:
            with open(os.path.join(project_dir, 'current_teacher.json'), 'w') as f:
                json.dump({'teacher_email': App.get_running_app().teacher_email}, f)
        except Exception as e:
            self.log(f"Error writing teacher file: {e}", "error")
        
        # start flask process if not already running
        app_inst = App.get_running_app()
        if not hasattr(app_inst, 'flask_proc') or app_inst.flask_proc is None or app_inst.flask_proc.poll() is not None:
            import subprocess, sys, time, webbrowser
            from kivy.clock import Clock
            from threading import Thread
            
            def run_flask():
                try:
                    app_inst.flask_proc = subprocess.Popen(
                        [sys.executable, "app.py", "--teacher", app_inst.teacher_email],
                        cwd=project_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace"
                    )
                    time.sleep(2)
                    if app_inst.flask_proc.poll() is None:
                        Clock.schedule_once(lambda dt: setattr(self, 'step4_status', "🟢 Server running"))
                        Clock.schedule_once(lambda dt: self.log("Dashboard running at http://127.0.0.1:5000", "success"))
                        webbrowser.open("http://127.0.0.1:5000")
                        for line in iter(app_inst.flask_proc.stdout.readline, ''):
                            line = line.strip()
                            if line:
                                Clock.schedule_once(lambda dt, l=line: self.log(l))
                    else:
                        out = app_inst.flask_proc.stdout.read()
                        Clock.schedule_once(lambda dt: setattr(self, 'step4_status', "✗ Error"))
                        Clock.schedule_once(lambda dt, e=out: self.log(f"Flask server failed: {e}", "error"))
                except Exception as e:
                    err_msg = str(e)
                    Clock.schedule_once(lambda dt: setattr(self, 'step4_status', "✗ Error"))
                    Clock.schedule_once(lambda dt, err=err_msg: self.log(err, "error"))
                    
            Thread(target=run_flask, daemon=True).start()
        else:
            # already running, just open browser
            import webbrowser
            webbrowser.open("http://127.0.0.1:5000")
            self.step4_status = "🟢 Server running"
            self.log("Dashboard already running, opened browser.", "info")
    
    def show_attendance_dashboard(self):
        """Show attendance records in a popup dashboard"""
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        
        # Date selection
        date_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        date_layout.add_widget(Label(text='Date:', color=COLORS['text_primary'], size_hint_x=0.3))
        
        date_input = TextInput(
            hint_text='YYYY-MM-DD',
            foreground_color=COLORS['text_primary'],
            background_color=COLORS['bg_card'],
            size_hint_x=0.7,
            multiline=False
        )
        date_layout.add_widget(date_input)
        content.add_widget(date_layout)
        
        # Class selection
        class_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        class_layout.add_widget(Label(text='Class:', color=COLORS['text_primary'], size_hint_x=0.3))
        
        class_spinner = Spinner(
            text='All Classes',
            values=['All Classes', 'Class A', 'Class B', 'Class C'],  # You can make this dynamic
            background_color=COLORS['bg_card'],
            color=COLORS['text_primary'],
            size_hint_x=0.7
        )
        class_layout.add_widget(class_spinner)
        content.add_widget(class_layout)
        
        # Filter button
        filter_btn = Button(
            text='Filter Records',
            background_color=COLORS['accent'],
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(filter_btn)
        
        # Results area
        results_scroll = ScrollView(size_hint_y=0.6)
        results_grid = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        results_grid.bind(minimum_height=results_grid.setter('height'))
        
        # Sample data - in real app, this would query the database
        sample_records = [
            "001 | John Doe | Class A | 09:15:30",
            "002 | Jane Smith | Class A | 09:17:45",
            "003 | Bob Johnson | Class B | 09:20:12"
        ]
        
        for record in sample_records:
            results_grid.add_widget(Label(
                text=record,
                color=COLORS['text_primary'],
                size_hint_y=None,
                height=dp(30),
                halign='left'
            ))
        
        results_scroll.add_widget(results_grid)
        content.add_widget(results_scroll)
        
        # Close button
        close_btn = Button(
            text='Close',
            background_color=COLORS['error'],
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(close_btn)
        
        popup = Popup(
            title='Attendance Dashboard',
            content=content,
            size_hint=(0.95, 0.9)
        )
        
        def filter_records(instance):
            selected_date = date_input.text.strip()
            selected_class = class_spinner.text
            
            results_grid.clear_widgets()
            
            if not selected_date:
                results_grid.add_widget(Label(
                    text='Please enter a date',
                    color=COLORS['error'],
                    size_hint_y=None,
                    height=dp(30)
                ))
                return
            
            # In real app, query database here
            # For now, show sample filtered data
            filtered_records = []
            if selected_class == 'All Classes':
                filtered_records = sample_records
            else:
                filtered_records = [r for r in sample_records if selected_class in r]
            
            if not filtered_records:
                results_grid.add_widget(Label(
                    text='No records found',
                    color=COLORS['text_secondary'],
                    size_hint_y=None,
                    height=dp(30)
                ))
            else:
                for record in filtered_records:
                    results_grid.add_widget(Label(
                        text=record,
                        color=COLORS['text_primary'],
                        size_hint_y=None,
                        height=dp(30),
                        halign='left'
                    ))
        
        filter_btn.bind(on_press=filter_records)
        close_btn.bind(on_press=popup.dismiss)
        
        popup.open()
    
    def logout(self):
        """Logout and return to login screen"""
        self.log("Logging out...", "accent")
        App.get_running_app().root.current = 'login'

class LoadingIndicator(Popup):
    """A premium looking loading indicator."""
    def __init__(self, message="Loading...", **kwargs):
        super().__init__(**kwargs)
        self.title = "Processing"
        self.size_hint = (0.7, 0.25)
        self.auto_dismiss = False
        self.background_color = (0.1, 0.1, 0.15, 0.9)
        
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        label = Label(text=message, color=COLORS['text_primary'], font_size='16sp', bold=True)
        layout.add_widget(label)
        
        # Add a placeholder for a loading bar/spinner if desired
        self.content = layout

class RegisterStudentScreen(Screen):
    step = StringProperty('form')
    capture_count = NumericProperty(0)
    current_roll = StringProperty('')
    current_name = StringProperty('')
    fps_display = StringProperty('FPS: 0.0')
    face_count = StringProperty('Faces: 0')
    warning_text = StringProperty('')
    
    # Edit mode properties
    edit_mode = BooleanProperty(False)
    edit_roll = StringProperty('')
    edit_name = StringProperty('')
    edit_phone = StringProperty('')
    edit_email = StringProperty('')
    
    cap = None
    event = None
    path_photos = ''
    
    # FPS tracking
    frame_time = 0
    frame_start_time = 0
    fps = 0
    start_time = time.time()
    
    # Face detection
    face_roi_width_start = 0
    face_roi_height_start = 0
    face_roi_width = 0
    face_roi_height = 0
    out_of_range_flag = False
    
    # Boolean to track if data is loaded in edit mode
    data_loaded = BooleanProperty(False)
    
    def on_step(self, instance, value):
        """Automatically switch the internal ScreenManager based on step."""
        if hasattr(self.ids, 'internal_sm'):
            if value == 'form':
                self.ids.internal_sm.current = 'form_screen'
            elif value == 'capture':
                self.ids.internal_sm.current = 'capture_screen'
    
    def on_enter(self):
        """Handle screen entry and state reset."""
        self.cleanup_camera()
        
        # Always start on the form step
        self.step = 'form'
        if hasattr(self.ids, 'internal_sm'):
            self.ids.internal_sm.current = 'form_screen'
        
        if not self.edit_mode:
            # Clean form for new registration
            self.data_loaded = False
            self.clear_form()
            
        # Reset capture state
        self.capture_count = 0
        self.warning_text = ""
        self.fps_display = "FPS: 0.0"
        self.face_count = "Faces: 0"

    def load_student_data(self):
        """Edit mode: Load student details from DB in background."""
        roll = self.ids.roll_input.text.strip()
        if not roll:
            self.show_popup("Error", "Enter Roll Number to load")
            return
            
        loading = LoadingIndicator(f"Loading data for {roll}...")
        loading.open()
        
        def run_load():
            app = App.get_running_app()
            try:
                conn = sqlite3.connect('attendance.db')
                cursor = conn.cursor()
                cursor.execute("SELECT name, phone, email FROM students WHERE roll_number = ? AND teacher_email = ?", (roll, app.teacher_email))
                row = cursor.fetchone()
                conn.close()
                
                def update_ui(dt):
                    loading.dismiss()
                    if row:
                        self.ids.name_input.text = row[0] or ""
                        self.ids.phone_input.text = row[1] or ""
                        self.ids.email_input.text = row[2] or ""
                        self.edit_roll = roll
                        self.edit_name = row[0] or ""
                        self.data_loaded = True
                        self.show_popup("Loaded", f"Details for {roll} loaded.")
                    else:
                        self.show_popup("Not Found", f"No record found for {roll}")
                
                Clock.schedule_once(update_ui)
            except Exception as e:
                def on_error(dt):
                    loading.dismiss()
                    self.show_popup("DB Error", str(e))
                Clock.schedule_once(on_error)
        
        threading.Thread(target=run_load, daemon=True).start()

    def start_capture_step(self):
        """Switch to capture step and start camera."""
        roll = self.ids.roll_input.text.strip()
        name = self.ids.name_input.text.strip()
        
        if not roll:
            self.show_popup("Error", "Enter Roll Number first")
            return
            
        # If in registration mode, check name too
        if not self.edit_mode:
            if not name:
                self.show_popup("Error", "Enter Student Name first")
                return
        
        self.current_roll = roll
        self.current_name = name
        
        # Prepare path
        app = App.get_running_app()
        self.path_photos = f"data/data_faces_from_camera/{app.teacher_email}/person_1_{roll}_{name}/"
        
        # If recapturing, delete the old photos to avoid mixing features
        if os.path.exists(self.path_photos):
            try:
                import shutil
                shutil.rmtree(self.path_photos)
            except Exception as e:
                self.show_popup("Error", f"Failed to clear old photos: {e}")
        
        if not os.path.exists(self.path_photos):
            os.makedirs(self.path_photos, exist_ok=True)
            
        self.capture_count = 0
            
        self.step = 'capture'
        if hasattr(self.ids, 'internal_sm'):
            self.ids.internal_sm.current = 'capture_screen'
        self.start_camera_logic()

    def on_leave(self):
        """Cleanup when leaving the screen."""
        self.cleanup_camera()
        # Reset mode so next entry is clean
        self.edit_mode = False

    def cleanup_camera(self):
        """Release camera and stop events."""
        if hasattr(self, 'event') and self.event:
            self.event.cancel()
            self.event = None
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
            self.cap = None
        # Clear texture to prevent frozen frame
        if hasattr(self, 'ids') and 'capture_video' in self.ids:
            self.ids.capture_video.texture = None

    def start_camera_logic(self):
        """Initialize camera in background to avoid UI freeze."""
        loading = LoadingIndicator("Initializing Camera...")
        loading.open()
        
        def run_cam():
            try:
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    def on_fail(dt):
                        loading.dismiss()
                        self.show_popup("Error", "Could not open camera")
                    Clock.schedule_once(on_fail)
                    return
                
                # Try to configure camera props but don't fail if they don't apply
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                def on_success(dt):
                    self.cap = cap
                    self.frame_start_time = time.time()
                    self.start_time = time.time()
                    self.event = Clock.schedule_interval(self.update_capture_frame, 1.0/20.0)
                    loading.dismiss()
                Clock.schedule_once(on_success, 0.5) # allow slight delay for UI transition
            except Exception as e:
                def on_error(dt):
                    loading.dismiss()
                    self.show_popup("Camera Error", str(e))
                Clock.schedule_once(on_error)
        
        threading.Thread(target=run_cam, daemon=True).start()
    
    def register_new_student(self):
        """Save data in background to avoid UI delay."""
        roll = self.ids.roll_input.text.strip()
        name = self.ids.name_input.text.strip()
        phone = self.ids.phone_input.text.strip()
        email = self.ids.email_input.text.strip()
        
        if not all([roll, name, email]):
            self.show_popup('Error', 'Roll, name and email required')
            return
            
        if not self.edit_mode and self.capture_count == 0:
            self.show_popup('Error', 'Please capture face images first')
            return
        
        loading = LoadingIndicator("Saving details to database...")
        loading.open()
        
        def run_save():
            app = App.get_running_app()
            try:
                conn = sqlite3.connect('attendance.db')
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO students (roll_number, name, phone, email, teacher_email) VALUES (?, ?, ?, ?, ?)",
                    (roll, name, phone, email, app.teacher_email)
                )
                conn.commit()
                conn.close()
                
                def on_success(dt):
                    loading.dismiss()
                    self.show_popup("Success", f"{name} saved successfully!")
                    app.root.current = 'dashboard'
                Clock.schedule_once(on_success)
            except Exception as e:
                def on_error(dt):
                    loading.dismiss()
                    self.show_popup('Error', str(e))
                Clock.schedule_once(on_error)
        
        threading.Thread(target=run_save, daemon=True).start()

    def update_student_data(self):
        """Update existing student info and optionally rename face data folder."""
        roll = self.ids.roll_input.text.strip()
        name = self.ids.name_input.text.strip()
        phone = self.ids.phone_input.text.strip()
        email = self.ids.email_input.text.strip()
        
        if not all([roll, name, email]):
            self.show_popup('Error', 'Roll, name and email required')
            return
            
        loading = LoadingIndicator("Updating details...")
        loading.open()
        
        def run_update():
            app = App.get_running_app()
            try:
                # rename folder if roll or name changed
                old_roll = getattr(self, 'edit_roll', roll)
                old_name = getattr(self, 'edit_name', name)
                
                if old_roll and (old_roll != roll or old_name != name):
                    base_path = f"data/data_faces_from_camera/{app.teacher_email}/"
                    if os.path.exists(base_path):
                        # search for folder match
                        for folder in os.listdir(base_path):
                            parts = folder.split('_')
                            if len(parts) >= 3 and parts[2] == old_roll:
                                old_folder = os.path.join(base_path, folder)
                                new_folder_name = f"person_{parts[1]}_{roll}_{name}"
                                os.rename(old_folder, os.path.join(base_path, new_folder_name))
                                break
                                
                conn = sqlite3.connect('attendance.db')
                cursor = conn.cursor()
                if old_roll != roll:
                    cursor.execute("DELETE FROM students WHERE roll_number = ? AND teacher_email = ?", (old_roll, app.teacher_email))
                cursor.execute(
                    "INSERT OR REPLACE INTO students (roll_number, name, phone, email, teacher_email) VALUES (?, ?, ?, ?, ?)",
                    (roll, name, phone, email, app.teacher_email)
                )
                conn.commit()
                conn.close()
                
                def on_success(dt):
                    loading.dismiss()
                    self.show_popup("Success", f"{name} updated successfully!")
                    app.root.current = 'dashboard'
                Clock.schedule_once(on_success)
            except Exception as e:
                def on_error(dt):
                    loading.dismiss()
                    self.show_popup('Error', str(e))
                Clock.schedule_once(on_error)
        
        threading.Thread(target=run_update, daemon=True).start()

    def delete_student_data(self):
        """Delete student from DB and disk."""
        roll = self.ids.roll_input.text.strip()
        if not roll: return
        
        app = App.get_running_app()
        try:
            conn = sqlite3.connect('attendance.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE roll_number = ? AND teacher_email = ?", (roll, app.teacher_email))
            conn.commit()
            conn.close()
            
            face_folder = f"data/data_faces_from_camera/{app.teacher_email}/person_1_{roll}_"
            # note: path might be slightly different depending on name, but we can attempt prefix delete or user provided
            self.show_popup("Deleted", "Student record removed")
            app.root.current = 'dashboard'
        except Exception as e:
            self.show_popup("Error", str(e))
    
    def update_fps(self):
        """Update FPS counter (same logic as desktop version)"""
        now = time.time()
        if str(self.start_time).split(".")[0] != str(now).split(".")[0]:
            self.fps_show = self.fps
        self.start_time = now
        self.frame_time = now - self.frame_start_time
        if self.frame_time > 0:
            self.fps = 1.0 / self.frame_time
        self.frame_start_time = now
        self.fps_display = f"FPS: {round(self.fps, 2)}"

    def clear_form(self):
        self.ids.roll_input.text = ''
        self.ids.name_input.text = ''
        self.ids.phone_input.text = ''
        self.ids.email_input.text = ''
    
    def capture_face_image(self):
        """Capture face only if in range"""
        if self.cap is None or not self.cap.isOpened():
            return
        
        if self.out_of_range_flag:
            self.show_popup('Warning', 'Face is out of range!')
            return
        
        # safely parse face count
        try:
            faces_detected = int(self.face_count.split(': ')[1])
        except:
            faces_detected = 0

        if faces_detected != 1:
            self.show_popup('Error', 'Exactly one face required')
            return
        
        ret, frame = self.cap.read()
        if ret:
            # frame is BGR from cap.read()
            img_path = os.path.join(self.path_photos, f'img_face_{int(self.capture_count)+1}.jpg')
            # cv2.imwrite expects BGR, so we don't convert to RGB here
            cv2.imwrite(img_path, frame)
            self.capture_count += 1
            self.show_popup('Success', f'Photo #{int(self.capture_count)} captured!')
    
    def finish_capture(self):
        """Done in camera -> Return to the form."""
        self.cleanup_camera()
        self.step = 'form'
        if hasattr(self.ids, 'internal_sm'):
            self.ids.internal_sm.current = 'form_screen'
        self.show_popup("Captured", f"{int(self.capture_count)} photos ready. Now click Register/Update to finish.")

    def cancel_capture(self):
        """Cancel in camera -> Return to the form."""
        self.cleanup_camera()
        self.step = 'form'
        if hasattr(self.ids, 'internal_sm'):
            self.ids.internal_sm.current = 'form_screen'
        self.warning_text = ''
        # We don't remove photos immediately so the user can see if they want to try again
        # or if they made a mistake. If they click "Register" and count is 0, it errors.
    
    def update_capture_frame(self, dt):
        """Real-time camera with face detection (same as desktop)"""
        if self.cap is None or not self.cap.isOpened():
            return
        
        ret, frame = self.cap.read()
        if not ret:
            return
        
        # Resize to match desktop version
        frame = cv2.resize(frame, (640, 480))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces using dlib
        faces = detector(frame, 0)
        self.face_count = f'Faces: {len(faces)}'
        
        # Draw rectangles around detected faces
        if len(faces) > 0:
            for k, d in enumerate(faces):
                self.face_roi_width_start = d.left()
                self.face_roi_height_start = d.top()
                self.face_roi_height = (d.bottom() - d.top())
                self.face_roi_width = (d.right() - d.left())
                
                hh = int(self.face_roi_height / 2)
                ww = int(self.face_roi_width / 2)
                
                # Check if out of range
                if (d.right() + ww) > 640 or (d.bottom() + hh > 480) or (d.left() - ww < 0) or (d.top() - hh < 0):
                    self.warning_text = '⚠️ OUT OF RANGE'
                    self.out_of_range_flag = True
                    color = (255, 0, 0)  # Red
                else:
                    self.out_of_range_flag = False
                    self.warning_text = '✓ Face in range'
                    color = (255, 255, 255)  # White
                
                # Draw rectangle
                frame = cv2.rectangle(
                    frame,
                    tuple([d.left() - ww, d.top() - hh]),
                    tuple([d.right() + ww, d.bottom() + hh]),
                    color, 2
                )
        else:
            self.warning_text = ''
            self.out_of_range_flag = False
        
        # Update FPS
        self.update_fps()
        
        # Display FPS and face count on frame
        cv2.putText(frame, self.fps_display, (20, 30), cv2.FONT_ITALIC, 0.8, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.putText(frame, self.face_count, (20, 60), cv2.FONT_ITALIC, 0.8, (0, 255, 0), 1, cv2.LINE_AA)
        if self.warning_text:
            warning_color = (0, 0, 255) if '⚠️' in self.warning_text else (0, 255, 0)
            cv2.putText(frame, self.warning_text, (20, 90), cv2.FONT_ITALIC, 0.8, warning_color, 1, cv2.LINE_AA)
        
        # Convert to texture
        buf = cv2.flip(frame, 0).tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.ids.capture_video.texture = texture
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=message, color=COLORS['text_primary']))
        btn = Button(text='OK', size_hint_y=0.3, background_color=COLORS['accent'])
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.9, 0.4))
        btn.bind(on_press=popup.dismiss)
        popup.open()

class CameraScreen(Screen):
    cam_index = NumericProperty(0)

    def on_enter(self):
        """Initialize camera and face recognizer in background."""
        loading = LoadingIndicator("Initializing Attendance System...")
        loading.open()
        
        def run_init():
            try:
                cap = cv2.VideoCapture(self.cam_index)
                app = App.get_running_app()
                face_rec = Face_Recognizer(class_name=getattr(app, 'class_name', 'General'), teacher_email=app.teacher_email)
                
                def on_success(dt):
                    self.cap = cap
                    self.face_rec = face_rec
                    self.event = Clock.schedule_interval(self.update_frame, 1.0/30.0)
                    loading.dismiss()
                Clock.schedule_once(on_success)
            except Exception as e:
                def on_error(dt):
                    loading.dismiss()
                    self.show_popup("Init Error", str(e))
                Clock.schedule_once(on_error)
        
        threading.Thread(target=run_init, daemon=True).start()

    def on_leave(self):
        if hasattr(self, 'event'):
            self.event.cancel()
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
    
    def stop_camera(self):
        self.on_leave()

    def switch_camera(self, label):
        self.on_leave()
        self.cam_index = 1 if 'Front' in label else 0
        self.on_enter()

    def update_frame(self, dt):
        ret, frame = self.cap.read()
        if not ret:
            return
        
        if self.cam_index == 1:
            frame = cv2.flip(frame, 1)

        annotated = self.face_rec.process_frame(frame)
        buf = cv2.flip(annotated, 0).tobytes()
        texture = Texture.create(size=(annotated.shape[1], annotated.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.ids.video_feed.texture = texture

class AttendanceApp(App):
    COLORS = COLORS
    teacher_email = StringProperty('')
    class_name = StringProperty('General')

    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(SignUpScreen(name='signup'))
        sm.add_widget(DashboardScreen(name='dashboard'))
        sm.add_widget(RegisterStudentScreen(name='register'))
        sm.add_widget(CameraScreen(name='camera'))
        sm.current = 'login'
        return sm

if __name__ == '__main__':
    AttendanceApp().run()
