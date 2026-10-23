import pytest
from pydantic import ValidationError

from app.core.exceptions import BadRequestError
from app.schemas.feedback import FeedbackCreate
from app.services import feedback_service


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_schema_rejects_out_of_range_rating(rating):
    with pytest.raises(ValidationError):
        FeedbackCreate(category_id=1, rating=rating, description="bad rating")


@pytest.mark.parametrize("rating", [1, 3, 5])
def test_valid_ratings(rating):
    assert feedback_service.validate_rating(rating) == rating


@pytest.mark.parametrize("rating", [0, 6, True])
def test_service_rejects_invalid_rating(rating):
    with pytest.raises(BadRequestError):
        feedback_service.validate_rating(rating)
