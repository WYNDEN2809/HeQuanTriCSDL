# ScentStation: Nền tảng IoT đa thương hiệu cho máy trải nghiệm và quản lý nước hoa

## 1. Giới thiệu đề tài

ScentStation là nền tảng ứng dụng công nghệ IoT nhằm xây dựng hệ thống máy trải nghiệm nước hoa tự động, hỗ trợ nhiều thương hiệu cùng hoạt động trên một nền tảng. Hệ thống cho phép khách hàng trải nghiệm sản phẩm thông qua máy xịt nước hoa, đồng thời hỗ trợ quản lý sản phẩm, tồn kho, thiết bị và theo dõi hoạt động kinh doanh của từng thương hiệu.

## 2. Nhóm sinh viên thực hiện

| STT | Họ và tên | Mã số sinh viên |
|:---:|---|:---:|
| TV1 | Nguyễn Chánh Tư Duy | 058306002848 |
| TV2 | Nguyễn Hoàng Khang | 092206002101 |
| TV3 | Trương Hoàng Việt Hùng | 079206039582 |
| TV4 | Đặng Ngọc Thùy Dung | 079306005262 |
| TV5 | Tôn Thiên Thanh | 084306000518 |


## 3. Cấu trúc thư mục

```
HeQuanTriCSDL/
├── README.md                  <- file này (hướng dẫn chạy)
├── docker-compose.yml         <- (tuỳ chọn) dựng SQL Server + nạp database bằng Docker
├── application/
│   ├── database/              <- 01..04: tạo DB + dữ liệu mẫu | 05, 06: nâng cấp DB cũ
│   ├── backend/               <- Django: kiosk, API thiết bị, webhook, portal quản lý
│   └── frontend/              <- (giao diện nằm trong backend/templates, thư mục để dành)
├── doc/
│   ├── request_ScentStation.md      đề tài
│   ├── HUONG_DAN_SU_DUNG.md         hướng dẫn dùng theo từng vai trò
│   ├── TAI_LIEU_KY_THUAT.md         kiến trúc, luồng nghiệp vụ, API, bảo mật
│   └── DOI_CHIEU_YEU_CAU.md         đối chiếu từng yêu cầu của đề tài với phần đã làm
└── images/                    <- ERD, use case, activity diagram
```

## 4. Chuẩn bị (làm 1 lần)

| Thành phần | Yêu cầu |
|---|---|
| SQL Server | 2016 trở lên (Developer/Express). Có thể dùng Docker thay thế (mục 3, cách B) |
| ODBC Driver | **ODBC Driver 18 for SQL Server** ([tải](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)) |
| Python | **3.10 – 3.12** (Django 4.2 chưa hỗ trợ 3.13) |
| Trình duyệt | Cần Internet (kiosk tải Bootstrap, thư viện vẽ QR từ CDN) |

## 5. Tạo database

### Cách A – SSMS / Azure Data Studio (khuyên dùng)
Mở và chạy **lần lượt** trong `application/database/`:

| Thứ tự | File | Nội dung | Thời gian |
|---|---|---|---|
| 1 | `01_CreateSchema.sql` | Tạo `ScentStationDB` + 17 bảng (**xoá và tạo lại** nếu đã có) | vài giây |
| 2 | `02_SeedMasterData.sql` | Brand, User, Location, Perfume, Machine, MachineSlot | vài giây |
| 3 | `03_SeedOrders.sql` | ~30.000 đơn, thanh toán, lệnh xịt, nhật ký tồn kho | 30–60 giây |
| 4 | `04_SeedOperations.sql` | Cảnh báo, phiếu bảo trì, sự kiện thiết bị, audit | 15–30 giây |

> File 05 và 06 **chỉ** dùng để nâng cấp database tạo từ bản `01` cũ. Database tạo mới thì bỏ qua.

### Cách B – Docker (không cần cài SQL Server)
```bash
docker compose up -d          # dựng SQL Server 2022 (cổng 1433) và tự nạp 01..04
docker compose logs -f db-init   # chờ thấy "Hoan tat" rồi nhấn Ctrl+C
```
Khi dùng Docker, trong `.env` của backend đặt: `DB_HOST=localhost`, `DB_PORT=1433`, `DB_USER=sa`,
`DB_PASSWORD=ScentStation@2026Db`, `DB_TRUSTED=False`. (Máy Mac chip ARM: image SQL Server cần giả lập x86, có thể chậm/không ổn định – nên dùng máy Windows hoặc SQL Server có sẵn.)

## 6. Cài đặt backend

```bash
cd application/backend

python.exe -m venv venv
venv\Scripts\activate            # Windows        (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env           # Windows        (Mac/Linux: cp .env.example .env)
```
Mở `.env` và sửa `DB_HOST`, `DB_USER`, `DB_PASSWORD` (hoặc `DB_TRUSTED=True` nếu dùng Windows Authentication). Ví dụ:
SQL Express → `DB_HOST=localhost\SQLEXPRESS` (để trống `DB_PORT`).

Khởi tạo Django (**đúng thứ tự**):
```bash
python manage.py makemigrations accounts catalog devices sales inventory maintenance reports
python manage.py migrate
python manage.py reset_sample_passwords    # đặt mật khẩu cho 31 tài khoản mẫu: ScentStation@2026
python manage.py check_db                  # phải báo "OK - 17 model khớp với bảng"
```
> `migrate` chỉ tạo thêm bảng `django_*`, `auth_*`; **không** đụng vào 17 bảng nghiệp vụ (các model đều `managed = False`).
> Nếu đã chạy bản cũ và gặp lỗi "inconsistent migration history": chạy lại `01_CreateSchema.sql` → 02 → 03 → 04 rồi làm lại các lệnh trên từ đầu.

## 7. Chạy dự án

Cần **2 cửa sổ terminal** (đều đã kích hoạt venv, đang ở `application/backend`):
cd ...\application\backend
python.exe -m venv venv
venv\Scripts\activate

```bash
# Terminal 1 – web server
python manage.py runserver

# Terminal 2 – giả lập máy kiosk (heartbeat, nhận lệnh xịt, báo kết quả)
python manage.py run_device_simulator
```
Nếu không kích hoạt được venv, thay `python` bằng `venv\Scripts\python.exe`.

| Địa chỉ | Dành cho |
|---|---|
| http://127.0.0.1:8000/kiosk/ | **Màn hình khách** (chọn mùi → QR → trạng thái) |
| http://127.0.0.1:8000/ | **Portal quản lý** (đăng nhập) |
| http://127.0.0.1:8000/admin/ | Django Admin (chỉ `superadmin`) |

### Tài khoản mẫu (mật khẩu `ScentStation@2026`)
| Tài khoản | Vai trò |
|---|---|
| `superadmin` | Platform Super Administrator (mọi thương hiệu) |
| `admin_lumiere` | Brand Administrator |
| `ops_lumiere` | Operations Manager |
| `tech1_lumiere`, `tech2_lumiere` | Technician |
| `inv_lumiere` | Inventory Staff |
| `viewer_lumiere` | Viewer |

Các thương hiệu: `lumiere`, `aurelia`, `saigon`, `noir`, `hoalan` (ví dụ `admin_noir`). Đăng nhập `admin_lumiere` rồi `admin_noir` để thấy mỗi người chỉ có dữ liệu của brand mình.

## 8. Demo nhanh

1. Mở `/kiosk/` → chọn một máy → **Chọn mùi này** → **Xác nhận** → xuất hiện mã QR + đồng hồ đếm ngược.
2. Bấm link **"mở trang thanh toán giả lập"** → **Thanh toán thành công**.
3. Quay lại kiosk: trạng thái tự chuyển *Đã nhận thanh toán → Hoàn tất*; terminal 2 in log máy xịt.
4. Đăng nhập `admin_lumiere` → **Giao dịch** thấy đơn vừa tạo, **Tồn kho** giảm 1.
5. **Khuyến mãi:** `admin_lumiere` → *Nước hoa và địa điểm* → *+ Thêm* khuyến mãi (ví dụ giảm 20%, hoặc *Dùng thử miễn phí*) → mở lại kiosk thấy giá mới và nhãn khuyến mãi. Đơn miễn phí không cần quét QR, máy xịt ngay.
6. **QR sản phẩm:** mỗi thẻ mùi hương trên kiosk có QR nhỏ → quét bằng điện thoại để xem thông tin. Muốn điện thoại truy cập được, chạy `python manage.py runserver 0.0.0.0:8000`, thêm IP máy vào `DJANGO_ALLOWED_HOSTS` trong `.env` và mở kiosk bằng địa chỉ IP đó (không dùng `127.0.0.1`).

## 9. Kiểm thử

```bash
python manage.py run_all_selftests
```
Chạy toàn bộ bộ tự kiểm thử trên **database thật** (mỗi bài đều `ROLLBACK`, không để lại dữ liệu) – kỳ vọng tất cả `[PASS]`:

| Lệnh | Nội dung |
|---|---|
| `selftest_sales` | chữ ký/số tiền webhook, webhook trùng, 1 đơn = tối đa 1 lệnh xịt, hết hạn, mất kết quả → REVIEW, tách brand |
| `selftest_machines` / `selftest_inventory` | máy & slot, tồn kho, nạp/thay chai |
| `selftest_alerts` / `selftest_transactions` / `selftest_maintenance` | cảnh báo, hoàn tiền/đối soát, bảo trì + checklist |
| `selftest_accounts` | nhân viên, vai trò, tenant, danh mục |
| `selftest_campaigns` | khuyến mãi, dùng thử miễn phí, giá tạm thời, QR sản phẩm |

## 10. Xử lý sự cố thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| `Data source name not found` / `Can't open lib 'ODBC Driver 18…'` | Chưa cài ODBC Driver 18, hoặc `DB_DRIVER` trong `.env` không đúng tên driver đã cài |
| `Login failed for user` | Sai `DB_USER`/`DB_PASSWORD`; SQL Server chưa bật *SQL Server and Windows Authentication mode*; hoặc dùng `DB_TRUSTED=True` |
| `Cannot open database "ScentStationDB"` | Chưa chạy `01_CreateSchema.sql` |
| `Invalid object name 'Campaign'` / `Invalid column name 'CampaignID'` | Database tạo từ bản `01` cũ → chạy `06_AddCampaign.sql` |
| `Invalid object name 'MaintenanceChecklistItem'` | Chạy `05_AddMaintenanceChecklist.sql` |
| Kiosk báo "chưa có máy nào" | Chưa chạy `run_device_simulator` (chỉ máy có heartbeat mới hiện) |
| Không đăng nhập được | Chưa chạy `reset_sample_passwords` |
| Không bấm "Kết thúc bảo trì" được | Máy còn phiếu bảo trì đang mở (dữ liệu mẫu có nhiều phiếu mở) – hoàn tất hoặc huỷ phiếu trước |
| Python 3.13 báo lỗi khi cài Django 4.2 | Dùng Python 3.10–3.12 |

## 11. Ghi chú & giới hạn

- Máy kiosk thật được **giả lập**; giao thức máy ↔ cloud là HTTP có chữ ký HMAC (token thiết bị, chữ ký lệnh, hạn lệnh, ack trước khi xịt). Tài liệu kỹ thuật mô tả cách ánh xạ sang MQTT khi có phần cứng.
- Thanh toán dùng **sandbox** (webhook ký HMAC giống nhà cung cấp thật); chưa tích hợp cổng thanh toán thật.
- Các cột VARCHAR không lưu dấu tiếng Việt nên tên nước hoa/địa điểm/khuyến mãi được lưu không dấu (`ascii_text`); nội dung có dấu nằm ở `AuditLog` (NVARCHAR).
- Token thiết bị suy ra từ `DEVICE_API_SECRET` + serial (đủ cho prototype); bản thật nên cấp khoá riêng cho từng máy.
- Khuyến mãi *Dùng thử miễn phí* chưa giới hạn số lần/khách; cần thêm quy tắc chống lạm dụng nếu triển khai thật.
- Trước khi triển khai thật: đổi `DJANGO_SECRET_KEY`, `PAYMENT_WEBHOOK_SECRET`, `DEVICE_API_SECRET`, đặt `DJANGO_DEBUG=False`, bật HTTPS.
