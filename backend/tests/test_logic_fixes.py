"""隔离回归测试：在 backend 目录执行 python -m unittest discover -s tests -v。"""

import os
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

# 先覆盖配置，再导入应用模块；测试不会连接项目 .env 中的数据库。
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "isolated-regression-test-key-at-least-32-bytes"

import jwt
from pydantic import ValidationError
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.common.exceptions import BusinessException
from app.config import settings
from app.database import Base
from app.migrations.add_username_unique import upgrade
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.lab import LabCreateRequest, LabUpdateRequest
from app.schemas.reservation import ReservationCreateRequest
from app.schemas.user import UserCreateRequest
from app.services import auth_service, reservation_service, user_service
from app.utils import jwt as jwt_utils


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        database_path = Path(self.directory.name) / "regression.sqlite"
        self.engine = create_engine(
            f"sqlite:///{database_path.as_posix()}",
            connect_args={"timeout": 15, "check_same_thread": False},
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        with self.sessions() as db:
            db.add_all(
                [
                    User(id=1, username="admin", password="hash", name="Admin", role="admin"),
                    User(id=2, username="student", password="hash", name="Student", role="student"),
                    User(id=3, username="other", password="hash", name="Other", role="student"),
                    Lab(id=1, name="Lab A", capacity=20),
                    Lab(id=2, name="Lab B", capacity=30),
                ]
            )
            db.commit()
            db.add_all(
                [
                    Equipment(id=1, lab_id=1, name="Equipment A"),
                    Equipment(id=2, lab_id=2, name="Equipment B"),
                    Equipment(id=3, lab_id=1, name="Equipment C"),
                ]
            )
            db.commit()

    def tearDown(self):
        self.engine.dispose()
        self.directory.cleanup()

    def request(self, **changes):
        payload = dict(lab_id=1, date="2099-10-20", start_time="09:00", end_time="10:00")
        payload.update(changes)
        return ReservationCreateRequest(**payload)

    def reserve(self, **changes):
        with self.sessions() as db:
            reservation_service.create_reservation(db, db.get(User, 2), self.request(**changes))

    def test_concurrent_identical_and_overlapping_reservations(self):
        for equipment_id in (None, 1):
            for second_start in ("09:00", "09:30"):
                with self.subTest(equipment_id=equipment_id, second_start=second_start):
                    with self.sessions() as db:
                        db.query(Reservation).delete()
                        db.commit()
                    start = threading.Barrier(2)

                    def widen_conflict_window(conn, cursor, statement, parameters, context, many):
                        if statement.lstrip().upper().startswith("SELECT") and "FROM reservation" in statement:
                            # 放大原先先查后写的窗口，覆盖两个请求均无冲突的竞态。
                            time.sleep(0.1)

                    def submit(start_time):
                        with self.sessions() as db:
                            user = db.get(User, 2)  # 模拟认证先读取用户、开启会话事务。
                            start.wait(timeout=5)
                            try:
                                reservation_service.create_reservation(
                                    db, user, self.request(equipment_id=equipment_id, start_time=start_time)
                                )
                                return 200
                            except BusinessException as exc:
                                self.assertFalse(db.in_transaction())
                                return exc.code

                    event.listen(self.engine, "after_cursor_execute", widen_conflict_window)
                    try:
                        with ThreadPoolExecutor(max_workers=2) as pool:
                            results = list(pool.map(submit, ("09:00", second_start)))
                    finally:
                        event.remove(self.engine, "after_cursor_execute", widen_conflict_window)
                    self.assertEqual(sorted(results), [200, 409])
                    with self.sessions() as db:
                        self.assertEqual(db.query(Reservation).count(), 1)

    def test_adjacent_times_and_independent_resources_remain_available(self):
        self.reserve()
        self.reserve(start_time="10:00", end_time="11:00")
        self.reserve(lab_id=2)
        self.reserve(equipment_id=1)
        self.reserve(equipment_id=3)
        self.reserve(date="2099-10-21")
        with self.sessions() as db:
            self.assertEqual(db.query(Reservation).count(), 6)

    def test_rejected_and_cancelled_reservations_do_not_block(self):
        for status in (2, 3):
            with self.subTest(status=status):
                with self.sessions() as db:
                    db.query(Reservation).delete()
                    db.add(Reservation(user_id=2, lab_id=1, date="2099-10-20", start_time="09:00", end_time="10:00", status=status))
                    db.commit()
                self.reserve()

    def test_pending_and_approved_reservations_block(self):
        for status in (0, 1):
            with self.subTest(status=status):
                with self.sessions() as db:
                    db.query(Reservation).delete()
                    db.add(Reservation(user_id=2, lab_id=1, date="2099-10-20", start_time="09:00", end_time="10:00", status=status))
                    db.commit()
                with self.assertRaises(BusinessException) as error:
                    self.reserve()
                self.assertEqual(error.exception.code, 409)

    def test_equipment_must_belong_to_lab_and_failed_request_releases_lock(self):
        with self.sessions() as db:
            with self.assertRaises(BusinessException) as error:
                reservation_service.create_reservation(db, db.get(User, 2), self.request(equipment_id=2))
            self.assertEqual(error.exception.code, 400)
            self.assertFalse(db.in_transaction())
            self.assertEqual(db.query(Reservation).count(), 0)
        self.reserve(equipment_id=1)

    def test_equipment_conflicts_are_identified_by_equipment(self):
        with self.sessions() as db:
            # 覆盖历史记录中 lab_id 与设备当前归属不同的情况。
            db.add(Reservation(user_id=2, lab_id=2, equipment_id=1, date="2099-10-20", start_time="09:00", end_time="10:00", status=1))
            db.commit()
        with self.assertRaises(BusinessException) as error:
            self.reserve(equipment_id=1)
        self.assertEqual(error.exception.code, 409)

    def test_reservation_does_not_change_lab_update_time(self):
        with self.sessions() as db:
            original = db.get(Lab, 1).update_time
        self.reserve()
        with self.sessions() as db:
            self.assertEqual(db.get(Lab, 1).update_time, original)

    def test_failed_commit_rolls_back_reservation_and_releases_lock(self):
        with self.sessions() as db:
            with patch.object(db, "commit", side_effect=RuntimeError("commit failed")):
                with self.assertRaisesRegex(RuntimeError, "commit failed"):
                    reservation_service.create_reservation(db, db.get(User, 2), self.request())
            self.assertFalse(db.in_transaction())
        self.reserve()

    def test_mysql_deadlock_retries_whole_transaction(self):
        original = reservation_service._create_reservation
        attempts = []

        def deadlock_then_succeed(db, user, data):
            attempts.append(1)
            if len(attempts) == 1:
                db.execute(text("SELECT 1"))
                raise OperationalError("UPDATE labs", {}, Exception(1213, "Deadlock"))
            return original(db, user, data)

        with patch.object(reservation_service, "_create_reservation", side_effect=deadlock_then_succeed):
            self.reserve()
        self.assertEqual(len(attempts), 2)
        with self.sessions() as db:
            self.assertEqual(db.query(Reservation).count(), 1)

    def test_mysql_busy_resource_returns_conflict_after_rollback(self):
        for error_code, expected_attempts in ((1205, 1), (1213, 3)):
            with self.subTest(error_code=error_code):
                error = OperationalError("UPDATE labs", {}, Exception(error_code, "Busy"))
                with self.sessions() as db:
                    user = db.get(User, 2)
                    with patch.object(reservation_service, "_create_reservation", side_effect=error) as submit:
                        with self.assertRaises(BusinessException) as caught:
                            reservation_service.create_reservation(db, user, self.request())
                    self.assertEqual(caught.exception.code, 409)
                    self.assertEqual(submit.call_count, expected_attempts)
                    self.assertFalse(db.in_transaction())
                    self.assertEqual(db.query(Reservation).count(), 0)

    def test_concurrent_account_creation_uses_database_unique_constraint(self):
        for modes in (("register", "register"), ("create", "create"), ("register", "create")):
            with self.subTest(modes=modes):
                username = "race_" + "_".join(modes)
                checked = threading.Barrier(2)

                def hash_after_precheck(_):
                    # 强制两次用户名存在性预检查都先通过，再进入写入阶段。
                    checked.wait(timeout=5)
                    return "hashed-test-password"

                def submit(mode):
                    with self.sessions() as db:
                        try:
                            if mode == "register":
                                auth_service.register(db, RegisterRequest(username=username, password="test"))
                            else:
                                user_service.create_user(db, UserCreateRequest(username=username, password="test", name="Test"))
                            result = 200
                        except BusinessException as exc:
                            self.assertEqual(exc.message, "账号已存在")
                            result = exc.code
                        # 唯一约束失败后，Session 仍应可正常使用。
                        self.assertEqual(db.execute(text("SELECT 1")).scalar_one(), 1)
                        return result

                with patch.object(auth_service, "hash_password", side_effect=hash_after_precheck), patch.object(user_service, "hash_password", side_effect=hash_after_precheck):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        results = list(pool.map(submit, modes))
                self.assertEqual(sorted(results), [200, 409])
                with self.sessions() as db:
                    self.assertEqual(db.query(User).filter(User.username == username).count(), 1)

    def test_deleting_user_with_any_reservation_history_is_a_conflict(self):
        for status in (0, 1, 2, 3):
            with self.subTest(status=status):
                with self.sessions() as db:
                    db.query(Reservation).delete()
                    db.add(Reservation(user_id=2, lab_id=1, date="2000-01-01", start_time="09:00", end_time="10:00", status=status))
                    db.commit()
                    with self.assertRaises(BusinessException) as error:
                        user_service.delete_user(db, 2, db.get(User, 1))
                    self.assertEqual(error.exception.code, 409)
                    self.assertIsNotNone(db.get(User, 2))
                    self.assertEqual(db.query(Reservation).count(), 1)

    def test_user_delete_handles_reservation_inserted_after_precheck(self):
        with self.sessions() as db:
            original_delete = db.delete

            def insert_then_delete(user):
                with self.sessions() as other:
                    other.add(Reservation(user_id=2, lab_id=1, date="2099-10-20", start_time="09:00", end_time="10:00"))
                    other.commit()
                original_delete(user)

            with patch.object(db, "delete", side_effect=insert_then_delete):
                with self.assertRaises(BusinessException) as error:
                    user_service.delete_user(db, 2, db.get(User, 1))
            self.assertEqual(error.exception.code, 409)
            self.assertFalse(db.in_transaction())
            self.assertIsNotNone(db.get(User, 2))
            self.assertEqual(db.query(Reservation).count(), 1)

    def test_user_without_reservations_can_be_deleted(self):
        with self.sessions() as db:
            user_service.delete_user(db, 3, db.get(User, 1))
            self.assertIsNone(db.get(User, 3))


class MigrationTests(unittest.TestCase):
    def test_upgrade_adds_unique_index_and_is_idempotent(self):
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL)"))
                connection.execute(text("INSERT INTO users (username) VALUES ('existing')"))
                self.assertTrue(upgrade(connection))
                self.assertFalse(upgrade(connection))
                with self.assertRaises(IntegrityError):
                    connection.execute(text("INSERT INTO users (username) VALUES ('existing')"))
        finally:
            engine.dispose()

    def test_upgrade_refuses_duplicate_accounts_without_modifying_data(self):
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL)"))
                connection.execute(text("INSERT INTO users (username) VALUES ('duplicate'), ('duplicate')"))
                with self.assertRaisesRegex(RuntimeError, "重复账号"):
                    upgrade(connection)
                self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one(), 2)
                self.assertEqual(inspect(connection).get_indexes("users"), [])
        finally:
            engine.dispose()


class ValidationAndTokenTests(unittest.TestCase):
    def test_capacity_requires_positive_integer_for_create_and_update(self):
        for model in (LabCreateRequest, LabUpdateRequest):
            self.assertEqual(model(name="Lab", capacity=30).capacity, 30)
            for invalid in (0, -1, 1.5, "invalid"):
                with self.subTest(model=model.__name__, capacity=invalid):
                    with self.assertRaises(ValidationError):
                        model(name="Lab", capacity=invalid)
        with self.assertRaises(ValidationError):
            LabCreateRequest(name="Lab")
        self.assertIsNone(LabUpdateRequest(name="Lab").capacity)

    def test_jwt_lifetime_matches_configuration_across_local_timezones(self):
        fixed_utc = datetime(2040, 10, 20, 1, 0, tzinfo=timezone.utc)
        for offset in (-7, 0, 8):
            with self.subTest(offset=offset):
                local_zone = timezone(timedelta(hours=offset))

                class Clock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        if tz is None:
                            return fixed_utc.astimezone(local_zone).replace(tzinfo=None)
                        return fixed_utc.astimezone(tz)

                with patch.object(jwt_utils, "datetime", Clock):
                    token = jwt_utils.create_access_token(2)
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_exp": False})
                self.assertEqual(payload["user_id"], 2)
                self.assertEqual(payload["exp"] - fixed_utc.timestamp(), settings.JWT_EXPIRE_HOURS * 3600)

    def test_real_token_lifetime_and_decode(self):
        before = time.time()
        token = jwt_utils.create_access_token(2)
        after = time.time()
        payload = jwt_utils.decode_access_token(token)
        expected = settings.JWT_EXPIRE_HOURS * 3600
        self.assertGreaterEqual(payload["exp"] - before, expected - 1)
        self.assertLessEqual(payload["exp"] - after, expected)


if __name__ == "__main__":
    unittest.main()
