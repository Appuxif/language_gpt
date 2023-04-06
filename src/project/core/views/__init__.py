from project.core.views.base import Route, RouteResolver
from project.core.views.dummy import DummyView

RouteResolver.register_route(Route(DummyView))
