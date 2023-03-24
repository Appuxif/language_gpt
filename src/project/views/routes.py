from project.core.views.base import Route
from project.views.dummy import DummyView
from project.views.main import MainView

routes = [Route(DummyView), Route(MainView)]
