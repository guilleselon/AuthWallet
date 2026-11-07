import pytest

from relay.adapters.outbound.in_memory import StaticTokenValidator
from relay.domain.errors import Unauthorized
from relay.domain.types import ProjectId


def test_valid_token_returns_project_id():
    v = StaticTokenValidator({"tok-1": ProjectId("proj-1")})
    assert v.validate("tok-1") == "proj-1"


def test_unknown_token_raises_unauthorized():
    v = StaticTokenValidator({"tok-1": ProjectId("proj-1")})
    with pytest.raises(Unauthorized):
        v.validate("wrong")


def test_empty_mapping_rejects_everything():
    v = StaticTokenValidator({})
    with pytest.raises(Unauthorized):
        v.validate("anything")


def test_constructor_copies_input_mapping():
    src = {"tok-1": ProjectId("proj-1")}
    v = StaticTokenValidator(src)
    src["tok-2"] = ProjectId("proj-2")
    # Mutating the caller's dict doesn't affect the validator.
    with pytest.raises(Unauthorized):
        v.validate("tok-2")
