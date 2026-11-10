"""Build a two-page Lab 7 report using the previous weeks' cover and typography."""
import json
from pathlib import Path
import shutil
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAPS = ROOT / 'src/tb4_voice_navigation/maps'
SUB = json.loads((HERE / 'submission.json').read_text())
SIM = json.loads((HERE / 'simulation.json').read_text())
ROS = json.loads((HERE / 'ros_integration.json').read_text())
LIVE = json.loads((HERE / 'live_microphone.json').read_text())
SPEECH = json.loads((HERE / 'synthetic_speech_gtts_small.json').read_text())
for name, filename in [('DV', 'DejaVuSans.ttf'), ('DV-Bold', 'DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name, '/usr/share/fonts/truetype/dejavu/' + filename))
pdfmetrics.registerFontFamily('DV', normal='DV', bold='DV-Bold', italic='DV', boldItalic='DV-Bold')
BLUE = colors.HexColor('#12374b')
TEAL = colors.HexColor('#006d77')
GRAY = colors.HexColor('#52616b')
PALE = colors.HexColor('#e5f1f3')
WIDTH = A4[0] - 84
body = ParagraphStyle('BodyVN', fontName='DV', fontSize=9.1, leading=13.2, spaceAfter=7)
title = ParagraphStyle('TitleVN', parent=body, fontName='DV-Bold', fontSize=22, leading=29, textColor=BLUE, spaceAfter=10)
heading = ParagraphStyle('HeadingVN', parent=body, fontName='DV-Bold', fontSize=11.5, leading=16, textColor=TEAL, spaceBefore=6, spaceAfter=6)
caption = ParagraphStyle('CaptionVN', parent=body, fontSize=7.7, leading=10.7, textColor=GRAY, spaceAfter=6)
cell = ParagraphStyle('CellVN', parent=body, fontSize=8, leading=11, spaceAfter=0)
story = []


def p(text, style=body):
    story.append(Paragraph(text, style))


def link(url, label):
    return f'<link href="{escape(url, {chr(34): "&quot;"})}" color="#0077b6"><u>{escape(label)}</u></link>'


def table(rows, widths):
    item = Table([[Paragraph(escape(str(value)), cell) for value in row] for row in rows], colWidths=widths, hAlign='LEFT')
    item.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PALE), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), .7, TEAL),
        ('LINEBELOW', (0, 1), (-1, -1), .3, colors.HexColor('#dddddd')),
        ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([item, Spacer(1, 6)])


def architecture():
    drawing = Drawing(WIDTH, 70)
    labels = [['Micro / audio', 'Tiếng Việt'], ['Whisper small', 'CPU int8'],
              ['Tên vùng', 'regions.yaml'], ['Nav2', 'NavigateToPose'], ['TurtleBot 4', 'Gazebo']]
    box_width, gap = 89, (WIDTH - 5 * 89) / 4
    for i, lines in enumerate(labels):
        x = i * (box_width + gap)
        drawing.add(Rect(x, 14, box_width, 42, rx=4, ry=4, fillColor=PALE, strokeColor=TEAL, strokeWidth=.8))
        for j, label in enumerate(lines):
            drawing.add(String(x + box_width / 2, 41 - j * 13, label, textAnchor='middle', fontName='DV', fontSize=8, fillColor=BLUE))
        if i < 4:
            end = x + box_width + gap
            drawing.add(Line(x + box_width, 35, end, 35, strokeColor=TEAL))
            drawing.add(Polygon([end, 35, end - 4, 38, end - 4, 32], fillColor=TEAL, strokeColor=TEAL))
    return drawing


# Same cover identity, link block and colour palette as the Lab 6 report.
p('BÁO CÁO THỰC HÀNH<br/>TURTLEBOT 4', title)
p('<b>Bài tập 7 — Phân vùng bản đồ và điều hướng robot bằng giọng nói</b>')
p('Ngày thực nghiệm: <b>10/11/2026</b> · Múi giờ Việt Nam (UTC+7).<br/>'
  'Môi trường: Ubuntu 24.04 LTS, ROS 2 Jazzy, Gazebo Harmonic, TurtleBot 4 Standard.')
p(f'Họ và tên: <b>{escape(SUB["student"])}</b><br/>'
  f'Mã sinh viên: <b>{escape(SUB["student_id"])}</b><br/>'
  f'Lớp / Nhóm: <b>{escape(SUB["class_group"])}</b>')
p('GitHub: ' + link(SUB['public_source_url'], SUB['public_source_url']) + '<br/>'
  'Google Drive: ' + link(SUB['previous_assignment_drive_folder_url'], 'Thư mục nộp bài và tài liệu — dùng chung các tuần'))
p('Kết quả thực nghiệm', heading)
p('<b>39/39 kiểm thử logic</b>, <b>11/11 tình huống ROS action giả</b> và '
  '<b>3/3 ca điều hướng Nav2 thật trong Gazebo</b> đạt. Whisper small nhận đúng '
  '<b>3/3 câu tổng hợp Google TTS</b>. Đã thử micro trực tiếp: các lệnh đến B và C '
  'hoàn tất trong log sau khi bổ sung bí danh “vùng A/B/C”.')
story.append(Image(str(MAPS / 'segmented_map.png'), width=460, height=460 * 304 / 604))
p('Hình 1. Bản đồ Depot phân vùng A/B/C; vòng tròn là đích điều hướng hợp lệ. '
  'Màu vùng được sinh từ xử lý bản đồ, không phải ảnh chụp robot đang di chuyển.', caption)
table([['Vùng', 'Tên chức năng', 'Đích (x; y), m', 'Khoảng hở, m'],
       ['A', 'Phòng học', '−2,468; 0,503', '2,87'],
       ['B', 'Phòng thí nghiệm', '1,982; −2,997', '0,51'],
       ['C', 'Hành lang', '1,982; 3,003', '0,57']], [45, 167, 177, WIDTH - 389])
p('Phạm vi minh chứng: bản đồ, quỹ đạo, ảnh mô phỏng và log đã lưu trong repo. '
  'Link Drive giữ nguyên từ báo cáo tuần trước; chưa xác nhận video Bài 7 trong thư mục này. '
  'Đề dùng Ubuntu 22.04 / Humble; phiên thực hiện dùng Jazzy và chưa kiểm thử trên Humble.', caption)

story.append(PageBreak())
p('1. Phương pháp phân vùng và gắn nhãn', heading)
p('Đọc map.yaml và map.pgm; chỉ ô có occupancy &lt; free_thresh được xem là trống. '
  'Lan truyền đồng thời từ ba hạt giống theo lưới 4 lân cận, gán mỗi ô cho hạt giống '
  'có khoảng cách đường đi ngắn nhất (geodesic Voronoi), không xuyên vật cản hay ô chưa biết. '
  'Tên A/B/C là nhãn chức năng gán thủ công cho kho mở, không phải nhận dạng phòng tự động.')
p('Distance transform chọn đích gần hạt giống có khoảng hở ≥0,4 m, bù nửa đường chéo ô; '
  'các đích phải cùng thành phần liên thông của lưới đủ khoảng hở. 757 ô trống thuộc đảo '
  'không nối đến hạt giống giữ nhãn 0. Xuất labels.png, ảnh màu và regions.yaml chứa '
  'ID, tên, bí danh, điểm đích và fingerprint để phát hiện bản đồ thay đổi.')
p('Tâm pixel: qx=(u+0,5)r, qy=(H−v−0,5)r; tọa độ ROS nhận được bằng xoay '
  '(qx,qy) theo yaw rồi cộng origin trong map.yaml.', caption)
p('2. Nhận dạng tiếng nói và điều hướng', heading)
story.append(architecture())
p('Micro thu từng câu sau khi nhấn Enter (6 giây), hoặc đọc tệp audio. faster-whisper '
  'small chạy cục bộ trên CPU int8 với language=vi, VAD và lọc đoạn có độ tin cậy thấp. '
  'Văn bản lên /voice_nav/text được bỏ dấu, chuẩn hóa hoa/thường và đối chiếu toàn bộ '
  'bí danh, gồm “vùng A”, “khu vực A”, “phòng A” và tên chức năng.')
p('“Đi đến khu vực A” → A; “Di chuyển từ khu vực A đến khu vực B” → A rồi B; '
  '“Đi đến phòng thí nghiệm” → B. Mở rộng A→C→B được hỗ trợ. Kiểm tra toàn bộ tuyến '
  'trước khi gửi NavigateToPose; chỉ gửi chặng tiếp sau STATUS_SUCCEEDED. Vùng lạ, '
  'câu phủ định/mơ hồ bị từ chối; lệnh mới khi đang bận không ghi đè tuyến. “Dừng lại” '
  'hủy action; lỗi/từ chối/timeout dừng toàn bộ tuyến. Nav2 dùng LiDAR/costmap để lập '
  'đường và tránh vật cản. Nhãn và thứ tự đích hiển thị trên RViz; /plan là đường thực.')
p('3. Kết quả kiểm thử và giới hạn', heading)
ros_pass = sum(t['passed'] for t in ROS['tests'])
sim_pass = sum(t['passed'] for t in SIM['results'])
speech_pass = sum(t['passed'] for t in SPEECH['results'])
completed_live = [s for s in LIVE['sessions'] if s['input'] == 'live microphone command' and s['completed']]
completed_regions = ', '.join(s['route'][-1] for s in completed_live)
table([['Hạng mục', 'Kết quả / minh chứng'],
       ['Logic / ROS action giả', f'39/39 pytest; {ros_pass}/{len(ROS["tests"])} tình huống DDS/action đạt.'],
       ['Nav2 thật, đầu vào văn bản', f'{sim_pass}/{len(SIM["results"])} ca A, A→B, C đạt; sai số cuối 0,11 / 0,25 / 0,20 m.'],
       ['ASR tổng hợp', f'Google TTS: small {speech_pass}/3, base 2/3. eSpeak: cả hai 0/3.'],
       ['Micro trực tiếp', f'Đã thử; log xác nhận hoàn tất {completed_regions}. B được gọi khi robot đã ở B.'],
       ['Vùng không tồn tại', 'Vùng Z bị từ chối; không gửi đích mới.']], [146, WIDTH - 146])
p('AMCL được khởi tạo từ ground truth chỉ trong mô phỏng; sai số ban đầu 0,031 m. '
  f'Nhận {SIM["hazard_messages"]} message hazard, {SIM["bump_events"]} sự kiện BUMP trong phép thử, '
  'không suy ra mọi loại va chạm đều đã được đo. Chưa có thống kê WER/accuracy giọng người '
  'hoặc URL video demo được kiểm chứng. Lệnh dừng bằng giọng nói chịu độ trễ thu/nhận dạng. '
  'PyAV 16.0.1 được ghim để tương thích faster-whisper 1.2.1.', caption)
p('Tái hiện: README.md; minh chứng: docs/lab7/validation.md, simulation.json, '
  'live_microphone.json. Tài liệu: ' + link('https://github.com/SYSTRAN/faster-whisper', 'faster-whisper') + '; '
  + link('https://api.nav2.org/actions/humble/navigatetopose.html', 'Nav2 NavigateToPose') + '.', caption)


def footer(canvas, doc):
    canvas.setFont('DV', 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(42, 24, 'TurtleBot 4 · Bài 7 · Thực nghiệm 10/11/2026')
    canvas.drawRightString(A4[0] - 42, 24, f'Trang {doc.page}')


output = HERE / 'report.pdf'
SimpleDocTemplate(str(output), pagesize=A4, leftMargin=42, rightMargin=42,
                  topMargin=32, bottomMargin=38,
                  title='Báo cáo thực hành TurtleBot 4 — Bài 7', author=SUB['student']).build(
                      story, onFirstPage=footer, onLaterPages=footer)
submission = ROOT / SUB['submission_report']
submission.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(output, submission)
print(output)
print(submission)
