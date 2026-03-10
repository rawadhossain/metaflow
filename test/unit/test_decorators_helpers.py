from types import SimpleNamespace

from metaflow.decorators import StepDecorator, _sort_step_decorators


class _DummyDecorator(StepDecorator):
    name = "dummy"

    def __init__(self, priority):
        super(_DummyDecorator, self).__init__()
        self.ORDER_PRIORITY = priority


class _MetadataRecorder(object):
    def __init__(self):
        self.calls = []

    def register_metadata(self, run_id, step_name, task_id, metadata):
        self.calls.append((run_id, step_name, task_id, metadata))


def test_sort_step_decorators_priority_then_source_order():
    d0 = _DummyDecorator(priority=0)
    d1 = _DummyDecorator(priority=-1)
    d2 = _DummyDecorator(priority=0)
    step = SimpleNamespace(decorators=[d0, d1, d2])

    _sort_step_decorators(step)

    # Lowest priority first, ties preserve source order.
    assert step.decorators == [d1, d0, d2]


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
