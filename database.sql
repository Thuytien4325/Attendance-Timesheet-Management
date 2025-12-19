CREATE DATABASE IF NOT EXISTS attendance_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE attendance_db;
 CREATE TABLE departments (
    dept_id INT AUTO_INCREMENT PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL
);
INSERT INTO departments (dept_name) VALUES
('IT'),
('Nhân sự'),
('Kế toán');
CREATE TABLE shifts (
    shift_id INT AUTO_INCREMENT PRIMARY KEY,
    shift_name VARCHAR(100),
    start_time TIME,
    end_time TIME
);
INSERT INTO shifts (shift_name, start_time, end_time) VALUES
('Ca sáng', '08:00:00', '12:00:00'),
('Ca chiều', '13:00:00', '17:00:00'),
('Ca hành chính', '08:00:00', '17:00:00');
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role ENUM('admin', 'staff') DEFAULT 'staff',
    dept_id INT,
    shift_id INT,

    FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
    FOREIGN KEY (shift_id) REFERENCES shifts(shift_id)
);
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    check_in_time DATETIME,
    check_out_time DATETIME,
    status VARCHAR(50),

    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
INSERT INTO users (username, password, full_name, role, dept_id, shift_id)
VALUES ('admin', '123', 'Admin Demo', 'admin', 1, 3);

-- Thêm dữ liệu điểm danh mẫu để kiểm tra tính năng Export
INSERT INTO attendance (user_id, check_in_time, check_out_time, status) VALUES 
(1, '2023-10-27 08:00:00', '2023-10-27 17:00:00', 'Đúng giờ'),
(1, '2023-10-28 08:05:00', '2023-10-28 17:10:00', 'Đi muộn/Về sớm');