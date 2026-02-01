USE attendance_db;

-- Departments
INSERT INTO departments (dept_name) VALUES
('HR'),
('IT'),
('Sales')
ON DUPLICATE KEY UPDATE dept_name = dept_name;

-- Shifts
INSERT INTO shifts (shift_name, start_time, end_time, break_minutes) VALUES
('Ca sáng', '08:00:00', '12:00:00', 0),
('Ca chiều', '13:00:00', '17:00:00', 0),
('Hành chính', '08:30:00', '17:30:00', 60)
ON DUPLICATE KEY UPDATE shift_name = shift_name;

-- Admin mặc định (password: admin123)
-- password_hash này sẽ được sinh đúng khi chạy scripts/seed_db.py, nên ở đây chỉ tạo placeholder nếu chưa có.
INSERT INTO users (full_name, username, password_hash, role, dept_id, shift_id)
SELECT 'Admin Demo', 'admin', 'CHANGE_ME', 'admin', d.dept_id, s.shift_id
FROM departments d
JOIN shifts s
WHERE d.dept_name='IT' AND s.shift_name='Hành chính'
AND NOT EXISTS (SELECT 1 FROM users WHERE username='admin');
