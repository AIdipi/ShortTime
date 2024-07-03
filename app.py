from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
import subprocess
import cv2
import numpy as np
from ultralytics import YOLO

from ultralytics.utils.checks import check_imshow
from ultralytics.utils.plotting import Annotator, colors

from collections import defaultdict

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4'}
app.config['PROCESS_FOLDER'] = 'process'
app.config['RESULTS_FOLDER'] = 'results'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists(app.config['PROCESS_FOLDER']):
    os.makedirs(app.config['PROCESS_FOLDER'])

if not os.path.exists(app.config['RESULTS_FOLDER']):
    os.makedirs(app.config['RESULTS_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Run the tracking script
        reid_model_path = 'osnet_x0_25_msmt17.pt' # reid 모델 불러오기
        project_path = app.config['RESULTS_FOLDER'] # 결과를 저장한 디렉터리 이름(results)
        name = filename.rsplit('.', 1)[0]

        try:
            command = f'python tracking/track.py --source {file_path} --reid-model {reid_model_path} --save --project {project_path} --name {name} --save-id-crops --show-conf'
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError as e:
            return f"An error occurred: {e}"

        return redirect(url_for('result', name=name))

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         return redirect(request.url)
#     file = request.files['file']
#     if file.filename == '':
#         return redirect(request.url)
#     if file and allowed_file(file.filename):
#         filename = secure_filename(file.filename)
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(file_path)
#
#         # Run the tracking script
#         reid_model_path = 'osnet_x0_25_msmt17.pt' # reid 모델 불러오기
#         project_path = app.config['RESULTS_FOLDER'] # 결과를 저장한 디렉터리 이름(results)
#         name = filename.rsplit('.', 1)[0]
#
#         # try:
#         #     command = f'python tracking/track.py --source {file_path} --reid-model {reid_model_path} --save --project {project_path} --name {name} --save-id-crops --show-conf'
#         #     subprocess.check_call(command, shell=True)
#         # except subprocess.CalledProcessError as e:
#         #     return f"An error occurred: {e}"
#
#         select_id = 2  # 선택한 id(추후 변수 처리)
#
#         frame_number = 0
#         p_boxes = []
#         track_history = defaultdict(lambda: [])
#         model = YOLO("osnet_x0_25_msmt17.pt")  # 모델 불러옴
#         names = model.model.names
#
#         cap = cv2.VideoCapture(file_path)  # 프레임 따기
#         w, h, fps = (int(cap.get(x)) for x in
#                      (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))  # 프레임 크기 저장
#         result = cv2.VideoWriter(file_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
#
#         while cap.isOpened():
#             success, frame = cap.read()
#             if success:
#                 frame_number += 1  # 프레임 번호 증가
#                 results = model.track(frame, persist=True, verbose=False)
#                 boxes = results[0].boxes.xyxy.cpu()
#
#                 if results[0].boxes.id is not None:
#
#                     # Extract prediction results
#                     clss = results[0].boxes.cls.cpu().tolist()  # 탐지된 객체들
#                     track_ids = results[0].boxes.id.int().cpu().tolist()  # 객체 추적 id
#                     confs = results[0].boxes.conf.float().cpu().tolist()  # 신뢰도
#
#                     annotator = Annotator(frame, line_width=2)  # Annotator 객체 생성, 박스 라인 두께 2
#
#                     for box, cls, track_id in zip(boxes, clss, track_ids):
#                         if cls == 0.0:  # person으로 분류된 객체만
#
#                             if track_id == select_id:
#                                 # 클래스 이름과 추적 ID를 라벨에 포함시키기
#                                 label = f"{names[int(cls)]} {int(track_id)}"
#                                 annotator.box_label(box, color=colors(int(cls), True), label=label)
#
#                                 # Store tracking history
#                                 track = track_history[track_id]
#                                 track.append((int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)))
#
#                                 # Plot tracks
#                                 points = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
#                                 cv2.circle(frame, (track[-1]), 7, colors(int(cls), True), -1)
#                                 cv2.polylines(frame, [points], isClosed=False, color=colors(int(cls), True),
#                                               thickness=2)
#                                 print("framenum : %s, id : %s, box 좌표: %s" % (frame_number, track_id, box))
#                                 p_boxes.append([frame_number, box.tolist()])
#                 result.write(frame)
#                 if cv2.waitKey(1) & 0xFF == ord("q"):
#                     break
#             else:
#                 break
#
#         result.release()
#         cap.release()
#         cv2.destroyAllWindows()
#         print("%s : ID: %s, 검출 완료" % (filename, select_id))
#
#         return redirect(url_for('result', name=name))


@app.route('/result')
def result():
    name = request.args.get('name')
    video_path = os.path.join(name, name +'.mp4')  # Adjust as needed for the actual output video filename
    return render_template('result.html', video_path=video_path)


@app.route('/results/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)


if __name__ == "__main__":
    app.run(debug=True)
