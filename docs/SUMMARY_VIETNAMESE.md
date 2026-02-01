# Tóm tắt (Vietnamese)

Hệ thống chấm công được tổ chức theo kiến trúc MVC và tuân thủ SOLID:

- **Model (Domain)**: Entity (User, Shift, Department, AttendanceRecord) + Interfaces (Repository Protocol)
- **Repository (Data Access)**: Thực thi truy vấn MySQL, che giấu SQL khỏi Service
- **Service (Business Logic)**: Xử lý đăng nhập, chấm công, quy tắc đi muộn/về sớm
- **Controller (Flask)**: Nhận request/response, gọi Service, render template

Mục tiêu: code rõ ràng, dễ test, dễ mở rộng.
