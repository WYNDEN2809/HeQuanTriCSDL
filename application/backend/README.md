# ScentStation – Backend (Django + SQL Server)

Thư mục này chứa project Django. Database là SQL Server tạo bằng 4 file trong `../database/`
(Django **không** tạo/sửa 15 bảng nghiệp vụ – các model đều `managed = False`).

## 1. Chuẩn bị (làm 1 lần)
1. Chạy 4 file SQL `01 → 04` trong `application/database/` để có database `ScentStationDB`.
2. Cài **ODBC Driver 18 for SQL Server**: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server
3. Python 3.10 – 3.12. Tạo môi trường ảo và cài thư viện:
   ```bash
   cd application/backend
   python -m venv venv
   venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   ```
4. Tạo file cấu hình: sao chép `.env.example` thành `.env` rồi sửa `DB_HOST`, `DB_USER`, `DB_PASSWORD`
   (hoặc `DB_TRUSTED=True` nếu dùng Windows Authentication).

## 2. Khởi tạo Django (thứ tự quan trọng)
```bash
python manage.py makemigrations accounts catalog devices sales inventory maintenance reports
python manage.py migrate
python manage.py reset_sample_passwords   # đặt mật khẩu Django cho 31 user mẫu: ScentStation@2026
python manage.py check_db                 # đếm số dòng 15 bảng, đối chiếu model <-> bảng thật
python manage.py runserver
```
Mở http://127.0.0.1:8000/ và đăng nhập.

> `migrate` chỉ tạo thêm các bảng của Django (`django_*`, `auth_*`) trong cùng database,
> **không** đụng vào 15 bảng ScentStation.
> Nên commit các file trong `*/migrations/` sau khi chạy `makemigrations`, để cả nhóm dùng chung.

## 3. Tài khoản thử
| Tài khoản | Vai trò |
|---|---|
| `superadmin` | Platform Super Administrator (thấy mọi brand, vào được `/admin/`) |
| `admin_lumiere` | Brand Admin của Lumiere Parfums |
| `ops_lumiere` | Operations Manager |
| `tech1_lumiere`, `tech2_lumiere` | Technician |
| `inv_lumiere` | Inventory Staff |
| `viewer_lumiere` | Viewer |

Các brand: `lumiere`, `aurelia`, `saigon`, `noir`, `hoalan` (ví dụ `admin_noir`).
Mật khẩu: `ScentStation@2026` (sau khi chạy `reset_sample_passwords`).
Hãy thử đăng nhập `admin_lumiere` và `admin_noir`: mỗi người chỉ thấy số liệu của brand mình.

## 4. Cấu trúc
```
backend/
├── config/        settings, urls
├── accounts/      User (ánh xạ bảng [User]), BrandMember, middleware brand, phân quyền (permissions.py)
├── catalog/       Brand, Location, Perfume
├── devices/       Machine, MachineSlot, DeviceEvent, Alert
├── sales/         Order (bảng Orders), Payment, DispenseTransaction
├── inventory/     InventoryLog
├── maintenance/   MaintenanceRecord
├── reports/       AuditLog, audit.py (log_action), trang tổng quan
├── kiosk/         Giao diện khách hàng trên màn hình cảm ứng (chọn mùi, QR, trạng thái)
├── templates/     base.html (Bootstrap 5), login, home
└── static/css/
```

## 5. Quy ước cho cả nhóm
- Truy vấn dữ liệu nghiệp vụ **luôn** đi qua `accounts.permissions.scope_queryset(qs, request, "<đường dẫn tới BrandID>")`
  hoặc `BrandScopedQuerysetMixin` để brand này không thấy dữ liệu brand khác.
- View chỉ cho một số vai trò: dùng decorator `@brand_role_required("OPS_MANAGER", "BRAND_ADMIN")`.
- Thao tác quan trọng (đổi giá, refill, hoàn tiền, đổi quyền…) gọi `reports.audit.log_action(...)`.
- Schema đổi ở đâu? Sửa `01_CreateSchema.sql` rồi sửa model tương ứng – model chỉ phản chiếu schema.
- Test: do model `managed = False`, test database của Django sẽ không có bảng nghiệp vụ.
  Khi viết test sẽ cần cấu hình riêng (làm ở bước sau).


---

# Phần 2 – Luồng bán hàng đầu cuối (kiosk → thanh toán → lệnh xịt → thiết bị)

## Chạy
Cần 2 cửa sổ terminal (đều đã kích hoạt venv, đang ở thư mục backend):
```
# Terminal 1
python manage.py runserver

# Terminal 2  (giả lập các máy kiosk: heartbeat + nhận lệnh xịt)
python manage.py run_device_simulator
```
> Nếu venv không kích hoạt được, thay `python` bằng `venv\Scripts\python.exe`.

## Demo từng bước
1. Mở http://127.0.0.1:8000/kiosk/ → chọn một máy (chỉ máy đang có heartbeat mới hiện).
2. Bấm "Chọn mùi này" → xác nhận → trang có mã QR và đồng hồ đếm ngược.
3. Bấm link "mở trang thanh toán giả lập" → "Thanh toán thành công".
4. Quay lại màn hình kiosk: trạng thái tự chuyển "Đã nhận thanh toán" → "Hoàn tất" (khi máy giả lập xịt xong).
5. Terminal 2 in ra log của máy. Đăng nhập portal (`admin_lumiere`...) → trang tổng quan có đơn vừa tạo.

## Chứng minh các quy tắc cốt lõi
**a) Tự kiểm thử trên database thật (dữ liệu được ROLLBACK, không để lại gì):**
```
python manage.py selftest_sales
```
Kết quả mong đợi: tất cả dòng `PASS` (khoảng 35 kiểm tra), gồm: sai chữ ký/sai số tiền bị từ chối; webhook gửi trùng
không tạo lệnh xịt thứ hai; ack lệnh hai lần bị từ chối; gửi sai máy bị từ chối; chỉ DISPENSED khi máy báo thành công
và tồn kho giảm đúng 1; trả tiền sau khi hết hạn/hủy → REVIEW, không xịt; mất kết quả → REVIEW, không tự xịt lại;
tách dữ liệu giữa các brand.

**b) Webhook trùng bằng HTTP thật:** tạo đơn trên kiosk (đừng bấm thanh toán), lấy mã đơn `PAY-...` rồi:
```
python manage.py send_webhook PAY-20261105-XXXXXXXX --times 3
```
Lần 1 `payment_confirmed`, lần 2 và 3 `duplicate_notification`; chỉ có đúng 1 lệnh xịt.
Thử thêm: `--bad-signature` (401), `--amount 1` (400), `--status FAILED`.

**c) Mô phỏng sự cố:** `python manage.py run_device_simulator --fail-rate 0.5 --uncertain-rate 0.3`
→ nhiều đơn "đã trả tiền nhưng xịt lỗi" (DISPENSE_FAILED) hoặc "mất kết quả" (REVIEW, hiện ở số liệu đỏ trên trang tổng quan).

## Cách hoạt động (tóm tắt để trả lời thầy cô)
- Đơn chỉ do **backend** xác nhận thanh toán qua webhook có chữ ký HMAC-SHA256 (kiểm tra chữ ký, mã tham chiếu, số tiền, loại tiền, chống trùng theo `provider_transaction_id`).
- **Một đơn tối đa một lệnh xịt**: ràng buộc `UNIQUE(OrderID)` trên `DispenseTransaction` + cập nhật có điều kiện (compare-and-set).
- Lệnh xịt có `command_id`, hạn, **chữ ký**; máy tự kiểm tra chữ ký/hạn/cửa/tồn kho/bảo trì, phải **ack** trước khi xịt, rồi báo kết quả.
- Trạng thái đơn: `PENDING` (kèm Payment SUCCESS = đã trả tiền, chờ xịt) → `DISPENSED` / `DISPENSE_FAILED` / `REVIEW`; không bao giờ tự xịt lại.
- Máy online dựa trên heartbeat: `run_device_simulator` cũng đóng vai bộ giám sát, máy không còn heartbeat > 90 giây sẽ thành OFFLINE (kèm sự kiện + cảnh báo) và không nhận đơn mới.
- Các thao tác quan trọng được ghi `AuditLog` (PAYMENT_CONFIRMED, DISPENSE_COMMAND_CREATED, DISPENSE_RESULT, DISPENSE_TIMEOUT, PAYMENT_AFTER_EXPIRY...).

## Giới hạn hiện tại (để bước sau)
- Giao diện portal cho Operations Manager (xem đơn lỗi, **hoàn tiền / thử lại có kiểm soát**, đóng REVIEW) chưa có – hiện chỉ thấy số liệu và xem qua Django Admin.
- Refill, phiếu bảo trì, cảnh báo trên portal: Bước 3.
- Token thiết bị suy ra từ `DEVICE_API_SECRET` + serial (đủ cho prototype); bản thật nên cấp khóa riêng cho từng máy.
