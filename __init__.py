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

from flask import render_template, Blueprint, flash, request, redirect, url_for
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.migrations import upgrade
from CTFd.utils.decorators import admins_only
from CTFd.models import db, Solves, Challenges, Teams
from CTFd.utils.dates import ctf_started
from datetime import datetime, timedelta

from .models import WebhookLog
from .webhooks import webhook_config, send_webhook
from .events import event_registry
from .event_definitions import *


PLUGIN_PATH = os.path.dirname(__file__)
CONFIG = json.load(open("{}/config.json".format(PLUGIN_PATH)))
directory_name = PLUGIN_PATH.split(os.sep)[-1]  # Get the directory name of this file

webhooks_bp = Blueprint(directory_name, __name__, template_folder="templates")

last_scoreboard_update = None
SCOREBOARD_UPDATE_INTERVAL = timedelta(minutes=5)


def scoreboard_update_hook(user_id=None, team_id=None):
    global last_scoreboard_update
    now = datetime.utcnow()

    # Check if enough time has elapsed since the last update
    if (
        last_scoreboard_update is None
        or (now - last_scoreboard_update) >= SCOREBOARD_UPDATE_INTERVAL
    ):
        data = event_registry.generate_payload(
            "scoreboard_update", user_id=user_id, team_id=team_id
        )
        send_webhook("scoreboard_update", data)
        last_scoreboard_update = now
    else:
        print(
            f"[WEBHOOGZ] Scoreboard update skipped (last update: {last_scoreboard_update}, next allowed: {last_scoreboard_update + SCOREBOARD_UPDATE_INTERVAL})"
        )


def challenge_creation_hook(challenge):
    data = event_registry.generate_payload("challenge_created", challenge)
    send_webhook("challenge_created", data)


def firstblood_hook(solve):
    # Check if this is the first solve
    solve_count = Solves.query.filter_by(challenge_id=solve.challenge_id).count()
    if solve_count == 1:
        data = event_registry.generate_payload("firstblood", solve)
        send_webhook("firstblood", data)


def challenge_solved_hook(solve):
    data = event_registry.generate_payload("challenge_solved", solve)
    send_webhook("challenge_solved", data)


def ctf_start_hook():
    if ctf_started():
        data = event_registry.generate_payload("ctf_started")
        send_webhook("ctf_started", data)


def team_creation_hook(team):
    data = event_registry.generate_payload("team_created", team)
    send_webhook("team_created", data)


# Wrapper for hooks around solve after_inster event
def handle_solve_after_insert(mapper, conn, solve):
    """Handle post-insert events for challenge solves in CTFd.

    Triggers webhooks for challenge solves, first-blood achievements, and scoreboard
    updates when a new solve is recorded.

    Args:
        mapper: SQLAlchemy mapper object for the Solves model.
        conn: SQLAlchemy connection object for the database.
        solve (Solves): The newly inserted solve object.

    Returns:
        None
    """

    challenge_solved_hook(solve)
    firstblood_hook(solve)
    scoreboard_update_hook(
        solve.user_id, solve.team_id if hasattr(solve, "team_id") else None
    )


# -------------------------------------------------------------------------------- LOAD


def load(app):
    """Initialize the webhook plugin for CTFd.

    Sets up the database, runs migrations, registers assets, defines routes, and
    attaches event listeners for webhook triggers.

    Args:
        app (Flask): The CTFd Flask application instance.

    Returns:
        None
    """

    # Ensure database tables are created
    app.db.create_all()
    # Run plugin migrations
    upgrade()
    # Serve static assets from the plugin's assets directory
    register_plugin_assets_directory(
        app, base_path=f"/plugins/{directory_name}/assets/"
    )

    @webhooks_bp.route("/admin/webhoogz", methods=["GET", "POST"])
    @admins_only
    def webhook_config_route():
        """Handle webhook configuration management for admins.

        GET: Display the webhook configuration page with current URLs, events, and logs.
        POST: Update webhook configurations based on form data.

        Returns:
            flask.Response: Rendered template for GET, redirect for POST.
        """

        if request.method == "POST":
            # Extract form data
            urls = request.form.getlist("webhook_url")
            secrets = request.form.getlist("hmac_secret")
            config_ids = request.form.getlist("config_id")
            events = {
                event_id: request.form.getlist(f"events_{event_id}")
                for event_id in event_registry.get_events().keys()
            }

            new_config = {}
            for i, url in enumerate(urls):
                if url.strip():
                    # Use existing config_id or assign new one
                    config_id = (
                        config_ids[i]
                        if i < len(config_ids) and config_ids[i]
                        else str(webhook_config.next_id)
                    )
                    # Determine events for existing vs. new configs
                    if config_id in webhook_config.urls:
                        subscribed_events = [
                            event_id
                            for event_id, checked_ids in events.items()
                            if config_id in checked_ids
                        ]
                    else:
                        subscribed_events = [
                            event_id
                            for event_id, checked_urls in events.items()
                            if url in checked_urls
                        ]
                        if config_id == str(webhook_config.next_id):
                            webhook_config.next_id += 1

                    # Store secret if provided
                    secret = (
                        secrets[i].strip()
                        if i < len(secrets) and secrets[i].strip()
                        else None
                    )
                    new_config[config_id] = {
                        "url": url.strip(),
                        "events": subscribed_events,  # Can be empty
                        "secret": secret,
                    }

            # Update and save configuration
            webhook_config.urls = new_config
            webhook_config.save_config()
            flash("Webhook configuration updated!", "success")
            return redirect(url_for("webhoogz.webhook_config_route"))

        # Prepare logs for each URL
        logs_by_url = {}
        for config_id, data in webhook_config.urls.items():
            url = data["url"]
            logs_by_url[url] = (
                WebhookLog.query.filter_by(config_id=config_id)
                .order_by(WebhookLog.timestamp.desc())
                .limit(50)
                .all()
            )

        # Format event data for template
        webhook_events_with_wrapper = {
            event_id: {
                "display_name": event_data["display_name"],
                "description": event_data["description"],
                "sample_payload": {
                    "event": event_id,
                    "data": event_data["sample_data"],
                },
            }
            for event_id, event_data in event_registry.get_events().items()
        }

        return render_template(
            "webhoogz.html",
            webhook_config=webhook_config.urls,
            webhook_events=webhook_events_with_wrapper,
            logs_by_url=logs_by_url,
        )

    @webhooks_bp.route("/admin/webhoogz/delete/<config_id>", methods=["POST"])
    @admins_only
    def delete_webhook_config(config_id):
        """Delete a webhook configuration and its associated logs.

        Args:
            config_id (str): The ID of the configuration to delete.

        Returns:
            flask.Response: Redirect to the webhook configuration page.
        """

        if config_id in webhook_config.urls:
            # Remove associated logs
            WebhookLog.query.filter_by(config_id=config_id).delete()
            db.session.commit()

            # Remove config entry
            del webhook_config.urls[config_id]
            webhook_config.save_config()
            flash(f"Webhook configuration {config_id} deleted!", "success")
        else:
            flash(f"Webhook configuration {config_id} not found!", "error")
        return redirect(url_for("webhoogz.webhook_config_route"))

    # Register event listeners for CTFd events
    app.db.event.listen(
        Challenges,
        "after_insert",
        lambda mapper, conn, challenge: challenge_creation_hook(challenge),
    )
    app.db.event.listen(
        Teams, "after_insert", lambda mapper, conn, team: team_creation_hook(team)
    )
    app.db.event.listen(Solves, "after_insert", handle_solve_after_insert)

    app.register_blueprint(webhooks_bp)
    print("[WEBHOOGZ] Loaded successfully!")
