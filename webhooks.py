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

import os
import json
import requests
import hmac
import hashlib

from CTFd.utils import get_config, set_config, get_app_config
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import WebhookLog


class WebhookConfig:
    """Manages webhook configurations in CTFd, storing URLs and their associated events.

    This class handles the loading, saving, and querying of webhook configurations,
    including target URLs, associated events, and HMAC secrets. Configurations are
    stored in CTFd's configuration system as JSON.

    Attributes:
        urls (dict): A dictionary mapping configuration IDs to webhook details
            (url, events, secret).
        next_id (int): The next available ID for a new webhook configuration.
    """

    def __init__(self):
        """Initialize an empty webhook configuration."""

        self.urls = {}
        self.next_id = 1
        self.load_config()

    def load_config(self):
        """Load webhook configurations from CTFd's config storage.

        Retrieves the JSON-encoded webhook configuration from CTFd's database and
        populates the urls attribute. Updates next_id based on existing IDs.
        """

        config = get_config("WEBHOOK_CONFIG")
        if config:
            self.urls = json.loads(config)
            if self.urls:
                self.next_id = max(int(id) for id in self.urls.keys()) + 1
        else:
            self.urls = {}

    def save_config(self):
        """Save webhook configurations to CTFd's config storage.

        Serializes the urls attribute to JSON and stores it in CTFd's configuration.
        """
        set_config("WEBHOOK_CONFIG", json.dumps(self.urls))

    def get_urls_for_event(self, event):
        """Retrieve URLs configured for a specific event.

        Args:
            event (str): The event type to query (e.g., 'user_signup').

        Returns:
            list: A list of URLs configured to receive the specified event.
        """

        return [
            data["url"]
            for data in self.urls.values()
            if event in data.get("events", [])
        ]

    def get_secret_for_url(self, url):
        """Get the HMAC secret for a given webhook URL.

        Args:
            url (str): The webhook URL to query.

        Returns:
            str or None: The HMAC secret for the URL, or None if not found.
        """

        for data in self.urls.values():
            if data["url"] == url:
                return data.get("secret")
        return None

    def get_id_for_url(self, url):
        """Get the configuration ID for a given webhook URL.

        Args:
            url (str): The webhook URL to query.

        Returns:
            str or None: The configuration ID for the URL, or None if not found.
        """

        for id, data in self.urls.items():
            if data["url"] == url:
                return id
        return None


webhook_config = WebhookConfig()
"""Global instance of WebhookConfig for managing webhook configurations.

This instance is used to store and query webhook URLs, events, and secrets across
the CTFd application.

Example:
    from webhook_config import webhook_config
    urls = webhook_config.get_urls_for_event('user_signup')
    print(urls)  # List of URLs configured for 'user_signup'
"""


def send_webhook(event_type, data):
    """Send a webhook payload to configured URLs for a given event.

    Constructs a JSON payload with the event type and data, computes an HMAC signature,
    and sends POST requests to all URLs configured for the event. Logs the results
    using WebhookLog.

    Args:
        event_type (str): The type of event triggering the webhook (e.g., 'user_signup').
        data (dict): The data to include in the webhook payload.

    Returns:
        None
    """

    # Get URLs configured for this event
    target_urls = webhook_config.get_urls_for_event(event_type)
    if not target_urls:
        print(f"[WEBHOOGZ] No webhooks configured for event: {event_type}")
        return

    # Create payload with event and data
    payload = {"event": event_type, "data": data}

    # Initialize a new SQLAlchemy session for logging
    engine = create_engine(get_app_config("SQLALCHEMY_DATABASE_URI"))
    Session = sessionmaker(bind=engine)
    log_session = Session()

    # Get default HMAC secret from environment
    default_secret = os.getenv("WEBHOOK_SECRET")
    for url in target_urls:
        # Use URL-specific secret or fallback to default
        secret = webhook_config.get_secret_for_url(url) or default_secret
        if not secret:
            print(
                f"[WEBHOOGZ] No HMAC secret configured for {url} (and no WEBHOOK_SECRET env var)"
            )
            continue

        # Convert to bytes for HMAC
        secret = secret.encode("utf-8")

        config_id = webhook_config.get_id_for_url(url)
        try:
            # Serialize payload compactly for consistent HMAC
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

            # Compute HMAC-SHA256 signature
            signature = hmac.new(secret, body, digestmod=hashlib.sha256)
            signature_hex = signature.hexdigest()

            # Prepare POST request with custom headers
            request = requests.Request(method="POST", url=url, data=body)
            prepped = request.prepare()
            prepped.body = body  # Override default serialization with compact version
            prepped.headers["X-CTFd-HMAC-Signature"] = signature_hex
            prepped.headers["Content-Type"] = "application/json"

            # Send request and log response
            with requests.Session() as session:
                response = session.send(prepped)
                log_entry = WebhookLog(
                    config_id=config_id,
                    url=url,
                    event_type=event_type,
                    status="success",
                    response_code=response.status_code,
                    timestamp=datetime.utcnow(),
                )
                log_session.add(log_entry)
                log_session.commit()
                print(f"[WEBHOOGZ] Webhook sent to {url}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            # Log any request errors
            log_entry = WebhookLog(
                config_id=config_id,
                url=url,
                event_type=event_type,
                status="error",
                error_message=str(e),
                timestamp=datetime.utcnow(),
            )
            log_session.add(log_entry)
            log_session.commit()
            print(f"[WEBHOOGZ] Webhook error for {url}: {e}")
        finally:
            # Always close the session
            log_session.close()
