from types import SimpleNamespace

import pytest

from metaflow.decorators import StepDecorator, _sort_step_decorators
from metaflow.exception import MetaflowException


class _DummyDecorator(StepDecorator):
    name = "dummy-default"

    def __init__(self, name, depends_on=None):
        super(_DummyDecorator, self).__init__()
        self.name = name
        self.DEPENDS_ON = depends_on or []


class _MetadataRecorder(object):
    def __init__(self):
        self.calls = []

    def register_metadata(self, run_id, step_name, task_id, metadata):
        self.calls.append((run_id, step_name, task_id, metadata))


def test_sort_step_decorators_priority_then_source_order():
    # Updated to dependency semantics: A depends on B.
    d0 = _DummyDecorator(name="A", depends_on=["B"])
    d1 = _DummyDecorator(name="B")
    d2 = _DummyDecorator(name="C")
    step = SimpleNamespace(decorators=[d0, d1, d2])

    _sort_step_decorators(step)

    # B must run before A. C stays last because it has no dependencies.
    assert step.decorators == [d1, d0, d2]


def test_sort_step_decorators_no_dependencies_preserves_source_order():
    d0 = _DummyDecorator(name="A")
    d1 = _DummyDecorator(name="B")
    d2 = _DummyDecorator(name="C")
    step = SimpleNamespace(decorators=[d0, d1, d2])

    _sort_step_decorators(step)

    assert step.decorators == [d0, d1, d2]


def test_sort_step_decorators_a_depends_on_b():
    a = _DummyDecorator(name="A", depends_on=["B"])
    b = _DummyDecorator(name="B")
    step = SimpleNamespace(decorators=[a, b])

    _sort_step_decorators(step)

    assert step.decorators == [b, a]


def test_sort_step_decorators_diamond_dependency():
    # C depends on A and B, both A and B depend on D.
    a = _DummyDecorator(name="A", depends_on=["D"])
    b = _DummyDecorator(name="B", depends_on=["D"])
    c = _DummyDecorator(name="C", depends_on=["A", "B"])
    d = _DummyDecorator(name="D")
    step = SimpleNamespace(decorators=[a, b, c, d])

    _sort_step_decorators(step)

    assert step.decorators == [d, a, b, c]


def test_sort_step_decorators_cycle_raises_metaflow_exception():
    a = _DummyDecorator(name="A", depends_on=["B"])
    b = _DummyDecorator(name="B", depends_on=["A"])
    step = SimpleNamespace(decorators=[a, b])

    with pytest.raises(
        MetaflowException, match=r"Circular dependency detected among decorators:"
    ):
        _sort_step_decorators(step)


def test_register_metadata_keeps_none_by_default():
    deco = StepDecorator()
    metadata = _MetadataRecorder()

    deco._register_metadata(
        metadata=metadata,
        run_id="r1",
        step_name="s1",
        task_id="t1",
        meta_dict={"a": "1", "b": None},
        retry_count=2,
    )

    assert len(metadata.calls) == 1
    _, _, _, entries = metadata.calls[0]
    assert [(e.field, e.value) for e in entries] == [("a", "1"), ("b", None)]
    assert all("attempt_id:2" in e.tags for e in entries)


def test_register_metadata_can_skip_none():
    deco = StepDecorator()
    metadata = _MetadataRecorder()

    deco._register_metadata(
        metadata=metadata,
        run_id="r1",
        step_name="s1",
        task_id="t1",
        meta_dict={"a": "1", "b": None},
        retry_count=3,
        skip_none=True,
    )

    assert len(metadata.calls) == 1
    _, _, _, entries = metadata.calls[0]
    assert [(e.field, e.value) for e in entries] == [("a", "1")]
    assert "attempt_id:3" in entries[0].tags