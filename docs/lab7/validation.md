# Kiểm chứng và quay demo Bài 7

Phiên triển khai: 10/11/2026, Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic.
Hướng dẫn chạy đầy đủ ở [README package](../../src/tb4_voice_navigation/README.md).

## Minh chứng lưu tại workspace

- `src/tb4_voice_navigation/maps/map.yaml` + `map.pgm`: bản đồ Depot gốc được sao chép.
- `segmented_map.png`: ảnh ba vùng chức năng, `labels.png`: nhãn từng pixel uint16.
- `regions.yaml`: tên, bí danh, điểm hạt giống, đích hợp lệ, clearance và fingerprint.
- `ros_integration.json`: kết quả 11 tình huống action với **server giả**, không phải robot.
- `simulation.json` (nếu chạy kiểm tra Gazebo): vị trí theo thời gian, kết quả Nav2,
  trạng thái lệnh và thông điệp hazard. Đầu vào kiểm tra này là **văn bản**, không phải micro.
- `report.pdf`: báo cáo hai trang, tạo lại bằng `python3 docs/lab7/create_report.py`.
- `trajectory.png`: quỹ đạo đo bằng ground truth Gazebo trong phiên lệnh văn bản;
  tạo lại bằng `python3 docs/lab7/plot_simulation.py`.
- `gazebo.png`, `rviz.png`: ảnh riêng các cửa sổ mô phỏng sau khi robot tới C.
- `synthetic_speech_base.json`, `synthetic_speech_small.json` và `synthetic_audio/`:
  phép thử nhận dạng **âm thanh tạo bằng eSpeak**, không phải ghi âm giọng người.
- `synthetic_speech_gtts_base.json`, `synthetic_speech_gtts_small.json`, `gtts_audio/`:
  phép thử bằng âm thanh tổng hợp Google Translate TTS, tạo bằng gTTS 2.5.4.

39 unit tests đã đạt. Build package và kiểm thử colcon thực hiện trên Jazzy.
757 ô trống thuộc các đảo không nối đến hạt giống giữ nhãn 0; chúng không được dùng
làm đích. Ba vùng đều có đích thuộc cùng thành phần liên thông với clearance ≥0,4 m.

Trong Gazebo, cả ba ca lệnh văn bản đạt: A (66,16 s; sai số 0,113 m), A→B
(110,11 s; sai số cuối 0,252 m), C (117,56 s; sai số 0,201 m). Lệnh Z bị từ chối.
Sai số AMCL ban đầu so với ground truth là 0,031 m. Nhận 4303 thông điệp hazard,
không ghi nhận BUMP trong luồng này. Các tiến trình mô phỏng/Nav2 do phiên kiểm tra
khởi chạy được dừng sau khi thu minh chứng.

## Giới hạn kiểm chứng hiện tại

Cài đặt `faster-whisper` ban đầu thất bại do `No space left on device`; lần cài lại
đã thành công khi có thêm dung lượng. Môi trường `.venv-voice` dùng Python cùng
phiên bản với ROS, truy cập được rclpy, OpenCV và các thiết bị âm thanh. PyAV được
ghim phiên bản trong requirements để tương thích API đọc tệp của faster-whisper.
Đã thử micro trực tiếp: terminal nhận các câu “Đi đến vùng b”, “Đi đến vùng C” và
“Đi đến vùng A”. Log Nav2 xác nhận B và C hoàn tất; B được gọi khi robot đã đứng
ở B, còn A đã nhận đích tại thời điểm chốt minh chứng. Hai câu A/B ban đầu bị từ
chối do thiếu bí danh “vùng”; đã bổ sung bí danh và 7 trường hợp kiểm thử.
Xem `live_microphone.json` để phân biệt lần phát lại bằng văn bản với lệnh micro.
Chưa có bộ đo accuracy, WER hay độ trễ nhận dạng của giọng người. Không coi unit
test/parser hoặc Gazebo với lệnh văn bản là phép đo chất lượng nhận dạng micro.

Kết quả phụ thuộc đáng kể vào chất lượng âm thanh tổng hợp:

| Nguồn tổng hợp | Whisper base | Whisper small |
|---|---:|---:|
| eSpeak | 0/3 | 0/3 |
| Google Translate TTS | 2/3 | 3/3 |

Small nhận đúng ba câu Google TTS và trích xuất đúng tuyến A, A→B, B. Base đọc
sai “phòng thí nghiệm” nên bộ phân tích từ chối. Phiên âm eSpeak rỗng hoặc sai
cũng bị từ chối. Bộ âm thanh tổng hợp không đại diện cho giọng người dùng thực tế;
cần đánh giá micro, tiếng ồn và giọng vùng miền trước khi công bố hệ thống hoàn tất.
Không dùng các WAV/MP3 tổng hợp này làm minh chứng giọng nói thật.

Tái hiện phép thử ASR tổng hợp (không gửi lệnh di chuyển):

```bash
source /opt/ros/jazzy/setup.bash
.venv-voice/bin/python docs/lab7/check_synthetic_speech.py --model base
.venv-voice/bin/python docs/lab7/check_synthetic_speech.py --model small
.venv-voice/bin/python docs/lab7/check_synthetic_speech.py --model small --source gtts
```

Script dùng `libespeak-ng.so.1`. `requirements-voice.txt` ghim PyAV 16.0.1 vì
PyAV 19.0.2 không nhận tham số `metadata_errors` của faster-whisper 1.2.1.
`--source gtts` đọc các MP3 đã lưu nên không cần gTTS hoặc kết nối tới Google
khi kiểm tra lại. Google TTS chỉ dùng tạo đầu vào kiểm thử; nhận dạng vẫn chạy
cục bộ bằng Whisper. Nguồn công cụ tạo âm thanh: [gTTS](https://gtts.readthedocs.io/en/latest/module.html).

Humble/Ubuntu 22.04 chưa được kiểm thử; không dùng launch Jazzy để tuyên bố tương
thích simulator Humble. Repo riêng: [turtlebot4-voice-navigation-lab7](https://github.com/ngaingu-05/turtlebot4-voice-navigation-lab7).
Link Drive trong `submission.json` giữ nguyên thư mục các tuần trước. URL video
Bài 7 vẫn để `null` vì chưa xác nhận video cụ thể trong Drive.

## Tái hiện kiểm tra ROS bằng action giả

```bash
cd ~/turtlebot4-voice-navigation-lab7
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ROS_DOMAIN_ID=73 python3 src/tb4_voice_navigation/test/check_ros_integration.py
```

Các trường hợp: ba mẫu lệnh cơ bản, tuyến A→C→B, vùng lạ ở giữa tuyến, phủ định,
server từ chối, action thất bại, bận + dừng, timeout, dừng trước khi server chấp nhận.

## Tái hiện kiểm tra Nav2 thật trong Gazebo

Chạy các terminal mô phỏng, localization/Nav2 và node voice theo README, cùng
`ROS_DOMAIN_ID`. Undock thành công trước. Script sau **chỉ dùng mô phỏng**: nó đặt
initial pose AMCL bằng ground truth Gazebo, sau đó điều hướng bằng AMCL/Nav2 bình thường.
Không chạy script trên robot thật hoặc bản đồ không khớp world Depot.

```bash
python3 src/tb4_voice_navigation/test/check_simulation.py
```

Script thử A, A→B, C và vùng Z; lưu kết quả thực tế kể cả khi có bước thất bại.
`simulation_startup_rejection.json` lưu lần thử trước khi lifecycle Nav2 active:
goal bị từ chối; script đã bổ sung bước chờ active trước khi chạy lại.
Theo dõi `hazard_detection` chỉ phản ánh tín hiệu đã nhận, không tự chứng minh mọi
va chạm vật lý đều được đo. Dùng LiDAR/costmap và quan sát Gazebo để đánh giá thêm.

## Kịch bản video cần nộp

1. Hiển thị bản đồ A/B/C, micro, terminal transcript/status và Gazebo/RViz trong
   cùng video hoặc bố cục nhiều cửa sổ; không để dữ liệu riêng tư xuất hiện.
2. Nhấn Enter, nói “Đi đến khu vực A”; chờ nhận dạng, đích A và robot hoàn thành.
3. Nói “Di chuyển từ khu vực A đến khu vực B”; cho thấy A hoàn thành rồi mới gửi B.
   Để kiểm tra trường hợp xuất phát khác A, đưa robot đến C trước khi nói câu này.
4. Nói “Đi đến phòng thí nghiệm”; cho thấy tên có nghĩa được đối chiếu đúng B.
5. Nói “Đi đến khu vực Z”; cho thấy trạng thái `invalid_command` và không có goal mới.
6. Thử tuyến A→C→B, quan sát `/plan` và vật cản trong world. Thử “Dừng lại” khi đang chạy.
7. Giữ WAV bằng `--save-dir docs/lab7/audio` và ghi lại câu nói/phiên âm/kết quả
   cho ít nhất 3 mẫu câu, mỗi mẫu vài lần. Báo cáo tỷ lệ đúng theo số lần đã đo.
8. Upload video, mở quyền xem theo yêu cầu môn học, điền URL source public và video
   trong `submission.json`, rồi tạo lại PDF. Kiểm tra URL từ trình duyệt chưa đăng nhập.

Phiếu ghi kết quả thực nghiệm giọng nói (chưa điền):

| Câu nói | Số lần thử | Phiên âm đúng | Tuyến đúng | Hoàn tất Nav2 | Độ trễ |
|---|---:|---:|---:|---:|---|
| Đi đến khu vực A | — | — | — | — | — |
| Di chuyển từ khu vực A đến khu vực B | — | — | — | — | — |
| Đi đến phòng thí nghiệm | — | — | — | — | — |
