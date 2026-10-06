import os
import tempfile
import unittest
from datetime import datetime

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models.token_blocklist import TokenBlocklist


class TokenBlocklistTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "token-blocklist.db")
        self.config = type(
            "TokenBlocklistConfig",
            (),
            {
                "SECRET_KEY": "test-secret-key-with-32-characters!!",
                "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars!!",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": True,
                "ENVIRONMENT": "test",
            },
        )

        self.app = create_app(self.config)
        self.runner = self.app.test_cli_runner()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.runner.invoke(args=["db", "upgrade"])

    def tearDown(self) -> None:
        db.session.remove()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def test_token_blocklist_table_exists_after_upgrade(self) -> None:
        inspector = inspect(db.engine)
        self.assertIn("token_blocklist", inspector.get_table_names())

    def test_token_blocklist_columns_match_model(self) -> None:
        inspector = inspect(db.engine)
        columns = {col["name"] for col in inspector.get_columns("token_blocklist")}
        self.assertIn("id", columns)
        self.assertIn("jti", columns)
        self.assertIn("token_type", columns)
        self.assertIn("revoked_at", columns)

    def test_token_blocklist_jti_unique_index_exists(self) -> None:
        inspector = inspect(db.engine)
        indexes = inspector.get_indexes("token_blocklist")
        jti_unique = any(
            idx.get("unique") and "jti" in idx["column_names"]
            for idx in indexes
        )
        self.assertTrue(jti_unique, "jti unique index missing on token_blocklist")

    def test_token_blocklist_insert_and_query(self) -> None:
        entry = TokenBlocklist(
            jti="test-jti-1234-5678-abcd",
            token_type="access",
            revoked_at=datetime.utcnow(),
        )
        db.session.add(entry)
        db.session.commit()

        result = db.session.execute(
            text("SELECT COUNT(*) FROM token_blocklist WHERE jti = :jti"),
            {"jti": "test-jti-1234-5678-abcd"},
        ).scalar()
        self.assertEqual(result, 1)

    def test_token_blocklist_jti_uniqueness_enforced(self) -> None:
        jti = "duplicate-jti-abcd-1234"
        db.session.add(TokenBlocklist(jti=jti, token_type="access", revoked_at=datetime.utcnow()))
        db.session.commit()

        db.session.add(TokenBlocklist(jti=jti, token_type="access", revoked_at=datetime.utcnow()))
        with self.assertRaises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_token_blocklist_query_on_empty_table_does_not_crash(self) -> None:
        result = db.session.execute(text("SELECT * FROM token_blocklist LIMIT 1")).fetchall()
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
