from argparse import Namespace
from types import SimpleNamespace

import pytest

from src.tests.__common.shapes.stages_shape import DEFAULT_STAGES, StagesShape, load_stages_on_init

STAGES_JSON = '[{"duration": 10, "users": 2, "spawn_rate": 0.5}, {"duration": 30, "users": 4, "spawn_rate": 1}]'


def make_shape(stages_json: str | None, run_time: float) -> StagesShape:
    shape = StagesShape()
    load_stages_on_init(SimpleNamespace(shape_class=shape, parsed_options=Namespace(STAGES=stages_json)))
    shape.get_run_time = lambda: run_time
    return shape


@pytest.mark.parametrize("run_time, expected", [(0, (2, 0.5)), (9.9, (2, 0.5)), (10, (4, 1)), (29, (4, 1))])
def test_tick_follows_stages(run_time, expected):
    assert make_shape(STAGES_JSON, run_time).tick() == expected


def test_tick_stops_after_last_stage():
    assert make_shape(STAGES_JSON, 30).tick() is None


def test_defaults_without_stages_option():
    first = DEFAULT_STAGES[0]

    assert make_shape(None, 0).tick() == (first.users, first.spawn_rate)


def test_invalid_stages_fail_at_init():
    with pytest.raises(ValueError):
        make_shape('[{"duration": 0, "users": 1, "spawn_rate": 1}]', 0)


def test_init_ignores_foreign_shapes():
    environment = SimpleNamespace(shape_class=None, parsed_options=Namespace(STAGES=STAGES_JSON))

    load_stages_on_init(environment)

    assert environment.shape_class is None


def test_stages_are_independent_per_shape_instance():
    make_shape(STAGES_JSON, 0).tick()

    assert make_shape(None, 0).tick() == (DEFAULT_STAGES[0].users, DEFAULT_STAGES[0].spawn_rate)
