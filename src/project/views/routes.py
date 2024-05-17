from telebot_views.base import Route
from telebot_views.views.links_view import LinksView

from project.views.admin.main import MainAdminView
from project.views.admin.user import UserDetailAdminView
from project.views.admin.users import UsersAdminView
from project.views.check_sub import CheckSubView
from project.views.main import MainView
from project.views.public_groups.copy_public_group import CopyPublicGroupView
from project.views.public_groups.public_group import PublicGroupView
from project.views.public_groups.public_groups import PublicGroupsView
from project.views.public_groups.public_word import PublicWordView
from project.views.user_groups.create_user_group import CreateUserGroupView
from project.views.user_groups.delete_user_group import DeleteUserGroupView
from project.views.user_groups.publish_user_group import PublishUserGroupView
from project.views.user_groups.user_group import UserGroupView
from project.views.user_groups.user_groups import UserGroupsView
from project.views.word_learn.learn_words import LearnWordsView
from project.views.word_learn.learning_game import LearningGameView
from project.views.words.add_word import AddWordView
from project.views.words.add_word_translation import AddWordTranslationView
from project.views.words.delete_word import DeleteWordView
from project.views.words.edit_word import EditWordView
from project.views.words.edit_word_translation import EditWordTranslationView
from project.views.words.word import WordView

# main
routes = [
    Route(CheckSubView),
    Route(MainView),
    Route(LinksView),
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

# Admin
routes += [
    Route(MainAdminView),
    Route(UsersAdminView),
    Route(UserDetailAdminView),
]
