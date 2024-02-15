from telebot_views.base import Route

from project.views.check_sub import CheckSubView
from project.views.main import MainView
from project.views.public_groups_views.copy_public_group import CopyPublicGroupView
from project.views.public_groups_views.public_group import PublicGroupView
from project.views.public_groups_views.public_groups import PublicGroupsView
from project.views.public_groups_views.public_word import PublicWordView
from project.views.user_groups_views.create_user_group import CreateUserGroupView
from project.views.user_groups_views.delete_user_group import DeleteUserGroupView
from project.views.user_groups_views.publish_user_group import PublishUserGroupView
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

# main
routes = [
    Route(CheckSubView),
    Route(MainView),
]

# user groups
routes += [
    Route(UserGroupsView),
    Route(UserGroupView),
    Route(CreateUserGroupView),
    Route(DeleteUserGroupView),
    Route(PublishUserGroupView),
]

# words
routes += [
    Route(WordView),
    Route(AddWordView),
    Route(AddWordTranslationView),
    Route(DeleteWordView),
    Route(EditWordView),
    Route(EditWordTranslationView),
]

# learning
routes += [
    Route(LearnWordsView),
    Route(LearningGameView),
]

# public
routes += [
    Route(CopyPublicGroupView),
    Route(PublicGroupView),
    Route(PublicGroupsView),
    Route(PublicWordView),
]
