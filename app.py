from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
from pathlib import Path
from boxmot import DeepOCSORT
import cv2
from ultralytics import YOLO
import numpy as np
from video import frame_to_time, clip_video, crop_frame

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
        filename = secure_filename(file.filename) # 안전한 파일명으로 바꿈 ex. '/' or '\' 제거
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # # Run the tracking script
        reid_model_path = "osnet_x0_25_msmt17.pt" # reid 모델 불러오기
        project_path = app.config['RESULTS_FOLDER'] # 결과를 저장한 디렉터리 이름(results)
        name = filename.rsplit('.', 1)[0]

        select_id = 1  # 선택한 id(추후 변수 처리)

        frame_count = 0
        p_boxes = []
        newboxes = []
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
                track_ids = tracks[:, -1].tolist()
                # for track in tracks: # track = [x1,y1,x2,y2, [trk.id], [trk.conf], [trk.cls], [trk.det_ind]]
                for box, track_id in zip(boxes, track_ids):
                    x1, y1, x2, y2 = box
                    track_id = int(track_id)
                    p_box = [frame_count, x1, y1, x2, y2, track_id]
                    # print(f"Frame {frame_count}: ID {track_id} Bounding Box: {box}")
                    p_boxes.append(p_box)

                for box in p_boxes:
                    frame_count, x1, y1, x2, y2, id = box
                    if id == select_id - 1:
                        print(f"Frame {frame_count}")
                        newboxes.append([frame_count, x1, y1, x2, y2, id])

                out.write(frame)
            else:
                break

        print(newboxes)
        s_frame_num = int(newboxes[0][0])
        e_frame_num = int(newboxes[-1][0])
        s_time = frame_to_time(s_frame_num, fps)
        e_time = frame_to_time(e_frame_num, fps)
        print(s_time, e_time)

        output_path = os.path.join(app.config['PROCESS_FOLDER'], name)
        clip_video(name, file_path, s_time, e_time, output_path)
        crop_frame(newboxes, name, output_path)


        #
        # result.release()
        # cap.release()
        # cv2.destroyAllWindows()
        return redirect(url_for('result', name=name))


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
