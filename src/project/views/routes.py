from project.core.views.base import Route
from project.views.dummy import DummyView
from project.views.main import MainView
from project.views.user_groups_views.create_user_group import CreateUserGroupView
from project.views.user_groups_views.delete_user_group import DeleteUserGroupView
from project.views.user_groups_views.user_group import UserGroupView
from project.views.user_groups_views.user_groups import UserGroupsView

routes = [
    Route(DummyView),
    Route(MainView),
    Route(UserGroupsView),
    Route(UserGroupView),
    Route(CreateUserGroupView),
    Route(DeleteUserGroupView),
]
