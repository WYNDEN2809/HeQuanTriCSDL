# Hướng dẫn sử dụng theo vai trò

Đăng nhập tại `http://127.0.0.1:8000/` (mật khẩu mẫu `ScentStation@2026`). Menu bên trái chỉ hiện các chức năng được phép.

## Khách hàng – màn hình kiosk (`/kiosk/`)
1. Chọn máy → chọn mùi hương (thẻ có giá, nhãn khuyến mãi nếu có). Quét QR nhỏ trên thẻ để xem thông tin sản phẩm trên điện thoại.
2. **Chọn mùi này** → xem lại tên và giá → **Xác nhận & thanh toán**.
3. Quét mã QR thanh toán trước khi đồng hồ đếm ngược về 0 (đơn miễn phí không cần quét).
4. Đặt giấy thử hoặc cổ tay vào khu vực xịt; máy chỉ xịt **một lần**.
5. Nếu báo lỗi sau khi đã trả tiền: ghi lại mã đơn `PAY-...` và gặp nhân viên để được hoàn tiền. Màn hình tự về trang chính sau thời gian không thao tác.

## Platform Super Administrator (`superadmin`)
- **Thương hiệu**: tạo, sửa, tạm khoá thương hiệu; tạo Brand Admin đầu tiên.
- Thanh trên cùng: chọn một thương hiệu để thao tác thay mặt; chọn "tất cả" để xem toàn nền tảng.
- **Nhật ký audit**, **Tổng quan/Báo cáo** toàn nền tảng; khoá tài khoản (thu hồi phiên ngay).

## Brand Administrator (`admin_lumiere`)
- **Nước hoa và địa điểm**: thêm/sửa nước hoa (giá mặc định), địa điểm, thông tin thương hiệu.
- **Khuyến mãi**: *+ Thêm* → chọn loại (giảm %, giá tạm thời, dùng thử miễn phí), phạm vi, thời gian. Nút **Tắt/Bật** để dừng sớm. Giá áp dụng cho các đơn tạo sau đó.
- **Máy và slot**: gán nước hoa, giá, ngưỡng cho từng slot; bật/tắt máy.
- **Nhân viên**: tạo tài khoản và gán vai trò; khoá/mở khoá.
- **Báo cáo**, **Nhật ký audit** của thương hiệu.

## Operations Manager (`ops_lumiere`)
- **Giao dịch**: lọc theo trạng thái; với đơn "đã trả tiền nhưng xịt lỗi" hoặc REVIEW → *Hoàn tiền*, *Xác nhận thủ công*, *Thử lại có kiểm soát* (cần nhập lại mật khẩu). **Đối chiếu**: tải CSV của nhà cung cấp (`provider_transaction_id,amount,status`).
- **Cảnh báo**: tiếp nhận → giao việc → xử lý; cảnh báo quá hạn được đánh dấu leo thang.
- **Máy và slot**: bật/tắt máy hoặc slot khi có sự cố. **Bảo trì**: tạo/giao phiếu.

## Technician (`tech1_lumiere`)
- Chỉ thấy máy và phiếu được giao. Mở phiếu → **Bắt đầu** (máy vào chế độ bảo trì, không nhận đơn mới) → làm checklist → **Xịt thử** (ghi riêng, không tính doanh thu/tồn kho khách) → ghi kết quả → test sau bảo trì → **Hoàn tất**.

## Inventory Staff (`inv_lumiere`)
- **Tồn kho**: nạp thêm, thay chai, đối soát số đếm với thực tế (bắt buộc ghi lý do), xem lịch sử và báo cáo. Nhận cảnh báo sắp hết/hết hàng.

## Viewer (`viewer_lumiere`)
- Chỉ xem giao dịch, bảo trì, tồn kho, báo cáo, danh mục.
