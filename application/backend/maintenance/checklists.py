"""Mau checklist theo loai bao tri (luu trong DB o bang MaintenanceChecklistItem, cot NVARCHAR nen co dau)."""

POST_TEST_TEXT = "Xịt thử sau bảo trì thành công"      # chi tick duoc bang chuc nang "Xit thu sau bao tri"
RESULT_TEXT = "Kết quả sửa chữa / ghi chú (bắt buộc để đóng phiếu)"

_POST_ITEMS = [
    "Đóng cửa và khóa máy",
    "Vệ sinh, kiểm tra bên ngoài máy",
]

# maintenance_type -> danh sach (phase, noi dung)
TEMPLATES = {
    "INSPECTION": [
        ("INSPECTION", "Kiểm tra cửa và khóa máy"),
        ("INSPECTION", "Kiểm tra đầu phun và ống dẫn"),
        ("INSPECTION", "Kiểm tra cảm biến cân / mức nước hoa"),
        ("INSPECTION", "Kiểm tra dấu hiệu rò rỉ"),
        ("INSPECTION", "Kiểm tra nguồn điện và kết nối mạng"),
        ("INSPECTION", "Vệ sinh khu vực xịt"),
    ],
    "REPAIR": [
        ("INSPECTION", "Ghi nhận hiện tượng lỗi"),
        ("INSPECTION", "Kiểm tra mã lỗi và nhật ký thiết bị"),
        ("REPAIR", "Xác định nguyên nhân hỏng"),
        ("REPAIR", "Thực hiện sửa chữa"),
        ("REPAIR", "Kiểm tra lại các kết nối sau sửa"),
    ],
    "PART_REPLACEMENT": [
        ("INSPECTION", "Ghi nhận linh kiện lỗi"),
        ("REPAIR", "Tắt nguồn trước khi tháo"),
        ("REPAIR", "Thay linh kiện (ghi rõ linh kiện/chi phí ở phần kết quả)"),
        ("REPAIR", "Hiệu chuẩn lại sau khi thay"),
    ],
    "CALIBRATION": [
        ("INSPECTION", "Kiểm tra liều xịt hiện tại"),
        ("REPAIR", "Hiệu chuẩn thời gian xịt"),
        ("REPAIR", "Đối chiếu lượng hao hụt mỗi lần xịt"),
    ],
    "REFILL_SUPPORT": [
        ("REFILL_SUPPORT", "Xác nhận đúng mùi hương cho đúng slot"),
        ("REFILL_SUPPORT", "Lắp chai / cartridge"),
        ("REFILL_SUPPORT", "Ghi nhận cân nặng trước và sau khi lắp"),
        ("REFILL_SUPPORT", "Kiểm tra rò rỉ tại chỗ nối"),
    ],
}


def items_for(maintenance_type):
    """Danh sach (phase, text) day du: cac muc theo loai + sau bao tri + ket qua."""
    items = list(TEMPLATES.get(maintenance_type, TEMPLATES["INSPECTION"]))
    items += [("POST_MAINTENANCE", t) for t in _POST_ITEMS]
    items.append(("POST_MAINTENANCE", POST_TEST_TEXT))
    items.append(("RESULT", RESULT_TEXT))
    return items
