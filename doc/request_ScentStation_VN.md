# ScentStation: Nền tảng IoT đa thương hiệu cho máy trải nghiệm và quản lý nước hoa

## 3.2. Nội dung đề xuất chính (bao gồm kết quả và sản phẩm)

### a) Bối cảnh

Khách hàng nước hoa thường cần trải nghiệm hương thơm trước khi mua sản phẩm kích thước đầy đủ. Tuy nhiên, việc tiếp cận mẫu thử thường bị giới hạn tại các cửa hàng bán lẻ có nhân viên, trong khi các thương hiệu gặp khó khăn trong việc đo lường mức độ quan tâm thực tế của khách hàng, kiểm soát lượng tiêu thụ mẫu thử và vận hành các chiến dịch lấy mẫu trên nhiều địa điểm. Việc kiểm tra thủ công mức nước hoa và tình trạng máy móc cũng làm tăng chi phí vận hành và có thể dẫn đến tình trạng hết hàng hoặc gián đoạn dịch vụ.

Những tiến bộ trong Internet of Things (IoT), thanh toán không dùng tiền mặt và quản lý thiết bị từ xa đã tạo điều kiện cho mô hình trải nghiệm nước hoa tự động. **ScentStation** được đề xuất như một nền tảng tích hợp, trong đó người dùng chọn hương thơm trên ki-ốt, hoàn tất thanh toán bằng mã QR và nhận một lần xịt được kiểm soát. Nền tảng cũng cung cấp quản lý cách ly theo tenant cho nhiều thương hiệu nước hoa, ước tính tồn kho theo thời gian thực, giám sát thiết bị, quy trình bảo trì, đối soát giao dịch và phân tích vận hành.

### b) Giải pháp đề xuất

Dự án này đề xuất **ScentStation**, một hệ sinh thái trải nghiệm nước hoa hỗ trợ IoT bao gồm ki-ốt đa hương, backend đám mây và cổng quản lý đa tenant. Hệ thống sẽ:

- Cho phép khách hàng chọn hương thơm, hoàn tất thanh toán QR và nhận một lần xịt được đo lường.
- Giám sát từ xa kết nối máy, cảm biến, trạng thái khe, kết quả phân phối và mức nước hoa ước tính.
- Hỗ trợ không gian làm việc cách ly theo thương hiệu, quản trị dựa trên vai trò, danh mục sản phẩm, giá cả, địa điểm và chiến dịch.
- Quản lý chai hoặc hộp mực, lịch sử nạp lại, cảnh báo, phiếu bảo trì và hoạt động của kỹ thuật viên.
- Cung cấp đối soát giao dịch, nhật ký kiểm toán, bảng điều khiển và báo cáo theo thương hiệu, máy, địa điểm và hương thơm.

### c) Yêu cầu chức năng

#### 1. Quản trị viên Siêu cấp Nền tảng (Platform Super Administrator)

Quản trị viên Siêu cấp Nền tảng quản lý toàn bộ nền tảng ScentStation và tất cả các thương hiệu nước hoa tham gia.

- Tạo, cập nhật, kích hoạt, tạm ngưng và quản lý các tenant thương hiệu nước hoa.
- Tạo và quản lý tài khoản Quản trị viên Thương hiệu cho mỗi tenant.
- Cấu hình các thiết lập toàn nền tảng, nhà cung cấp thanh toán, chính sách thiết bị, mẫu thông báo và tham số hệ thống.
- Giám sát tất cả máy đã đăng ký, địa điểm, kết nối thiết bị, phiên bản firmware, cảnh báo quan trọng và dịch vụ hệ thống.
- Xem thống kê toàn nền tảng, bao gồm thương hiệu, máy, giao dịch, hoạt động phân phối và sự cố vận hành.
- Truy cập nhật ký kiểm toán hệ thống để điều tra bảo mật và giám sát vận hành.
- Quản lý vai trò và quyền ở cấp nền tảng.
- Đảm bảo dữ liệu thuộc các thương hiệu nước hoa khác nhau được cách ly logic.
- Thu hồi quyền truy cập người dùng hoặc thiết bị khi phát hiện hoạt động đáng ngờ.

#### 2. Quản trị viên Thương hiệu (Brand Administrator)

Quản trị viên Thương hiệu quản lý dữ liệu kinh doanh, người dùng, sản phẩm, máy móc và hoạt động thuộc về một thương hiệu nước hoa.

- Quản lý thông tin thương hiệu, logo, mô tả, thông tin liên hệ và nội dung hiển thị trên ki-ốt.
- Tạo, cập nhật, vô hiệu hóa và gán tài khoản cho Quản lý Vận hành, Kỹ thuật viên, Nhân viên Kho và Người xem.
- Cấu hình vai trò và quyền trong phạm vi thương hiệu được gán.
- Quản lý sản phẩm nước hoa, bao gồm tên sản phẩm, mô tả, hình ảnh, nốt hương, giá mỗi lần xịt và tình trạng sẵn có.
- Quản lý địa điểm và gán máy cho các địa điểm cụ thể.
- Cấu hình sản phẩm nước hoa, giá bán và tình trạng sẵn có của từng khe máy.
- Cấu hình giờ hoạt động của máy, ngưỡng tồn kho thấp và cài đặt thông báo.
- Xem trạng thái của tất cả máy thuộc thương hiệu.
- Xem giao dịch, kết quả phân phối, tình trạng tồn kho, cảnh báo, lịch sử nạp lại và hoạt động bảo trì.
- Cấu hình chiến dịch khuyến mãi, chiến dịch dùng thử miễn phí hoặc giá tạm thời.
- Xem và xuất báo cáo vận hành và kinh doanh theo hương thơm, máy, địa điểm và khoảng thời gian.

#### 3. Quản lý Vận hành (Operations Manager)

Quản lý Vận hành giám sát hoạt động máy hàng ngày và xử lý sự cố giao dịch hoặc thiết bị.

- Giám sát trạng thái máy, bao gồm trạng thái online/offline, thời gian kết nối cuối, chế độ hoạt động, khe đang hoạt động và cảnh báo hiện tại.
- Xem nước hoa hiện đang lắp trong mỗi khe và số lượng còn lại ước tính.
- Bật hoặc tắt từ xa một máy hoặc một khe riêng lẻ khi xảy ra sự cố vận hành.
- Xem xét các giao dịch đang chờ, thành công, thất bại, hết hạn và đã hoàn tiền.
- Xác định các giao dịch trong đó thanh toán thành công nhưng phân phối thất bại hoặc chưa được xác nhận.
- Khởi tạo quy trình thử lại được ủy quyền, hoàn tiền hoặc xem xét thủ công theo chính sách vận hành.
- Nhận cảnh báo về máy offline, tồn kho thấp, khe trống, cửa mở, nghi ngờ rò rỉ, lỗi cảm biến và lỗi phân phối.
- Tạo, ưu tiên, gán và giám sát phiếu bảo trì.
- Giám sát thời gian hoạt động, thời gian dừng, tần suất nạp lại, tần suất sự cố và thời gian giải quyết của máy.
- Xem bảng điều khiển và báo cáo vận hành cho thương hiệu hoặc địa điểm được gán.

#### 4. Kỹ thuật viên (Technician)

Kỹ thuật viên thực hiện kiểm tra, hỗ trợ nạp lại, chẩn đoán và bảo trì cho các máy được gán.

- Xem các máy được gán, cảnh báo đang hoạt động và phiếu bảo trì.
- Xác thực trước khi truy cập các chức năng bảo trì hoặc chẩn đoán.
- Đưa máy vào chế độ bảo trì để ngăn giao dịch khách hàng mới.
- Xem thông tin máy, phiên bản firmware, số liệu cảm biến, mã lỗi và sự kiện thiết bị gần đây.
- Thực hiện các thao tác chẩn đoán được ủy quyền trên máy hoặc một khe được chọn.
- Chạy lần xịt thử nghiệm được kiểm soát và được ghi nhận riêng biệt với giao dịch khách hàng.
- Ghi lại kết quả kiểm tra, vấn đề đã xác định, hành động khắc phục và linh kiện đã thay thế.
- Hoàn thành danh sách kiểm tra bảo trì có thể cấu hình.
- Ghi lại ghi chú hỗ trợ hoặc hình ảnh khi cần thiết.
- Thực hiện kiểm tra sau bảo trì trước khi đưa máy trở lại hoạt động bình thường.
- Chỉ đóng phiếu bảo trì sau khi ghi nhận kết quả sửa chữa.
- Xem lịch sử bảo trì và hỏng hóc của các máy được gán.

#### 5. Nhân viên Kho (Inventory Staff)

Nhân viên Kho quản lý chai hoặc hộp mực nước hoa và thực hiện các thao tác nạp lại hoặc thay thế.

- Quản lý lô tồn kho nước hoa, bao gồm sản phẩm, số lô, số lượng, ngày nhận và ngày hết hạn.
- Đăng ký từng chai hoặc hộp mực nước hoa với mã định danh duy nhất.
- Xem chai hoặc hộp mực theo trạng thái, bao gồm sẵn có, đã lắp, gần hết, trống, hư hỏng và hết hạn.
- Gán một chai hoặc hộp mực cho một khe máy cụ thể.
- Xác minh rằng hương thơm đúng được lắp vào khe đúng.
- Ghi lại trọng lượng hoặc số lượng đo được trước và sau khi lắp đặt.
- Ghi lại nhân viên, thời gian, máy, khe, chai trước và chai mới cho mỗi lần nạp lại hoặc thay thế.
- Đối soát tồn kho ước tính với số liệu đo từ cảm biến.
- Ghi lại điều chỉnh tồn kho cùng với lý do bắt buộc.
- Nhận cảnh báo tồn kho thấp, tiêu thụ bất thường và hết hạn.
- Xem lịch sử di chuyển tồn kho và nạp lại.
- Tạo báo cáo tồn kho theo nước hoa, lô, máy, địa điểm và khoảng thời gian.

#### 6. Khách hàng / Người dùng Ki-ốt (Customer / Kiosk User)

Khách hàng sử dụng ki-ốt để chọn, thanh toán và nhận trải nghiệm nước hoa.

- Xem tất cả hương thơm hiện đang có sẵn trên máy.
- Xem thông tin hương thơm, bao gồm thương hiệu, tên sản phẩm, mô tả, nốt hương, hình ảnh, giá và hướng dẫn sử dụng.
- Chọn một hương thơm sẵn có cho phiên trải nghiệm.
- Xem lại và xác nhận hương thơm đã chọn cùng giá trước khi tạo đơn hàng.
- Nhận mã QR được tạo động để thanh toán.
- Xem trạng thái thanh toán hiện tại, bao gồm đang chờ, thành công, thất bại, đã hủy hoặc hết hạn.
- Nhận hướng dẫn đặt giấy thử hoặc cổ tay vào khu vực xịt được chỉ định.
- Nhận một lần xịt được kiểm soát chỉ sau khi backend xác nhận thanh toán thành công.
- Xem trạng thái phân phối, bao gồm đang xử lý, thành công hoặc thất bại.
- Nhận hướng dẫn khôi phục rõ ràng khi thanh toán thành công nhưng phân phối thất bại.
- Quét mã QR sản phẩm để xem thêm thông tin, khuyến mãi hoặc kênh mua hàng.
- Tự động quay về màn hình chính sau giao dịch hoặc hết thời gian không hoạt động.

#### 7. Quản lý Thương hiệu, Người dùng và Truy cập

Hệ thống phải cung cấp quản lý tài khoản đa tenant và kiểm soát truy cập dựa trên vai trò.

- Liên kết mỗi người dùng với một thương hiệu nước hoa và một hoặc nhiều vai trò được ủy quyền.
- Giới hạn người dùng trong các chức năng và dữ liệu thuộc tenant và phạm vi vận hành được gán.
- Ngăn người dùng của một thương hiệu truy cập máy, sản phẩm, giao dịch, tồn kho hoặc báo cáo thuộc thương hiệu khác.
- Cho phép quản trị viên được ủy quyền kích hoạt, vô hiệu hóa, khóa hoặc đặt lại tài khoản người dùng.
- Hỗ trợ gán quyền theo vai trò, địa điểm, máy hoặc trách nhiệm vận hành.
- Ghi lại các lần đăng nhập, thay đổi tài khoản, thay đổi vai trò và thay đổi quyền.
- Chấm dứt hoặc thu hồi phiên đang hoạt động khi tài khoản bị vô hiệu hóa.
- Yêu cầu ủy quyền bổ sung cho các hành động nhạy cảm như hoàn tiền, điều chỉnh tồn kho, xịt chẩn đoán và cấu hình lại máy.

#### 8. Quản lý Máy và Khe

Hệ thống phải quản lý các máy nước hoa vật lý và các khe được điều khiển độc lập của chúng.

- Đăng ký mỗi máy bằng số sê-ri duy nhất và định danh thiết bị.
- Kích hoạt và liên kết máy với một tenant và địa điểm hoạt động.
- Cấu hình số lượng và mã định danh của các khe có sẵn trên mỗi máy.
- Gán một chai hoặc hộp mực nước hoa đang hoạt động cho mỗi khe.
- Ngăn một khe có nhiều chai đang hoạt động cùng lúc.
- Cấu hình giá khe, sản phẩm, ngưỡng tồn kho thấp, thời lượng xịt hoặc liều lượng đã hiệu chuẩn và tình trạng sẵn có.
- Hiển thị kết nối máy, chế độ hoạt động, phiên bản firmware, phiên bản cấu hình và thời gian giao tiếp cuối.
- Cho phép người dùng được ủy quyền bật hoặc tắt toàn bộ máy hoặc các khe được chọn.
- Duy trì lịch sử lắp đặt, di dời, quyền sở hữu, cấu hình và bảo dưỡng máy.
- Ghi lại tất cả thay đổi cấu hình quan trọng vào nhật ký kiểm toán.

#### 9. Quản lý Đơn hàng và Thanh toán

Hệ thống phải quản lý an toàn quy trình đơn hàng và thanh toán của khách hàng.

- Chỉ cho phép tạo đơn hàng khi máy và khe được chọn đang sẵn có.
- Lưu trữ tenant, máy, khe, sản phẩm nước hoa, giá, đơn vị tiền tệ và thời gian hết hạn tại thời điểm tạo đơn hàng.
- Tạo mã tham chiếu thanh toán duy nhất và mã QR cho mỗi đơn hàng.
- Nhận thông báo thanh toán từ nhà cung cấp thanh toán đã cấu hình.
- Xác minh chữ ký webhook, mã tham chiếu thanh toán, số tiền đã thanh toán, đơn vị tiền tệ và trạng thái giao dịch.
- Ngăn xử lý thông báo thanh toán trùng lặp nhiều hơn một lần.
- Đánh dấu các đơn hàng chưa thanh toán là hết hạn sau thời gian chờ đã cấu hình.
- Ngăn các đơn hàng thất bại, đã hủy hoặc hết hạn tạo lệnh phân phối.
- Duy trì lịch sử trạng thái thanh toán và đơn hàng đầy đủ.
- Hỗ trợ quy trình hoàn tiền hoặc xem xét thủ công khi thanh toán thành công nhưng phân phối không thành công.
- Đối soát giao dịch nội bộ với hồ sơ của nhà cung cấp thanh toán.
- Cho phép người dùng được ủy quyền tìm kiếm giao dịch theo thời gian, máy, địa điểm, nước hoa, mã tham chiếu thanh toán và trạng thái.

#### 10. Quản lý Phân phối An toàn

Hệ thống phải đảm bảo rằng mỗi thanh toán hợp lệ chỉ tạo ra không quá một lần xịt nước hoa.

- Chỉ tạo lệnh phân phối sau khi backend xác minh thanh toán thành công.
- Gán cho mỗi lệnh một mã định danh duy nhất, máy đích, khe đích, thời gian tạo, thời gian hết hạn và chữ ký bảo mật.
- Đảm bảo một đơn hàng không có nhiều hơn một lệnh phân phối đang hoạt động.
- Gửi lệnh đến máy đúng thông qua kênh giao tiếp IoT bảo mật.
- Yêu cầu thiết bị xác nhận lệnh trước khi thực thi.
- Yêu cầu thiết bị từ chối các lệnh không hợp lệ, hết hạn, trùng lặp hoặc địa chỉ sai.
- Ngăn phân phối khi máy đang ở chế độ bảo trì, cửa mở, khe được chọn trống hoặc có lỗi nghiêm trọng.
- Chỉ kích hoạt khe được chọn cho một chu kỳ phân phối đã hiệu chuẩn.
- Ghi lại xác nhận lệnh, thời gian thực thi, kết quả, dữ liệu cảm biến liên quan và mã lỗi.
- Chỉ cập nhật đơn hàng thành DISPENSED sau khi nhận kết quả thành công từ máy.
- Xử lý kết quả hết thời gian hoặc không chắc chắn mà không tự động tạo lần xịt thứ hai không kiểm soát.
- Gửi kết quả phân phối không thành công hoặc không chắc chắn vào quy trình xem xét vận hành.

#### 11. Giám sát và Giao tiếp Thiết bị IoT

Hệ thống phải giám sát máy từ xa và trao đổi dữ liệu an toàn với các thiết bị IoT.

- Nhận thông điệp heartbeat định kỳ từ mỗi máy đã đăng ký.
- Xác định máy đang online, không ổn định hoặc offline dựa trên heartbeat gần nhất.
- Thu thập telemetry như trọng lượng khe, nước hoa còn lại ước tính, trạng thái cửa, trạng thái rò rỉ, trạng thái bộ truyền động và trạng thái nguồn.
- Nhận sự kiện thiết bị như khởi động, tắt máy, kết nối lại, chế độ bảo trì, lỗi cảm biến và lỗi phân phối.
- Gửi lệnh bảo mật cho phân phối, chẩn đoán, yêu cầu trạng thái và cập nhật cấu hình.
- Liên kết mỗi lệnh với xác nhận và kết quả thực thi cuối cùng của nó.
- Lưu trữ telemetry quan trọng và tổng hợp số liệu lịch sử để báo cáo.
- Cho phép thiết bị tạm thời lưu trữ sự kiện chưa gửi khi mạng không khả dụng.
- Đồng bộ hóa sự kiện đã lưu sau khi kết nối lại mà không tạo bản ghi trùng lặp.
- Giám sát phiên bản firmware và cấu hình thiết bị.
- Từ chối giao tiếp từ các thiết bị chưa đăng ký, đã thu hồi hoặc không hợp lệ.

#### 12. Giám sát Tồn kho và Mức Nước hoa

Hệ thống phải ước tính mức tiêu thụ nước hoa và quản lý hoạt động nạp lại.

- Ghi lại số lượng hoặc trọng lượng ban đầu khi chai hoặc hộp mực được lắp đặt.
- Ước tính số lượng còn lại bằng cách sử dụng số lần xịt thành công và mức tiêu thụ đã hiệu chuẩn mỗi lần xịt.
- So sánh mức tiêu thụ ước tính với số liệu đo từ cảm biến tải trọng hoặc cảm biến mức.
- Cập nhật số lần xịt còn lại ước tính sau mỗi lần xịt khách hàng hoặc chẩn đoán thành công.
- Tạo cảnh báo tồn kho thấp khi lượng còn lại dưới ngưỡng đã cấu hình.
- Đánh dấu khe không khả dụng khi không còn đủ nước hoa cho một lần xịt an toàn khác.
- Phát hiện khả năng rò rỉ hoặc tiêu thụ bất thường khi lượng mất đo được khác biệt đáng kể so với hoạt động phân phối đã ghi nhận.
- Duy trì lịch sử lắp đặt, nạp lại, tháo, điều chỉnh và thanh lý đầy đủ.
- Yêu cầu người dùng được ủy quyền và lý do cho các điều chỉnh tồn kho thủ công.
- Tạo báo cáo tồn kho theo sản phẩm, lô, máy, địa điểm, thương hiệu và khoảng thời gian.

#### 13. Quản lý Cảnh báo và Thông báo

Hệ thống phải tự động phát hiện và quản lý các vấn đề vận hành.

- Tạo cảnh báo cho trạng thái máy offline, tồn kho thấp, khe trống, cửa mở, nghi ngờ rò rỉ, lỗi cảm biến, lỗi bộ truyền động và lỗi phân phối lặp lại.
- Phân loại cảnh báo theo loại, mức độ nghiêm trọng, trạng thái, máy, địa điểm và thời gian xảy ra.
- Tránh tạo quá nhiều cảnh báo trùng lặp cho cùng một vấn đề chưa được giải quyết.
- Thông báo cho người dùng chịu trách nhiệm thông qua thông báo trong hệ thống và các kênh bên ngoài đã cấu hình.
- Cho phép người dùng được ủy quyền xác nhận, gán, giải quyết hoặc mở lại cảnh báo.
- Tự động tạo phiếu bảo trì cho các loại cảnh báo quan trọng đã cấu hình.
- Ghi lại người dùng chịu trách nhiệm, thời gian xác nhận, chi tiết giải quyết và thời gian giải quyết.
- Leo thang các cảnh báo vẫn chưa được giải quyết vượt quá thời gian dịch vụ đã cấu hình.
- Duy trì lịch sử cảnh báo để phân tích vận hành.

#### 14. Quản lý Bảo trì

Hệ thống phải hỗ trợ toàn bộ vòng đời bảo trì máy.

- Tạo phiếu bảo trì thủ công hoặc tự động từ cảnh báo thiết bị.
- Gán phiếu cho kỹ thuật viên dựa trên thương hiệu, địa điểm, máy hoặc trách nhiệm.
- Phân loại phiếu theo danh mục, mức độ nghiêm trọng, ưu tiên, trạng thái và ngày đến hạn.
- Ngăn các máy có phiếu bảo trì quan trọng chấp nhận đơn hàng mới.
- Cung cấp danh sách kiểm tra kiểm tra, sửa chữa, hỗ trợ nạp lại và sau bảo trì.
- Ghi lại kết quả chẩn đoán, hành động khắc phục, linh kiện thay thế, chi phí và bằng chứng hỗ trợ.
- Theo dõi thời gian từ phát hiện sự cố đến xác nhận và giải quyết cuối cùng.
- Yêu cầu kiểm tra sau bảo trì thành công trước khi đưa máy trở lại dịch vụ hoạt động.
- Duy trì lịch sử bảo trì cho mỗi máy và linh kiện.
- Tạo báo cáo về thời gian dừng, hỏng hóc lặp lại, tần suất bảo trì và hiệu suất giải quyết.

#### 15. Bảng điều khiển và Báo cáo

Hệ thống phải cung cấp báo cáo vận hành và kinh doanh theo phạm vi được ủy quyền của người dùng.

- Hiển thị máy theo trạng thái online, offline, bảo trì, bị vô hiệu hóa và lỗi.
- Hiển thị khối lượng giao dịch và doanh thu theo ngày, tuần, tháng và khoảng thời gian tùy chỉnh.
- Báo cáo giao dịch thành công, đang chờ, thất bại, hết hạn và đã hoàn tiền.
- Báo cáo tỷ lệ phân phối thành công và thất bại.
- Xác định các trường hợp thanh toán thành công nhưng phân phối chưa được xác nhận.
- Hiển thị các hương thơm được chọn nhiều nhất theo thương hiệu, máy, địa điểm và khoảng thời gian.
- Hiển thị ước tính tồn kho hiện tại, các khe tồn kho thấp và yêu cầu nạp lại dự kiến.
- Báo cáo thời gian hoạt động, thời gian dừng, tần suất cảnh báo và thời gian giải quyết trung bình của máy.
- Cho phép người dùng lọc báo cáo theo thương hiệu, địa điểm, máy, sản phẩm và khoảng thời gian được ủy quyền.
- Cho phép người dùng được ủy quyền xuất báo cáo ở các định dạng phổ biến như CSV hoặc Excel.
- Giới hạn báo cáo toàn nền tảng chỉ dành cho Quản trị viên Siêu cấp Nền tảng.

#### 16. Kiểm toán và Khả năng Truy xuất nguồn gốc

Hệ thống phải duy trì khả năng truy xuất nguồn gốc cho điều tra bảo mật và vận hành.

- Ghi lại các hành động người dùng quan trọng, sự kiện xác thực, lệnh thiết bị, sự kiện thanh toán, thay đổi tồn kho và cập nhật cấu hình.
- Lưu trữ tác nhân, tenant, hành động, đối tượng đích, dấu thời gian, nguồn và các giá trị trước-sau liên quan.
- Ghi lại tất cả thay đổi về giá sản phẩm, gán khe, quyền người dùng, điều chỉnh tồn kho, hoàn tiền và trạng thái bảo trì.
- Ngăn người dùng thông thường chỉnh sửa hoặc xóa bản ghi kiểm toán.
- Cho phép quản trị viên được ủy quyền tìm kiếm nhật ký kiểm toán theo thời gian, người dùng, máy, hành động, đối tượng và mức độ nghiêm trọng.
- Duy trì khả năng truy xuất nguồn gốc từ đầu đến cuối từ đơn hàng đến thanh toán, lệnh phân phối, kết quả thiết bị, trừ tồn kho, sự cố vận hành và hoàn tiền (nếu có).

#### 17. Quy tắc Kinh doanh

- Mỗi máy thuộc về đúng một tenant thương hiệu nước hoa tại một thời điểm nhất định.
- Mỗi khe máy chỉ có thể chứa một chai hoặc hộp mực nước hoa đang hoạt động tại một thời điểm.
- Chỉ các sản phẩm sẵn có được lắp trong máy online và đang hoạt động mới có thể được khách hàng chọn.
- Sản phẩm và giá của đơn hàng được cố định tại thời điểm tạo đơn hàng.
- Chỉ backend mới có thể xác nhận thanh toán thành công.
- Ảnh chụp màn hình hoặc kết quả hiển thị trên ki-ốt không được coi là bằng chứng thanh toán.
- Một đơn hàng đã thanh toán thành công chỉ được tạo ra không quá một lần xịt thành công.
- Lệnh hết hạn, không hợp lệ, trùng lặp hoặc địa chỉ sai phải bị thiết bị từ chối.
- Máy không được phân phối khi cửa mở, đang bảo trì, khe được chọn trống hoặc có lỗi phần cứng nghiêm trọng đang hoạt động.
- Không chấp nhận đơn hàng mới khi máy không thể giao tiếp với backend.
- Chỉ các hoạt động phân phối đã xác nhận mới làm giảm tồn kho bán hàng cho khách hàng; các lần xịt chẩn đoán phải được ghi nhận riêng.
- Mọi lần nạp lại, điều chỉnh tồn kho, xịt chẩn đoán, thay đổi giá, thay đổi quyền và hoàn tiền phải được ghi vào nhật ký kiểm toán.
- Người dùng thuộc một thương hiệu nước hoa không được truy cập dữ liệu thuộc thương hiệu nước hoa khác.
- Kết quả phân phối không chắc chắn phải yêu cầu xem xét và không được tự động tạo lệnh xịt khác.
- Máy đang bảo trì chỉ được trở lại dịch vụ hoạt động sau khi hoàn thành danh sách kiểm tra bắt buộc và kiểm tra sau bảo trì.

### d) Yêu cầu Phi chức năng

- **Hiệu suất**: Trạng thái thanh toán và telemetry máy phải được cập nhật với độ trễ thấp trong điều kiện mạng bình thường.
- **Khả dụng**: Nền tảng phải duy trì hoạt động trong quá trình sử dụng dự kiến và rõ ràng vô hiệu hóa mua hàng mới khi máy không thể phân phối an toàn.
- **Bảo mật**: Hệ thống phải cung cấp cách ly tenant, xác thực bảo mật, kiểm soát truy cập dựa trên vai trò, giao tiếp TLS, lệnh thiết bị có chữ ký và nhật ký kiểm toán.
- **Độ tin cậy**: Mỗi đơn hàng đã xác nhận chỉ được tạo ra không quá một lần xịt; lệnh, webhook và thử lại phải có tính idempotent và có thể truy xuất.
- **Khả năng mở rộng**: Hệ thống phải hỗ trợ nhiều thương hiệu, địa điểm, máy, khe, người dùng đồng thời và khối lượng telemetry ngày càng tăng.
- **Khả năng sử dụng**: Giao diện ki-ốt và quản lý phải phản hồi nhanh, dễ tiếp cận và cung cấp hướng dẫn rõ ràng về thanh toán, phân phối, nạp lại và lỗi.
- **Khả năng bảo trì và An toàn**: Các module phải có thể kiểm thử và quan sát được; thiết bị phải thực thi các quy tắc an toàn về cửa, tồn kho, hết thời gian và truyền động.

### e) Lý thuyết & Thực tiễn

#### Lý thuyết

- Internet of Things, nhắn tin MQTT, định danh thiết bị và xử lý telemetry
- Kiến trúc Đa Tenant, Kiểm soát Truy cập dựa trên Vai trò và cách ly dữ liệu tenant
- Quy trình giao dịch phân tán, máy trạng thái, tính idempotent và xác minh webhook thanh toán
- Ước tính tồn kho sử dụng bộ đếm phân phối và số liệu đo cảm biến trọng lượng hoặc mức

#### Thực tiễn

- Phát triển phần mềm Agile/Scrum và xác thực yêu cầu với các bên liên quan
- Tích hợp bộ điều khiển nhúng, truyền động đã hiệu chuẩn, cảm biến và cơ chế an toàn thiết bị
- API Backend, MQTT broker, cơ sở dữ liệu quan hệ, xử lý sự kiện và giám sát
- Phát triển cổng quản trị web và ứng dụng ki-ốt màn hình cảm ứng
- Triển khai đám mây, kiểm thử tự động, kiểm thử bảo mật và tích hợp hệ thống đầu-cuối

### f) Sản phẩm (Kết quả mong đợi)

- Nguyên mẫu chức năng ki-ốt nước hoa với ít nhất bốn khe hương thơm được điều khiển độc lập
- Ứng dụng ki-ốt màn hình cảm ứng với chọn hương thơm, thanh toán QR và trạng thái phân phối
- API Backend, xác thực, quản lý thương hiệu đa tenant và tích hợp thanh toán
- Cổng thiết bị IoT cho telemetry, cảnh báo, lệnh bảo mật và cấu hình từ xa
- Module quản lý tồn kho, chai hoặc hộp mực, nạp lại và tồn kho thấp
- Module vận hành máy, phiếu bảo trì, danh sách kiểm tra kỹ thuật viên và lịch sử thiết bị
- Module đối soát giao dịch, bảng điều khiển, báo cáo, thông báo và nhật ký kiểm toán
- Mã nguồn, kết quả kiểm thử, gói triển khai, hướng dẫn người dùng và tài liệu kỹ thuật

### g) Các gói công việc đề xuất

- **Gói công việc 1**: Phân tích hệ thống, kiến trúc đa tenant, cơ sở dữ liệu, xác thực và quản trị thương hiệu.
- **Gói công việc 2**: Nguyên mẫu phần cứng ki-ốt, firmware nhúng, hiệu chuẩn xịt, cảm biến và điều khiển an toàn.
- **Gói công việc 3**: Cổng IoT, giao tiếp MQTT, giám sát máy, lệnh từ xa và hệ thống cảnh báo.
- **Gói công việc 4**: Giao diện ki-ốt khách hàng, danh mục hương thơm, quy trình đơn hàng, thanh toán QR và khôi phục lỗi.
- **Gói công việc 5**: Cổng web, quản lý tồn kho và nạp lại, bảo trì, đối soát, bảng điều khiển và báo cáo.
- **Gói công việc 6**: Tích hợp đầu-cuối, kiểm thử bảo mật và độ tin cậy, đánh giá thí điểm, triển khai và tài liệu.

### 4. Các ý kiến khác

*(Đề xuất tất cả các nội dung liên quan nếu có)*
