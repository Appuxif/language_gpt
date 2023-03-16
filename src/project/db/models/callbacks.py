from enum import Enum, unique

from pydantic import BaseModel, Field

from project.db.models.base import Model, ModelConfig, ModelManager, PyObjectId


@unique
class CallbackDataType(str, Enum):
    """Call Data Type"""

    DUMMY = 'DUMMY'
    CREATE_GROUP = 'create_group'
    LIST_GROUPS = 'list_groups'
    OPTIONS = 'options'
    GROUP = 'group'
    ADD_WORD = 'add_word'
    DELETE_WORD = 'delete_word'
    WORD = 'word'
    DELETE_GROUP = 'delete_group'
    YES = 'yes'
    PAGE = 'page'
    GROUPS_PAGE = 'groups_page'
    WORDS_MENU = 'words_menu'
    GAME = 'game'


class CallbackDataDummy(ModelConfig, BaseModel):
    """Callback Data Dummy"""

    type: CallbackDataType = Field(default=CallbackDataType.DUMMY, const=True)


class WithGroupId(ModelConfig, BaseModel):
    """With Group Id"""

    group_id: PyObjectId = Field(default_factory=PyObjectId)


class CallbackDataGroup(WithGroupId):
    """Callback Data Group"""

    type: CallbackDataType = Field(default=CallbackDataType.GROUP, const=True)


class CallbackDataAddWord(WithGroupId):
    """Callback Data Add Word"""

    type: CallbackDataType = Field(default=CallbackDataType.ADD_WORD, const=True)


class CallbackDataDelWord(WithGroupId):
    """Callback Data Del Word"""

    type: CallbackDataType = Field(default=CallbackDataType.DELETE_WORD, const=True)


class CallbackDataWord(WithGroupId):
    """Callback Data Word"""

    type: CallbackDataType = Field(default=CallbackDataType.WORD, const=True)
    word_id: PyObjectId = Field(default_factory=PyObjectId)


class CallbackDataDelGroup(WithGroupId):
    """Callback Data Del Group"""

    type: CallbackDataType = Field(default=CallbackDataType.DELETE_GROUP, const=True)


class CallbackDataYes(WithGroupId):
    """Callback Data Yes"""

    type: CallbackDataType = Field(default=CallbackDataType.YES, const=True)


class CallbackDataPage(WithGroupId):
    """Callback Data Page"""

    type: CallbackDataType = Field(default=CallbackDataType.PAGE, const=True)
    page_num: int = 0


class CallbackDataGroupsPage(ModelConfig, BaseModel):
    """Callback Data Groups Page"""

    type: CallbackDataType = Field(default=CallbackDataType.GROUPS_PAGE, const=True)
    page_num: int = 0


class CallbackDataWordsMenu(WithGroupId):
    """Callback Data Words Menu"""

    class Action(str, Enum):
        """Action"""

        NOT_SET = 'not_set'
        SELECT_ALL = 'select_all'
        DESELECT_ALL = 'deselect_all'
        PAGE = 'page'
        LEARN = 'learn'

    type: CallbackDataType = Field(default=CallbackDataType.WORDS_MENU, const=True)
    action: str = Action.NOT_SET
    page_num: int = 0
    word_id: PyObjectId | None = Field(None)


class CallbackDataGame(WithGroupId):
    """Callback Data Game"""

    type: CallbackDataType = Field(default=CallbackDataType.GAME, const=True)
    word_id: PyObjectId = Field(default_factory=PyObjectId)
    word2_id: PyObjectId | None = Field(None)


CallbackData = (
    CallbackDataDummy
    | CallbackDataGroup
    | CallbackDataAddWord
    | CallbackDataDelWord
    | CallbackDataWord
    | CallbackDataDelGroup
    | CallbackDataYes
    | CallbackDataPage
    | CallbackDataGroupsPage
    | CallbackDataWordsMenu
    | CallbackDataGame
)


class CallbackModel(Model):
    """Callback Model"""

    data: CallbackData = Field(default_factory=CallbackDataGroup)

    @classmethod
    async def get_button_callback(cls, data: CallbackData) -> str:
        callback = cls(data=data)
        await callback.insert()
        return str(callback.id)


class CallbackModelManager(ModelManager[CallbackModel]):
    """Callback Model Manager"""

    collection = 'callbacks'
    model = CallbackModel
