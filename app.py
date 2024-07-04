from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
from pathlib import Path
from boxmot import DeepOCSORT
import subprocess
import cv2
from ultralytics import YOLO
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4'}
app.config['RESULTS_FOLDER'] = 'results'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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

        # # Run the tracking script
        reid_model_path = "osnet_x0_25_msmt17.pt" # reid 모델 불러오기
        project_path = app.config['RESULTS_FOLDER'] # 결과를 저장한 디렉터리 이름(results)
        name = filename.rsplit('.', 1)[0]
        #
        # try:
        #     command = f'python tracking/track.py --source {file_path} --reid-model {reid_model_path} --save --project {project_path} --name {name} --save-id-crops --show-conf'
        #     subprocess.check_call(command, shell=True)
        # except subprocess.CalledProcessError as e:
        #     return f"An error occurred: {e}"

        select_id = 1  # 선택한 id(추후 변수 처리)

        frame_count = 0
        p_boxes = []
        tracker = DeepOCSORT(
            model_weights=Path(reid_model_path),
            device='cpu',
            fp16=False
        )

        cap = cv2.VideoCapture(file_path)  # 프레임 따기
        w, h, fps = (int(cap.get(x)) for x in
                     (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))  # 프레임 크기 저장

        out = cv2.VideoWriter(project_path+'/'+filename,
                                 cv2.VideoWriter_fourcc(*'mp4v'),
                                 fps,
                                 (w, h))
        model = YOLO("tracking/weights/yolov8n.pt")

        while cap.isOpened():
            frame_count += 1
            success, frame = cap.read()
            if success:
                results = model(frame)
                dets = []

                for result in results:
                    for detection in result.boxes.data.cpu().numpy():
                        x1, y1, x2, y2, conf, cls = detection
                        dets.append([x1, y1, x2, y2, conf, int(cls)])
                dets = np.array(dets)

                tracker.set_track_id(select_id)
                tracks = tracker.update(dets, frame)
                # print(tracks)

                boxes = tracks[:, :4].tolist()
                track_ids = tracks[:, -1].int().tolist()



                # for track in tracks: # track = [x1,y1,x2,y2, [trk.id], [trk.conf], [trk.cls], [trk.det_ind]]

                for box, track_id in zip(boxes, track_ids):
                    x1, y1, x2, y2 = box
                    print(f"Frame {frame_count}: ID {track_id} Bounding Box: {box} Bounding Box: ({x1}, {y1}, {x2}, {y2})")
                    p_boxes.append([frame_count, [track_id, box]])
                    print(p_boxes)

                out.write(frame)

            else:
                break
        #
        # result.release()
        # cap.release()
        # cv2.destroyAllWindows()
        return redirect(url_for('result', name=name))

    # 프레임을 시간 단위로 변경
    def frame_to_time(frame_count, fps):
        total_seconds = frame_count / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"




@app.route('/result')
def result():
    name = request.args.get('name')
    video_path = os.path.join(name +'.mp4')  # Adjust as needed for the actual output video filename
    print(video_path)
    return render_template('result.html', video_path=video_path)


@app.route('/results/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)


if __name__ == "__main__":
    # app.run(debug=True)
    app.run()
