from pydantic import Field
from telebot_models.models import Model, PyObjectId


class WithUser(Model):
    """With User Mixin"""

    user_id: PyObjectId = Field(default_factory=PyObjectId)
