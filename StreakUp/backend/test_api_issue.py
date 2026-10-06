from app import create_app
from app.models.user import User
from flask_jwt_extended import create_access_token

def run_test():
    app = create_app()
    with app.app_context():
        client = app.test_client()
        user = User.query.first()
        token = create_access_token(identity=str(user.id))
        
        # Try to assign a custom frequency 
        res = client.post("/api/habits", json={
            "habito_id": 1,
            "frequency": "custom",
            "schedule_days": [1, 3, 5]
        }, headers={"Authorization": f"Bearer {token}"})
        
        print("STATUS:", res.status_code)
        print("DATA:", res.get_data(as_text=True))

if __name__ == "__main__":
    run_test()
