import os
import pwd

print("USER:", os.environ.get('USER'))
print("UID:", os.getuid())
print("GID:", os.getgid())
print("Groups (numeric):", os.getgroups())
# Преобразуем числовые ID групп в имена (для наглядности)
import grp
group_names = [grp.getgrgid(g).gr_name for g in os.getgroups()]
print("Groups (names):", group_names)

# Проверим доступ к файлам камеры
video_devices = [f for f in os.listdir('/dev') if f.startswith('video')]
media_devices = [f for f in os.listdir('/dev') if f.startswith('media')]
print("Video devices found:", video_devices)
for dev in video_devices:
    path = f'/dev/{dev}'
    try:
        with open(path, 'rb'):
            print(f"  {path}: accessible")
    except Exception as e:
        print(f"  {path}: {e}")

# Проверим picamera2
try:
    from picamera2 import Picamera2
    info = Picamera2.global_camera_info()
    print("Picamera2 cameras:", info)
except Exception as e:
    print("Picamera2 error:", e)