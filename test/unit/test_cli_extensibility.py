from types import SimpleNamespace

import pytest

from metaflow import decorators
from metaflow import cli as cli_mod
from metaflow._vendor import click
from metaflow._vendor.click.testing import CliRunner
from metaflow.cli_components import run_cmds
from metaflow.exception import CommandException, MetaflowInternalError
from metaflow.parameters import current_flow
from metaflow.util import dict_to_cli_args


def test_dict_to_cli_args_supports_config_and_tuple_values():
    params = {
        "decospecs": ["retry"],
        "config": {"prod": {}},
        "option_name": "value",
        "multi": [("a", "b"), "c"],
        "flag": True,
        "disabled": False,
    }

    args = list(dict_to_cli_args(params))
    assert args == [
        "--with",
        "retry",
        "--config-value",
        "prod",
        "kv.prod",
        "--option-name",
        "value",
        "--multi",
        "a",
        "b",
        "--multi",
        "c",
        "--flag",
    ]


def test_add_run_decorator_options_adds_options(monkeypatch):
    class DummyFlowDecorator:
        name = "dummy"
        run_options = {
            "priority": {
                "default": "normal",
                "show_default": True,
                "help": "Task priority",
            }
        }

    monkeypatch.setattr(current_flow, "flow_cls", object(), raising=False)
    monkeypatch.setattr(
        decorators, "flow_decorators", lambda flow_cls: [DummyFlowDecorator()]
    )

    def command_fn():
        return None

    command_fn = decorators.add_run_decorator_options(command_fn)
    params = getattr(command_fn, "__click_params__", [])
    priority = next((p for p in params if p.name == "priority"), None)

    assert priority is not None
    assert priority.envvar == "METAFLOW_RUN_PRIORITY"


def test_add_run_decorator_options_normalizes_option_name(monkeypatch):
    class DummyFlowDecorator:
        name = "dummy"
        run_options = {
            "--demo-priority": {
                "default": "normal",
                "show_default": True,
                "help": "Task priority",
            }
        }

    monkeypatch.setattr(current_flow, "flow_cls", object(), raising=False)
    monkeypatch.setattr(
        decorators, "flow_decorators", lambda flow_cls: [DummyFlowDecorator()]
    )

    def command_fn():
        return None

    command_fn = decorators.add_run_decorator_options(command_fn)
    params = getattr(command_fn, "__click_params__", [])
    demo_priority = next((p for p in params if p.name == "demo_priority"), None)

    assert demo_priority is not None
    assert demo_priority.opts == ["--demo-priority"]
    assert demo_priority.envvar == "METAFLOW_RUN_DEMO_PRIORITY"


def test_add_run_decorator_options_rejects_empty_option_name(monkeypatch):
    class DummyFlowDecorator:
        name = "dummy"
        run_options = {"--": {"is_flag": True}}

    monkeypatch.setattr(current_flow, "flow_cls", object(), raising=False)
    monkeypatch.setattr(
        decorators, "flow_decorators", lambda flow_cls: [DummyFlowDecorator()]
    )

    def command_fn():
        return None

    with pytest.raises(MetaflowInternalError, match="invalid run option name"):
        decorators.add_run_decorator_options(command_fn)


def test_common_run_options_parses_decorator_option_via_click(monkeypatch):
    class DummyFlowDecorator:
        name = "dummy"
        run_options = {
            "demo-priority": {
                "default": "normal",
                "show_default": True,
                "type": click.Choice(["normal", "high"]),
                "help": "Demo priority",
            }
        }

    monkeypatch.setattr(current_flow, "flow_cls", object(), raising=False)
    monkeypatch.setattr(
        decorators, "flow_decorators", lambda flow_cls: [DummyFlowDecorator()]
    )

    captured = {}

    @run_cmds.common_run_options
    def command_fn(**kwargs):
        captured.update(kwargs)
        click.echo("ok")

    command = click.command()(command_fn)
    result = CliRunner().invoke(command, ["--demo-priority", "high"])

    assert result.exit_code == 0
    assert captured["demo_priority"] == "high"
    assert "ok" in result.output


def test_run_cli_lifecycle_hooks_invokes_tl_plugin_hooks(monkeypatch):
    calls = []

    class HookPlugin:
        @staticmethod
        def cli_init(phase, ctx):
            calls.append((phase, ctx))

    monkeypatch.setattr(
        cli_mod.plugins,
        "TL_PLUGINS",
        {"hook": HookPlugin, "noop": object()},
        raising=False,
    )

    ctx = SimpleNamespace()
    cli_mod._run_cli_lifecycle_hooks("post_start", ctx)
    assert calls == [("post_start", ctx)]


def test_run_cli_lifecycle_hooks_wraps_hook_errors(monkeypatch):
    class BrokenPlugin:
        @staticmethod
        def cli_init(phase, ctx):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        cli_mod.plugins, "TL_PLUGINS", {"broken": BrokenPlugin}, raising=False
    )

    with pytest.raises(CommandException, match="broken"):
        cli_mod._run_cli_lifecycle_hooks("post_datastore", SimpleNamespace())