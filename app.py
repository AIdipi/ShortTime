from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
from werkzeug.utils import secure_filename
import subprocess
import cv2

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
