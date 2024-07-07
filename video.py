import subprocess
import os

# 프레임을 시간 단위로 변경
def frame_to_time(frame_count, fps):
    total_seconds = frame_count / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

# 특정 구간 오디오 추출
def clip_audio(file_name, input_path, start_time, end_time, output_path):
    audio_file = f'{file_name}_audio'

    output_file_path = os.path.join(output_path, f"{audio_file}.mp3")

    command = f'ffmpeg -i "{input_path}" -ss {start_time} -to {end_time} -vn -acodec libmp3lame "{output_file_path}"'

    try:
        result = subprocess.run(command, shell=True, capture_output=True)  # ffmpeg 명령어 실행
        print("오디오 추출 성공 : ", file_name)
        print(result.stdout.decode())  # 표준 출력 메세지 출력
        return output_file_path

    except subprocess.CalledProcessError as e:
        print("오디오 추출 중 오류 발생:")
        print(e.stderr.decode())  # 에러 메세지 출력
        return output_file_path

# 특정 구간 비디오 추출
def clip_video(file_name, input_path, start_time, end_time, output_path):
    file_name = f'{file_name}_video'
    os.makedirs(output_path, exist_ok=True)

    output_file_path = os.path.join(output_path, f"{file_name}.mp4")

    command = f'ffmpeg -ss {start_time} -to {end_time} -i "{input_path}" -c:v libx264 -preset fast -crf 22 -c:a aac "{output_file_path}"'

    try:
        result = subprocess.run(command, shell=True, capture_output=True, check=True)  # ffmpeg 명령어 실행
        print("비디오 추출 성공 : ", file_name)
        return output_file_path

    except subprocess.CalledProcessError as e:
        print("비디오 추출 중 오류 발생:")
        # print(result.stdout.decode())  # 표준 출력 메세지 출력
        print(e.stderr.decode())  # 에러 메세지 출력
        return output_file_path

# 프레임에서 객체 추출
def crop_frame(p_boxes, input_path, output_path):
    # output_path 설정 및 디렉토리 생성
    output_path = os.path.join(output_path, "frames")
    frame_file_path = os.path.join(output_path, "frame")
    os.makedirs(output_path, exist_ok=True)

    width = []
    height = []

    # 각 bounding box의 너비와 높이를 계산
    for p_box in p_boxes:
        width.append(round(int(p_box[3] - p_box[1])))
        height.append(round(int(p_box[4] - p_box[2])))

    # 가장 큰 너비와 높이를 crop 크기로 설정
    w = max(width)
    h = max(height)

    # 각 프레임을 crop하여 저장
    for i in range(len(p_boxes)):
        # x = ((p_boxes[i][3] - p_boxes[i][1]) / 2) + p_boxes[i][1]
        # y = ((p_boxes[i][4] - p_boxes[i][2]) / 2) + p_boxes[i][2]
        x = p_boxes[i][1]
        y = p_boxes[i][2]
        # command = f'ffmpeg -i "{input_path}" -vf "crop={w}:{h}:{int(x - (w / 2))}:{int(y - (h / 2))}, select=\'eq(n\\,{i+1})\'" -frames:v 1 "{frame_file_path}_{i+1:04d}.png"'
        command = f'ffmpeg -i "{input_path}" -vf "crop={w}:{h}:{int(x)}:{int(y)}, select=\'eq(n\\,{i + 1})\'" -frames:v 1 "{frame_file_path}_{i + 1:04d}.png"'
        subprocess.run(command, shell=True)

    print("프레임 추출 완료")
    return frame_file_path

# 프레임 병합
def frames_to_video(fps, frame_file_path, file_name, output_path):
    output_file_path = os.path.join(output_path, f"crop_{file_name}.mp4")

    command = f'ffmpeg -framerate {fps} -i "{frame_file_path}_%04d.png" -c:v libx264 -pix_fmt yuv420p "{output_file_path}"'

    try:
        subprocess.run(command, shell=True, capture_output=True)  # ffmpeg 명령어 실행
        print("프레임 병합 성공 : %s" % output_file_path)
        return output_file_path


    except subprocess.CalledProcessError as e:
        print("프레임 병합 중 오류 발생:")
        print(e.stderr.decode())  # 에러 메세지 출력

# 최종 결과물 : 비디오 + 오디오 병합
def create_final_video(file_name, video_path, audio_path, output_path):
    output_file_path = os.path.join(output_path, f"{file_name}.mp4")

    command = f'ffmpeg -i "{video_path}" -i "{audio_path}" -c:v copy -c:a aac -strict experimental "{output_file_path}"'

    try:
        subprocess.run(command, shell=True, capture_output=True)  # ffmpeg 명령어 실행
        print("오디오 병합 성공 : %s" % file_name)

    except subprocess.CalledProcessError as e:
        print("오디오 병합 중 오류 발생:")
        print(e.stderr.decode())  # 에러 메세지 출력
