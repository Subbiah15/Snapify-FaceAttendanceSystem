# Face Recognition Based Attendance System

This project is a face recognition-based attendance system that uses OpenCV and Python. The system uses a camera to capture images of individuals and then compares them with the images in the database to mark attendance.

## Installation

1. Clone the repository to your local machine. ``` git clone https://github.com/Arijit1080/Face-Recognition-Based-Attendance-System ```
2. Install the required packages using ```pip install -r requirements.txt```.
3. Download the dlib models from https://drive.google.com/drive/folders/12It2jeNQOxwStBxtagL1vvIJokoz-DL4?usp=sharing and place the data folder inside the repo

## Usage

1. Collect the Faces Dataset by running ``` python get_faces_from_camera_tkinter.py``` .
2. Convert the dataset into ```python features_extraction_to_csv.py```.
3. To take the attendance run ```python attendance_taker.py``` .
4. Check the Database by ```python app.py```.

## Mobile application (Kivy)

A standalone mobile version uses the same backend logic and provides a similar
UI with front/back camera switching. The code lives in `mobile_app/main.py`.

### Running on desktop for testing

```bash
pip install -r requirements.txt   # includes kivy
python mobile_app/main.py
```

### Building for Android

1. Install [Buildozer](https://buildozer.readthedocs.io/).
2. From the repo root, run: ```buildozer init``` to create `buildozer.spec`.
3. In the spec file, set `source.include_exts = py,kv,db,json,csv` and add
   `requirements = python3,kivy,opencv-python,dlib,numpy,pandas`.
4. Build the APK with ```buildozer android debug``` and install it on the device.

### Building for iOS

Follow the [Kivy iOS documentation](https://kivy.org/doc/stable/guide/packaging-ios.html)
using Briefcase/Toolchain; requirements are the same.

> The mobile app works entirely offline—emailing is disabled and any
> network-dependent features are omitted.  Camera selection uses a spinner to
> toggle between rear and front-facing devices.


## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you find any bugs or have any suggestions.


