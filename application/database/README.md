# ScentStation – Database (SQL Server / T-SQL)

CSDL của nền tảng ScentStation gồm **17 bảng** (15 bảng ERD + `MaintenanceChecklistItem` + `Campaign`), kèm dữ liệu mẫu lớn (\~30.000 đơn hàng).

## Yêu cầu

* SQL Server 2016 trở lên (Developer/Express đều được)
* SSMS

## Cách cài đặt

Chạy **lần lượt** 4 file đầu trong thư mục này (file 01 đã gồm đủ 17 bảng):

|Thứ tự|File|Nội dung|Thời gian ước tính|
|-|-|-|-|
|1|`01\_CreateSchema.sql`|Tạo database `ScentStationDB` và 17 bảng (**xóa và tạo lại** nếu đã tồn tại)|vài giây|
|2|`02\_SeedMasterData.sql`|Brand, User, BrandMember, Location, Perfume, Machine, MachineSlot|vài giây|
|3|`03\_SeedOrders.sql`|Orders, Payment, DispenseTransaction, InventoryLog|30–60 giây|
|4|`04\_SeedOperations.sql`|Alert, MaintenanceRecord, DeviceEvent, AuditLog, index, truy vấn kiểm tra|15–30 giây|

Mỗi file tự kiểm tra thứ tự chạy và chặn nạp trùng dữ liệu. Muốn làm lại từ đầu thì chạy lại file 01.

> Cẩn thận: file 01 xóa toàn bộ database. Không chạy lại khi database đã có dữ liệu thật.

## Quy mô dữ liệu mẫu

Chỉnh các biến `@Total...` ở đầu file 03 và 04 để tăng hoặc giảm lượng dữ liệu.

## Tài khoản mẫu

* Super admin: `superadmin`
* Mỗi brand có 6 tài khoản dạng `<vai\_trò>\_<brand>`, ví dụ `admin\_lumiere`, `ops\_lumiere`, `tech1\_lumiere`, `inv\_lumiere`, `viewer\_lumiere`
* Các brand: `lumiere`, `aurelia`, `saigon`, `noir`, `hoalan`
* Mật khẩu trong database là hash SHA-256 chỉ dùng cho dữ liệu mẫu. Backend Django sẽ đặt lại mật khẩu bằng cơ chế hash của Django.

## Quy ước làm việc nhóm

* Mọi thay đổi schema phải sửa trong `01\_CreateSchema.sql`, cập nhật ERD trong thư mục `images/`
* Không commit file `.bak`, `.mdf`, `.ldf` hay chuỗi kết nối chứa mật khẩu.


## Nâng cấp database đã tạo từ trước

| File | Khi nào chạy |
|-|-|
| `05_AddMaintenanceChecklist.sql` | Database tạo bằng bản `01` cũ (chưa có bảng checklist bảo trì) |
| `06_AddCampaign.sql` | Database tạo bằng bản `01` cũ (chưa có bảng `Campaign` và cột `Orders.CampaignID`) |

Cả hai file chạy lại nhiều lần vẫn an toàn. Database tạo mới bằng `01` hiện tại thì **không cần** chạy 05, 06.
