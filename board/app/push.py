"""
Web Push utilities for sending notifications from the Flask API server.

This expects VAPID keys generated with:
    npm install -g web-push
    web-push generate-vapid-keys

Note: requires the `pywebpush` package.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import json

from flask import current_app

# Import pywebpush directly (packages assumed installed)
from pywebpush import webpush, WebPushException

from marshmallow import fields
from .provider import ma


# --------------------------- Marshmallow Schemas (for later use) ---------------------------

class PushKeysSchema(ma.Schema):
    p256dh = fields.String(required=True)
    auth = fields.String(required=True)


class PushSubscriptionSchema(ma.Schema):
    endpoint = fields.String(required=True)
    keys = fields.Nested(PushKeysSchema, required=True)


class PushActionSchema(ma.Schema):
    action = fields.String(required=True)
    title = fields.String(required=True)
    icon = fields.String(load_default=None)


class PushMessageSchema(ma.Schema):
    title = fields.String(required=True)
    body = fields.String(required=True)
    icon = fields.String(load_default=None)
    badge = fields.String(load_default=None)
    url = fields.String(load_default=None)
    tag = fields.String(load_default=None)
    data = fields.Dict(load_default=None)
    actions = fields.List(fields.Nested(PushActionSchema), load_default=list)

class VapidPublicKeySchema(ma.Schema):
    public_key = fields.String(required=True)

class EndpointSchema(ma.Schema):
    endpoint = fields.String(required=True)


# --------------------------- Helpers ---------------------------

class PushSubscriptionGone(Exception):
    """Raised when a subscription is no longer valid (HTTP 404/410)."""

def is_configured() -> bool:
    """Return True if pywebpush is available and VAPID config is present."""
    try:
        return current_app.config.get("PUSH_VAPID") is not None
    except Exception:
        return False


# --------------------------- Payload Builder ---------------------------

def build_payload(
    title: str,
    body: str,
    *,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    url: Optional[str] = None,
    tag: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create a notification payload compatible with the Web Notifications API.

    This structure is typically consumed in a Service Worker push handler.
    """
    payload: Dict[str, Any] = {"title": title, "body": body}
    if icon:
        payload["icon"] = icon
    if badge:
        payload["badge"] = badge
    if url:
        payload["url"] = url
    if tag:
        payload["tag"] = tag
    if data is not None:
        payload["data"] = data
    if actions:
        payload["actions"] = actions
    return payload


# --------------------------- Send functions ---------------------------

def send_to_subscription(
    subscription: Union[Dict[str, Any], "PushSubscriptionLike"],
    payload: Union[Dict[str, Any], str],
    *,
    ttl: int = 60,
) -> Tuple[int, Optional[str]]:
    """Send a Web Push notification to a single subscription.

    Args:
        subscription: A dict with shape {endpoint, keys: {p256dh, auth}} or an object exposing these.
        payload: Dict (will be JSON-encoded) or a pre-encoded JSON string.
        ttl: Time-to-live in seconds for the push message.

    Returns:
        (status_code, response_text)

    Raises:
        PushSubscriptionGone: When the subscription is no longer valid (HTTP 404/410)
        ValueError: When configuration or input is invalid
    """

    # Normalize input
    if hasattr(subscription, "endpoint") and hasattr(subscription, "keys"):
        sub_dict: Dict[str, Any] = {
            "endpoint": getattr(subscription, "endpoint"),
            "keys": {
                "p256dh": subscription.keys.get("p256dh") if isinstance(subscription.keys, dict) else getattr(subscription.keys, "p256dh", None),
                "auth": subscription.keys.get("auth") if isinstance(subscription.keys, dict) else getattr(subscription.keys, "auth", None),
            },
        }
    else:
        sub_dict = dict(subscription)  # type: ignore[arg-type]

    # Validate shape
    if not sub_dict.get("endpoint", None) or "keys" not in sub_dict:
        raise ValueError("Invalid subscription: missing endpoint or keys")
    keys = sub_dict.get("keys") or {}
    if not (keys.get("p256dh") and keys.get("auth")):
        raise ValueError("Invalid subscription: missing keys.p256dh or keys.auth")

    if isinstance(payload, dict):
        payload_str = json.dumps(payload, separators=(",", ":"))
    else:
        payload_str = payload

    vapid = (current_app.config.get("PUSH_VAPID") or {})

    try:
        resp = webpush(
            subscription_info=sub_dict,
            data=payload_str,
            vapid_private_key=vapid["private_key"],
            vapid_claims={"sub": vapid["subject"]},
            ttl=ttl,
        )
        status = getattr(resp, "status_code", 201)
        text = getattr(resp, "text", None) if hasattr(resp, "text") else None
        return int(status), text
    except WebPushException as e:  # type: ignore[misc]
        # pywebpush exposes response attr when available
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (404, 410):
            raise PushSubscriptionGone(str(e))
        # Re-raise a simpler error upward
        raise RuntimeError(f"WebPush failed: {e}")


def send_bulk(
    subscriptions: Iterable[Union[Dict[str, Any], "PushSubscriptionLike"]],
    payload: Union[Dict[str, Any], str],
    *,
    ttl: int = 60,
) -> Dict[str, Any]:
    """Send a notification to many subscriptions.

    Returns a result dict:
    {
        "success": [indexes],
        "failed": [indexes],
        "gone": [indexes],  # invalid subscriptions (404/410)
    }
    """
    results = {"success": [], "failed": [], "gone": []}
    for idx, sub in enumerate(subscriptions):
        try:
            status, _ = send_to_subscription(sub, payload, ttl=ttl)
            if 200 <= status < 300:
                results["success"].append(idx)
            else:
                results["failed"].append(idx)
        except PushSubscriptionGone:
            results["gone"].append(idx)
        except Exception:
            results["failed"].append(idx)
    return results


# --------------------------- Protocol types ---------------------------
class PushSubscriptionLike:
    """Protocol-like base to document expected attributes for a subscription object.

    Implementations should expose:
      - endpoint: str
      - keys: {"p256dh": str, "auth": str} or an object with .p256dh/.auth
    """
    endpoint: str
    keys: Any
