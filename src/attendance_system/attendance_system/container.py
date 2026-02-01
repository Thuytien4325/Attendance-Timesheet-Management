from __future__ import annotations

from dataclasses import dataclass

from .attendance.factory import AttendanceStrategyFactory
from .attendance.mysql_attendance_repository import MySQLAttendanceRepository
from .attendance.service import AttendanceService
from .database.connection import DBConfig, DatabaseConnection
from .payroll.service import PayrollReportService
from .schedules.mysql_schedule_repository import MySQLScheduleRepository
from .schedules.service import ScheduleService
from .shifts.mysql_shift_repository import MySQLShiftRepository
from .requests.mysql_request_repository import MySQLRequestRepository
from .requests.service import RequestService
from .users.mysql_department_repository import MySQLDepartmentRepository
from .users.mysql_user_repository import MySQLUserRepository
from .users.service import AuthService, UserService


@dataclass(frozen=True)
class Container:
    conn: DatabaseConnection

    users_repo: MySQLUserRepository
    departments_repo: MySQLDepartmentRepository
    shifts_repo: MySQLShiftRepository
    attendance_repo: MySQLAttendanceRepository
    schedules_repo: MySQLScheduleRepository
    requests_repo: MySQLRequestRepository

    auth_service: AuthService
    user_service: UserService
    attendance_service: AttendanceService
    payroll_report_service: PayrollReportService
    schedule_service: ScheduleService
    request_service: RequestService


def build_container(*, db_config: dict) -> Container:
    config = DBConfig(
        host=str(db_config["host"]),
        port=int(db_config.get("port", 3306)),
        user=str(db_config["user"]),
        password=str(db_config["password"]),
        database=str(db_config["database"]),
    )
    conn = DatabaseConnection.get_instance(config)

    users_repo = MySQLUserRepository(conn)
    departments_repo = MySQLDepartmentRepository(conn)
    shifts_repo = MySQLShiftRepository(conn)
    attendance_repo = MySQLAttendanceRepository(conn)
    schedules_repo = MySQLScheduleRepository(conn)
    requests_repo = MySQLRequestRepository(conn)

    auth_service = AuthService(users_repo, shifts_repo, schedules_repo)
    user_service = UserService(users_repo)
    attendance_service = AttendanceService(
        attendance_repo,
        users_repo,
        shifts_repo,
        schedules_repo,
        strategy_factory=AttendanceStrategyFactory(),
        grace_minutes=5,
    )
    payroll_report_service = PayrollReportService(attendance_repo)
    schedule_service = ScheduleService(schedules_repo)
    request_service = RequestService(requests_repo, attendance_repo, schedules_repo)

    return Container(
        conn=conn,
        users_repo=users_repo,
        departments_repo=departments_repo,
        shifts_repo=shifts_repo,
        attendance_repo=attendance_repo,
        schedules_repo=schedules_repo,
        requests_repo=requests_repo,
        auth_service=auth_service,
        user_service=user_service,
        attendance_service=attendance_service,
        payroll_report_service=payroll_report_service,
        schedule_service=schedule_service,
        request_service=request_service,
    )
