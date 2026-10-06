import sys
import logging
import base64
from unittest.mock import patch, MagicMock

logging.basicConfig(level=logging.ERROR)

def run_test():
    try:
        from app import create_app
        import base64
        app = create_app()

        app.config.update({
            "TESTING": True,
            "JWT_SECRET_KEY": "fake_secret_key"
        })

        with app.app_context():
            from app.extensions import db
            from app.models.user import User
            from app.models.habit import Habit, Category
            from app.models.user_habit import UserHabit
            from datetime import date
            import json

            # Need DB purely for relationships required if we don't mock get_user_habit
            # Actually, to bypass DB issues, we can just patch get_user_habit
            
            client = app.test_client()
            
            from flask_jwt_extended import create_access_token
            token = create_access_token(identity="1")
            
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "habit_id": 1,
                "image_base64": base64.b64encode(b"abcd").decode("utf-8"),
                "mime_type": "image/png"
            }
            
            # Use mocking completely
            mock_habit = MagicMock()
            mock_habit.id = 1
            mock_habit.habit.nombre = "Beber Agua"
            mock_habit.habit.xp_base = 10
            
            with patch("app.services.validation_service.get_user_habit", return_value=mock_habit), \
                 patch("app.models.validation_log.ValidationLog.query"), \
                 patch("app.models.checkin.CheckIn.query"), \
                 patch("app.services.xp_service.award_xp"), \
                 patch("app.extensions.db.session.add"), \
                 patch("app.extensions.db.session.commit"), \
                 patch("app.extensions.db.session.rollback"), \
                 patch("app.services.openai_service.analyze_habit_image") as mock_analyze:
                
                # Test Case 1: Unhandled exception in provider
                mock_analyze.side_effect = Exception("OpenAI failed maliciously")
                resp = client.post("/api/habits/validate", json=payload, headers=headers)
                print(f"CASE 1 (Exception in Provider) CODE: {resp.status_code}")
                
            # Test Case 2: Run real code WITHOUT MOCKING db actions, against real db!
            # We already have u, c, h in db from previous tests
            db.create_all()
            if not User.query.get(1):
                u = User(username="test", email="test@test.com")
                c = Category(nombre="cat")
                h = Habit(nombre="Beber Agua", categoria=c, section="general", frequency="daily", habit_type="boolean")
                uh = UserHabit(user=u, habit=h, fecha_inicio=date.today())
                db.session.add_all([u, c, h, uh])
                db.session.commit()
                
            with patch("app.services.openai_service.analyze_habit_image") as mock_analyze2:
                mock_analyze2.return_value = {"valido": True, "razon": "Porque si", "confianza": 0.99}
                resp2 = client.post("/api/habits/validate", json=payload, headers=headers)
                print(f"CASE 2 (Real DB Flow) CODE: {resp2.status_code}")
                if resp2.status_code >= 500:
                    print(f"CASE 2 TRACEBACK (from logs): internal")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
