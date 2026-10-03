import cv2
import threading
import time
from flask import Flask, Response, render_template_string, request


HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mask Editor</title>
<style>
:root{
  --bg:#0f1115; --panel:#181b22; --panel-2:#21252e;
  --border:#2a2f3a; --text:#e6e9ef; --muted:#8b94a7;
  --accent:#4f8cff; --accent-2:#00d4aa;
}
*{box-sizing:border-box}
body{
  margin:0; min-height:100vh; color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:radial-gradient(1200px 600px at 80% -10%,#1a2130 0%,var(--bg) 60%);
}
header{
  padding:18px 28px; display:flex; align-items:center; justify-content:space-between;
  border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,#151922cc,#0f111500);
  backdrop-filter:blur(6px);
}
header h1{margin:0; font-size:20px; font-weight:600; letter-spacing:.3px}
header h1 span{color:var(--accent)}
.preset-bar{display:flex; gap:10px; align-items:center}
select,button{
  font-family:inherit; font-size:14px; padding:8px 14px; border-radius:8px;
  border:1px solid var(--border); background:var(--panel-2); color:var(--text);
  cursor:pointer; transition:.15s ease; outline:none;
}
select:hover,button:hover{border-color:var(--accent)}
button.primary{background:var(--accent); border-color:var(--accent); color:#fff; font-weight:600}
button.primary:hover{background:#6ba0ff}
button.success{background:var(--accent-2); border-color:var(--accent-2); color:#062620; font-weight:600}
button.success:hover{background:#2ee0bb}
main{
  display:grid; grid-template-columns:1fr 340px; gap:20px; padding:20px 28px;
}
@media (max-width:1000px){ main{grid-template-columns:1fr} }

.video-grid{display:grid; grid-template-columns:1fr 1fr; gap:16px}
@media (max-width:700px){ .video-grid{grid-template-columns:1fr} }

.window{
  background:var(--panel); border:1px solid var(--border); border-radius:14px;
  overflow:hidden; box-shadow:0 6px 24px rgba(0,0,0,.35);
}
.window h3{
  margin:0; padding:10px 16px; font-size:12px; font-weight:600;
  text-transform:uppercase; letter-spacing:1.2px; color:var(--muted);
  border-bottom:1px solid var(--border); background:var(--panel-2);
}
.window img{display:block; width:100%; height:auto; background:#000}

.controls{
  background:var(--panel); border:1px solid var(--border); border-radius:14px;
  padding:20px; height:fit-content; box-shadow:0 6px 24px rgba(0,0,0,.35);
}
.controls h2{
  margin:0 0 16px; font-size:12px; text-transform:uppercase;
  letter-spacing:1.2px; color:var(--muted); font-weight:600;
}
.slider{margin-bottom:14px}
.slider-header{display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px}
.slider-header label{color:var(--muted)}
.slider-header .value{
  color:var(--accent); font-family:ui-monospace,'SF Mono',Menlo,monospace;
  font-weight:600; min-width:36px; text-align:right;
}
input[type=range]{
  -webkit-appearance:none; appearance:none; width:100%; height:6px;
  border-radius:3px; background:var(--panel-2); outline:none; cursor:pointer;
}
input[type=range]::-webkit-slider-thumb{
  -webkit-appearance:none; width:16px; height:16px; border-radius:50%;
  background:var(--accent); border:2px solid var(--bg); cursor:pointer;
  transition:transform .12s ease, box-shadow .12s ease;
}
input[type=range]::-webkit-slider-thumb:hover{
  transform:scale(1.15); box-shadow:0 0 0 5px rgba(79,140,255,.18);
}
input[type=range]::-moz-range-thumb{
  width:16px; height:16px; border-radius:50%;
  background:var(--accent); border:2px solid var(--bg); cursor:pointer;
}
</style>
</head>
<body>
<header>
  <h1><span>Mask</span> Editor</h1>
  <div class="preset-bar">
    <label style="color:var(--muted);font-size:13px">Preset:</label>
    <select id="preset-select"></select>
    <button class="success" id="save-btn">💾 Save</button>
  </div>
</header>
<main>
  <div class="video-grid" id="windows"></div>
  <div class="controls">
    <h2>Parameters</h2>
    <div id="trackbars-list"></div>
  </div>
</main>
<script>
let dragging = null;
document.addEventListener('mousedown', e => { if (e.target.type === 'range') dragging = e.target; });
document.addEventListener('mouseup', () => { dragging = null; });

function fetchWindows(){
  fetch('/windows').then(r=>r.json()).then(data=>{
    const c = document.getElementById('windows');
    const cur = new Set(data);
    for (const w of data){
      if (!document.getElementById('win_'+w)){
        const d = document.createElement('div');
        d.className = 'window'; d.id = 'win_'+w;
        d.innerHTML = `<h3>${w}</h3><img src="/video_feed/${w}">`;
        c.appendChild(d);
      }
    }
    [...c.children].forEach(el=>{
      const n = el.id.replace('win_','');
      if (!cur.has(n)) c.removeChild(el);
    });
  });
}

function fetchTrackbars(){
  fetch('/trackbars').then(r=>r.json()).then(data=>{
    const c = document.getElementById('trackbars-list');
    const cur = new Set(Object.keys(data));
    for (const name in data){
      const tb = data[name];
      if (!document.getElementById('tb_'+name)){
        const d = document.createElement('div');
        d.className = 'slider'; d.id = 'tb_'+name;
        d.innerHTML = `
          <div class="slider-header">
            <label>${tb.label}</label>
            <span class="value" id="${name}_val">${tb.value}</span>
          </div>
          <input type="range" min="${tb.min}" max="${tb.max}" value="${tb.value}"
                 oninput="updateTB('${name}', this.value)">
        `;
        c.appendChild(d);
      } else {
        const inp = document.querySelector(`#tb_${name} input`);
        const sp  = document.getElementById(`${name}_val`);
        if (inp && dragging !== inp && tb.value !== parseInt(inp.value)){
          inp.value = tb.value;
          sp.innerText = tb.value;
        }
      }
    }
    [...c.children].forEach(el=>{
      const n = el.id.replace('tb_','');
      if (!cur.has(n)) c.removeChild(el);
    });
  });
}

function fetchPresets(){
  fetch('/presets').then(r=>r.json()).then(data=>{
    const s = document.getElementById('preset-select');
    const opts = Object.keys(data.options);
    if (s.dataset.opts !== opts.join(',')){
      s.innerHTML = '';
      for (const k of opts){
        const o = document.createElement('option');
        o.value = k; o.textContent = data.options[k];
        s.appendChild(o);
      }
      s.dataset.opts = opts.join(',');
    }
    if (data.value !== null && s.value !== String(data.value) && document.activeElement !== s){
      s.value = String(data.value);
    }
  });
}

function updateTB(name, value){
  document.getElementById(`${name}_val`).innerText = value;
  fetch('/trackbar', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name, value: parseInt(value)})
  });
}

function savePreset(){
  const b = document.getElementById('save-btn');
  fetch('/save', {method:'POST'}).then(()=>{
    b.innerText = '✓ Saved';
    setTimeout(()=>{ b.innerText = '💾 Save'; }, 800);
  });
}

document.getElementById('save-btn').addEventListener('click', savePreset);
document.getElementById('preset-select').addEventListener('change', e=>{
  fetch('/preset', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({value: e.target.value})
  });
});

setInterval(fetchWindows, 200);
setInterval(fetchTrackbars, 200);
setInterval(fetchPresets, 300);
fetchWindows(); fetchTrackbars(); fetchPresets();
</script>
</body>
</html>
'''


class WebGUI:
    """Веб-интерфейс: несколько видеопотоков, слайдеры и пресеты (маски)."""

    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self._images = {}              # имя окна -> numpy BGR
        self._trackbars = {}           # name -> (min, max, label, callback)
        self._trackbar_values = {}     # name -> текущее значение
        self._presets_options = {}     # key -> label
        self._presets_value = None
        self._presets_callback = None
        self._save_callback = None
        self._lock = threading.Lock()
        self._running = True
        self._setup_routes()

    # ---------- запуск сервера ----------
    def start(self):
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        time.sleep(0.5)
        try:
            import netifaces
            def get_ip(ifname):
                try:
                    return netifaces.ifaddresses(ifname)[netifaces.AF_INET][0]['addr']
                except (KeyError, ValueError):
                    return '127.0.0.1'
            print('http://' + get_ip('eth0')  + ':' + str(self.port))
            print('http://' + get_ip('wlan0') + ':' + str(self.port))
        except Exception:
            print(f'http://localhost:{self.port}')

    def _run_server(self):
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

    # ---------- маршруты ----------
    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template_string(HTML_TEMPLATE)

        @self.app.route('/windows')
        def list_windows():
            with self._lock:
                return list(self._images.keys())

        @self.app.route('/video_feed/<winname>')
        def video_feed(winname):
            def generate():
                while self._running:
                    with self._lock:
                        img = self._images.get(winname)
                    if img is not None:
                        ok, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        if ok:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n'
                                   + jpeg.tobytes() + b'\r\n')
                    time.sleep(0.05)
            return Response(generate(),
                            mimetype='multipart/x-mixed-replace; boundary=frame')

        @self.app.route('/trackbars')
        def get_trackbars():
            with self._lock:
                data = {}
                for name, (minv, maxv, label, _) in self._trackbars.items():
                    data[name] = {
                        'min': minv, 'max': maxv,
                        'label': label or name,
                        'value': self._trackbar_values.get(name, minv),
                    }
                return data

        @self.app.route('/trackbar', methods=['POST'])
        def trackbar_update():
            data = request.get_json()
            name = data['name']
            value = data['value']
            with self._lock:
                self._trackbar_values[name] = value
                cb = self._trackbars.get(name, (None, None, None, None))[3]
            if cb:
                cb(value)
            return ('', 204)

        @self.app.route('/presets')
        def get_presets():
            with self._lock:
                return {'options': dict(self._presets_options),
                        'value': self._presets_value}

        @self.app.route('/preset', methods=['POST'])
        def set_preset():
            data = request.get_json()
            value = data['value']
            with self._lock:
                self._presets_value = value
                cb = self._presets_callback
            if cb:
                cb(value)
            return ('', 204)

        @self.app.route('/save', methods=['POST'])
        def save():
            with self._lock:
                cb = self._save_callback
            if cb:
                cb()
            return {'status': 'ok'}

    # ---------- OpenCV-совместимый API ----------
    def imshow(self, winname, img):
        with self._lock:
            self._images[winname] = img.copy()

    def createTrackbar(self, trackbarname, winname, value, count, callback=None, label=None):
        with self._lock:
            self._trackbars[trackbarname] = (0, count, label, callback)
            self._trackbar_values[trackbarname] = value

    def setTrackbarPos(self, trackbarname, value):
        with self._lock:
            self._trackbar_values[trackbarname] = value

    def getTrackbarPos(self, trackbarname):
        with self._lock:
            return self._trackbar_values.get(trackbarname, 0)

    def setPresets(self, options, value, callback):
        """options: {key: label}, value: текущий ключ, callback(key) — переключение."""
        with self._lock:
            self._presets_options = dict(options)
            self._presets_value = value
            self._presets_callback = callback

    def setPresetValue(self, value):
        with self._lock:
            self._presets_value = value

    def onSave(self, callback):
        """Callback для кнопки Save (сохраняет текущий col в активный пресет)."""
        with self._lock:
            self._save_callback = callback

    def waitKey(self, delay=1):
        time.sleep(delay / 1000.0)
        return -1

    def destroyAllWindows(self):
        self._running = False