"""Generate a stable, JSON-ready catalogue for executable Agent tools."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any


TOOL_MODULES: dict[str, tuple[str, ...]] = {
    "monte_carlo": ("module00",),
    "bernoulli": ("module01",),
    "poisson": ("module01",),
    "random_walk": ("module02",),
    "continuous_random_walk": ("module03",),
    "brownian_motion": ("module04",),
    "markov_chain": ("module05",),
    "ctmc": ("module06",),
    "birth_death": ("module06",),
    "reliability": ("module07",),
    "buffer": ("module07",),
    "mm1_queue": ("module07",),
    "nhpp": ("module08",),
    "self_avoiding_walk": ("module09",),
    "coalescing_particles": ("module10",),
}


def _json_type(annotation: Any) -> str:
    rendered = str(annotation).strip("'")
    if rendered == "int":
        return "integer"
    if rendered == "float":
        return "number"
    if "Sequence" in rendered or rendered.startswith("list"):
        return "array"
    return "string"


def build_tool_catalog(
    tools: dict[str, Callable[..., dict[str, Any]]],
) -> list[dict[str, Any]]:
    catalogue: list[dict[str, Any]] = []
    for key, tool in tools.items():
        signature = inspect.signature(tool)
        parameters = []
        for parameter in signature.parameters.values():
            required = parameter.default is inspect.Parameter.empty
            item: dict[str, Any] = {
                "name": parameter.name,
                "type": _json_type(parameter.annotation),
                "required": required,
            }
            if not required:
                item["default"] = parameter.default
            parameters.append(item)
        doc = inspect.getdoc(tool) or "Executable stochastic-process tool."
        catalogue.append(
            {
                "key": key,
                "function": tool.__name__,
                "module_ids": list(TOOL_MODULES[key]),
                "description": doc.splitlines()[0],
                "parameters": parameters,
            }
        )
    return catalogue
