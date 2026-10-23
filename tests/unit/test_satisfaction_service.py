from app.core.constants import Role
from app.models import Category, Customer, Feedback
from app.services import satisfaction_service


def test_build_summary_formulas():
    s = satisfaction_service.build_summary(total=10, avg=3.456, positive=6, negative=2)
    assert s["average_rating"] == 3.46
    assert s["neutral_count"] == 2
    assert s["satisfaction_percentage"] == 60.0


def test_empty_summary():
    s = satisfaction_service.build_summary(0, None, 0, 0)
    assert s["average_rating"] is None and s["satisfaction_percentage"] == 0.0


def test_summary_from_database(db, make_user):
    user = make_user(Role.CUSTOMER)
    customer = db.query(Customer).filter_by(user_id=user.id).one()
    category = db.query(Category).first()
    for i, rating in enumerate([5, 4, 3, 2, 1, 5]):
        db.add(Feedback(customer_id=customer.id, category_id=category.id, rating=rating, description=f"fb {i}"))
    db.commit()
    s = satisfaction_service.summary(db)
    assert s["total_feedback"] == 6
    assert s["positive_count"] == 3 and s["neutral_count"] == 1 and s["negative_count"] == 2
    assert s["average_rating"] == 3.33
    assert s["satisfaction_percentage"] == 50.0
    cats = satisfaction_service.by_category(db)
    assert cats[0]["category_name"] == category.name and cats[0]["total_feedback"] == 6
    assert satisfaction_service.trends(db)[0]["total_feedback"] == 6
