-- Schema chuẩn hoá cho hệ thống chấm công
-- Target: MySQL 8+

CREATE DATABASE IF NOT EXISTS attendance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE attendance_db;

-- ====== MASTER DATA ======
CREATE TABLE IF NOT EXISTS departments (
    dept_id INT AUTO_INCREMENT PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_departments_name (dept_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS shifts (
    shift_id INT AUTO_INCREMENT PRIMARY KEY,
    shift_name VARCHAR(100) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    break_minutes INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_shifts_name (shift_name)
) ENGINE=InnoDB;

-- ====== USERS ======
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'staff') NOT NULL DEFAULT 'staff',
    dept_id INT NULL,
    shift_id INT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_users_username (username),
    KEY idx_users_dept (dept_id),
    KEY idx_users_shift (shift_id),

    CONSTRAINT fk_users_dept FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_users_shift FOREIGN KEY (shift_id) REFERENCES shifts(shift_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- Backward-compatible migration (older schema had role='user')
UPDATE users SET role='staff' WHERE role='user';
ALTER TABLE users MODIFY role ENUM('admin', 'staff') NOT NULL DEFAULT 'staff';

-- ====== SCHEDULES (PER-DAY SHIFT ASSIGNMENT) ======
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    work_date DATE NOT NULL,
    shift_id INT NOT NULL,
    note VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_schedules_user_date (user_id, work_date),
    KEY idx_schedules_date (work_date),
    KEY idx_schedules_shift (shift_id),

    CONSTRAINT fk_schedules_user FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_schedules_shift FOREIGN KEY (shift_id) REFERENCES shifts(shift_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS timesheet_adjustment_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    work_date DATE NOT NULL,
    requested_check_in TIME NULL,
    requested_check_out TIME NULL,
    requested_note VARCHAR(255) NULL,
    status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_by INT NULL,
    decided_at DATETIME NULL,
    admin_note VARCHAR(255) NULL,
    CONSTRAINT fk_adj_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_adj_decider FOREIGN KEY (decided_by) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_adj_user_date (user_id, work_date),
    INDEX idx_adj_status_created (status, created_at)
);

CREATE TABLE IF NOT EXISTS leave_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason VARCHAR(255) NOT NULL,
    status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_by INT NULL,
    decided_at DATETIME NULL,
    admin_note VARCHAR(255) NULL,
    CONSTRAINT fk_leave_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_leave_decider FOREIGN KEY (decided_by) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_leave_user_dates (user_id, start_date, end_date),
    INDEX idx_leave_status_created (status, created_at)
);

-- ====== SCHEDULE CHANGE REQUESTS (STAFF -> ADMIN APPROVAL) ======
-- Staff chỉ được đề xuất lịch làm (không chỉnh trực tiếp bảng schedules).
-- Admin duyệt sẽ áp dụng vào schedules (upsert theo user_id + work_date).
CREATE TABLE IF NOT EXISTS schedule_change_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    work_date DATE NOT NULL,
    requested_shift_id INT NOT NULL,
    requested_note VARCHAR(255) NOT NULL,
    status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_by INT NULL,
    decided_at DATETIME NULL,
    admin_note VARCHAR(255) NULL,

    CONSTRAINT fk_schreq_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_schreq_shift FOREIGN KEY (requested_shift_id) REFERENCES shifts(shift_id) ON DELETE RESTRICT,
    CONSTRAINT fk_schreq_decider FOREIGN KEY (decided_by) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_schreq_user_date (user_id, work_date),
    INDEX idx_schreq_status_created (status, created_at)
);
-- ====== ATTENDANCE ======
CREATE TABLE IF NOT EXISTS attendance_records (
    attendance_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,

    -- work_date giúp truy vấn theo ngày nhanh hơn và tránh lệ thuộc giờ
    work_date DATE NOT NULL,
    check_in_time DATETIME NOT NULL,
    check_out_time DATETIME NULL,

    status ENUM('ON_TIME', 'LATE', 'EARLY_LEAVE', 'ABSENT', 'UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
    note VARCHAR(255) NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_attendance_user_date (user_id, work_date),
    KEY idx_attendance_check_in (check_in_time),

    CONSTRAINT fk_attendance_user FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE CASCADE,

    -- Một nhân viên chỉ có 1 record/ngày 
    UNIQUE KEY uq_attendance_user_date (user_id, work_date)
) ENGINE=InnoDB;
