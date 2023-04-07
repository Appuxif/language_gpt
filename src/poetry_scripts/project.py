from project.main import run_loop

try:
    from IPython import start_ipython as _run_project_shell
except ImportError:
    from code import interact as _run_project_shell


run_project_shell = _run_project_shell
run_project_dev = run_loop
