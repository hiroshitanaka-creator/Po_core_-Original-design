"""po_core_original.trace_validation.errors

Trace continuity error taxonomy (PR-008).

These exceptions are raised by ``TraceValidationResult.raise_if_invalid()`` /
``TraceContinuityValidator.assert_valid()`` (see ``validator.py``). Every issue
carries an ``event_id`` / ``event_type`` and a short remediation hint in its
message where available, so a caller does not have to re-derive "what's wrong
and where" from a bare boolean.
"""

from __future__ import annotations


class TraceContinuityError(ValueError):
    """Base class for all trace continuity validation errors."""


class MissingRootEventError(TraceContinuityError):
    """No ``SemanticProfileComputed`` root event exists in the validated set."""


class OrphanTraceEventError(TraceContinuityError):
    """A Po_self / Viewer / reconstruction event has no valid continuity path."""


class MissingParentEventError(TraceContinuityError):
    """A required parent/ancestor event (or trace_refs target) is absent."""


class InvalidTraceTransitionError(TraceContinuityError):
    """An event's payload contradicts the required trace transition contract."""


class RequestIdMismatchError(TraceContinuityError):
    """The validated events do not share a single ``request_id``."""


class DuplicateEventIdError(TraceContinuityError):
    """Two or more events share the same ``event_id``."""
