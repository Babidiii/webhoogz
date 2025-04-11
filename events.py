# This file is part of Webhoogz - A CTFd webhook plugin
#
# Webhoogz is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from functools import wraps


class WebhookEventRegistry:
    """A registry for managing webhook events with metadata and payload generators.

    This class allows registration of webhook events, each associated with a unique
    event ID, display name, description, sample data, and a payload-generating function.
    Events can be registered directly or via a decorator, and payloads can be generated
    dynamically based on event IDs.

    Attributes:
        events (dict): A dictionary mapping event IDs to their metadata and payload
            generator functions.
    """

    def __init__(self):
        """Initialize an empty webhook event registry."""
        self.events = {}

    def register(
        self, event_id, display_name, description, sample_data, generate_payload
    ):
        """Register a new webhook event with metadata.

        Args:
            event_id (str): Unique identifier for the event.
            display_name (str): Human-readable name for the event.
            description (str): Detailed description of the event's purpose.
            sample_data (dict): Example data structure for the event payload.
            generate_payload (callable): Function to generate the event's payload.

        Returns:
            None
        """

        self.events[event_id] = {
            "display_name": display_name,
            "description": description,
            "sample_data": sample_data,
            "generate_payload": generate_payload,
        }

    def get_events(self):
        """Retrieve all registered events.

        Returns:
            dict: A dictionary of all events, mapping event IDs to their metadata.
        """
        return self.events

    def generate_payload(self, event_id, *args, **kwargs):
        """Generate a payload for a registered event.

        Args:
            event_id (str): The ID of the event to generate a payload for.
            *args: Positional arguments to pass to the payload generator.
            **kwargs: Keyword arguments to pass to the payload generator.

        Returns:
            The generated payload from the event's registered function.

        Raises:
            ValueError: If the event_id is not found or has no payload generator.
        """

        if event_id in self.events and self.events[event_id]["generate_payload"]:
            return self.events[event_id]["generate_payload"](*args, **kwargs)
        raise ValueError(f"Event {event_id} not found or has no payload generator")

    def event(self, event_id, display_name, description, sample_data):
        """Decorator to register a webhook event.

        Args:
            event_id (str): Unique identifier for the event.
            display_name (str): Human-readable name for the event.
            description (str): Detailed description of the event's purpose.
            sample_data (dict): Example data structure for the event payload.

        Returns:
            callable: A decorator that registers the decorated function as the
                event's payload generator.

        Example:
            @registry.event(
                event_id="user_signup",
                display_name="User Signup",
                description="Triggered when a user signs up.",
                sample_data={"user_id": 123, "email": "user@example.com"}
            )
            def generate_payload(user_id, email):
                return {"event": "user_signup", "user_id": user_id, "email": email}
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self.register(event_id, display_name, description, sample_data, wrapper)
            return wrapper

        return decorator


event_registry = WebhookEventRegistry()
"""Global instance of WebhookEventRegistry for managing webhook events.

This instance can be imported and used across modules to register and manage
webhook events consistently.

Example:
    from webhook_registry import event_registry

    @event_registry.event(
        event_id="user_signup",
        display_name="User Signup",
        description="Triggered when a user signs up.",
        sample_data={"user_id": 123, "email": "user@example.com"}
    )
    def generate_payload(user_id, email):
        return {"event": "user_signup", "user_id": user_id, "email": email}
"""
