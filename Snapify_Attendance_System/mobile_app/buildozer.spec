[app]

# (str) Title of your application
title = Snapify Attendance

# (str) Package name
package.name = snapify_attendance

# (str) Package domain (needed for android/ios packaging)
package.domain = org.arijit

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,ttf,db,dat,csv

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,opencv,numpy,sqlite3,dlib,pandas

# (str) Custom source folders for requirements
# (list) List of paths to your own python modules
#source.include_ids = 

# (str) Application versioning (method 1)
version = 0.1

# (list) Permissions
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET

# (int) Target Android API, should be as high as possible.
android.api = 31

# (int) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
#android.ndk = 25b

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android entry point, default is to use main.py
#android.entrypoint = main.py

# (list) Pattern to exclude for the search
#android.exclude_exts = spec

# (str) Full name used for the Android app
android.app_name = Snapify Attendance

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (bool) Allow backup
android.allow_backup = True

# (list) List of service to declare
#services = NAME:ENTRYPOINT_PY

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2
android.api = 31
android.minapi = 21
android.sdk = 31
android.ndk = 25b
android.build_tools = 30.0.3

# (int) Display warning if buildozer is run as root (0 = off, 1 = on)
warn_on_root = 1

# (str) python-for-android branch to use, defaults to master
p4a.branch = master
