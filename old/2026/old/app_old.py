import cv2
from hard_control.hard_camera import HardCamera
from flask import Flask, Response, render_template_string, request
import threading, time

app = Flask(__name__)

# Общие данные
raw = None      # исходный (перевёрнутый) кадр
masked = None   # кадр с маской
frame = None
lock = threading.Lock()

# Параметры маски (HSV)
hsv_min = [0, 0, 0]
hsv_max = [180, 255, 255]
obrez = 0
cap = HardCamera()
# Функция захвата и обработки
def capture_and_process():
    global raw, masked, cap
    while True:
        raw = cap.get_frame()
        if raw is None:
            continue

        # 1. Исходный кадр (переворот, как у вас)
        # raw = cv2.flip(cv2.flip(img, 1), 0)

        # 2. Обработка для маски
        if masked is None or __name__ == '__main__':
            hsv = cv2.cvtColor(raw, cv2.COLOR_BGR2HSV)
            lower = tuple(hsv_min)
            upper = tuple(hsv_max)
            masked = cv2.inRange(hsv, lower, upper)
            masked[:obrez, :] = 0

    cap.release()

# Генераторы потоков
def generate_raw():
    while True:
        with lock:
            ret_raw, jpeg_raw = cv2.imencode('.jpg', cv2.cvtColor(raw, cv2.COLOR_BGR2RGB))
            if ret_raw:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg_raw.tobytes() + b'\r\n')
        time.sleep(0.2)

def generate_masked():
    while True:
        with lock:
            ret_masked, jpeg_masked = cv2.imencode('.jpg', masked)
            if ret_masked:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg_masked.tobytes() + b'\r\n')
        time.sleep(0.2)

@app.route('/')
def index():
    # HTML с двумя изображениями
    html = '''
    <!DOCTYPE html>
    <html>
    <head><title>Multi Video Stream</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        .streams { display: flex; gap: 20px; flex-wrap: wrap; }
        .stream { text-align: center; }
        .slider-container { margin: 5px 0; }
    </style>
    </head>
    <body>
        <h1>Raspberry Pi Camera - Two Streams</h1>
        <div class="streams">
            <div class="stream">
                <h2>Raw (flipped)</h2>
                <img style="border: solid 5px black;" src="/video_feed/raw" width="640" height="480">
            </div>
            <div class="stream">
                <h2>Masked</h2>
                <img style="border: solid 5px black;" src="/video_feed/masked" width="640" height="480">
            </div>
        </div>

        <h2>HSV Range Mask<br><h6 style="margin: 0;" id="json"><span>{"h_min":"0","obrez":"68"}</span><br><input type="text" id="input_json" placeholder="{}" onchange="input_json(this.value);this.value='';"></h6></h2>
        <div class="slider-container">
            <label>H Min:</label>
            <input type="range" id="h_min" min="0" max="180" value="0" oninput="updateParam('h_min', this.value)">
            <span id="h_min_val" class="value">0</span>
        </div>
        <div class="slider-container">
            <label>H Max:</label>
            <input type="range" id="h_max" min="0" max="180" value="180" oninput="updateParam('h_max', this.value)">
            <span id="h_max_val" class="value">180</span>
        </div>
        <div class="slider-container">
            <label>S Min:</label>
            <input type="range" id="s_min" min="0" max="255" value="0" oninput="updateParam('s_min', this.value)">
            <span id="s_min_val" class="value">0</span>
        </div>
        <div class="slider-container">
            <label>S Max:</label>
            <input type="range" id="s_max" min="0" max="255" value="255" oninput="updateParam('s_max', this.value)">
            <span id="s_max_val" class="value">255</span>
        </div>
        <div class="slider-container">
            <label>V Min:</label>
            <input type="range" id="v_min" min="0" max="255" value="0" oninput="updateParam('v_min', this.value)">
            <span id="v_min_val" class="value">0</span>
        </div>
        <div class="slider-container">
            <label>V Max:</label>
            <input type="range" id="v_max" min="0" max="255" value="255" oninput="updateParam('v_max', this.value)">
            <span id="v_max_val" class="value">255</span>
        </div>
        <div class="slider-container">
            <label>obrez</label>
            <input type="range" id="obrez" min="0" max="480" value="0" oninput="updateParam('obrez', this.value)">
            <span id="obrez_val" class="value">255</span>
        </div>

        <script>
            let json_mask = {};
            function updateParam(name, value) {
                // Обновляем отображение значения
                document.getElementById(name + '_val').innerText = value;
                json_mask[name] = value;
                document.getElementById('json').innerText = JSON.stringify(json_mask);
                // Отправляем новое значение на сервер
                fetch('/set_params', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, value: parseInt(value) })
                });
            }
            function input_json(value) {
                let v = JSON.parse(value)
                for (i in v) {
                    document.getElementById(i).value = Number(v[i]);
                    updateParam(i, v[i]);
                }
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/video_feed/<stream>')
def video_feed(stream):
    if stream == 'raw':
        return Response(generate_raw(), mimetype='multipart/x-mixed-replace; boundary=frame')
    elif stream == 'masked':
        return Response(generate_masked(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Not found", 404

@app.route('/set_params', methods=['POST'])
def set_params():
    global hsv_min, hsv_max, obrez
    data = request.get_json()
    name = data.get('name')
    value = data.get('value')

    if name == 'h_min':
        hsv_min[0] = value
    elif name == 'h_max':
        hsv_max[0] = value
    elif name == 's_min':
        hsv_min[1] = value
    elif name == 's_max':
        hsv_max[1] = value
    elif name == 'v_min':
        hsv_min[2] = value
    elif name == 'v_max':
        hsv_max[2] = value
    elif name == 'obrez':
        obrez = value

    return ('', 204)  # No content
print(__name__)
if __name__ == '__main__':
    threading.Thread(target=capture_and_process, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
else:
    threading.Thread(target=capture_and_process, daemon=True).start()

    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, threaded=True), daemon=True).start()
    print(111)
