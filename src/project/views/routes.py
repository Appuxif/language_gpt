from project.core.views.base import Route
from project.views.dummy import DummyView
from project.views.main import MainView
from project.views.user_groups_views.create_user_group import CreateUserGroupView
from project.views.user_groups_views.delete_user_group import DeleteUserGroupView
from project.views.user_groups_views.user_group import UserGroupView
from project.views.user_groups_views.user_groups import UserGroupsView
from project.views.word_learn_views.learn_words import LearnWordsView
from project.views.word_learn_views.learning_game import LearningGameView
from project.views.words_views.add_word import AddWordView
from project.views.words_views.add_word_translation import AddWordTranslationView
from project.views.words_views.delete_word import DeleteWordView
from project.views.words_views.edit_word import EditWordView
from project.views.words_views.edit_word_translation import EditWordTranslationView
from project.views.words_views.word import WordView

routes = [
    Route(DummyView),
    Route(MainView),
]

routes += [
    Route(UserGroupsView),
    Route(UserGroupView),
    Route(CreateUserGroupView),
    Route(DeleteUserGroupView),
]

routes += [
    Route(WordView),
    Route(AddWordView),
    Route(AddWordTranslationView),
    Route(DeleteWordView),
    Route(EditWordView),
    Route(EditWordTranslationView),
]

routes += [
    Route(LearnWordsView),
    Route(LearningGameView),
]
