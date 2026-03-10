"""Scope plugin hook implementation for gesture arcade."""

from scope.core.plugins.hookspecs import hookimpl


@hookimpl
def register_pipelines(register):
    from .pipelines.pipeline import GestureArcadePipeline

    register(GestureArcadePipeline)
