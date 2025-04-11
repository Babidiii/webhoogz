# Webhoogz

This plugin extends [CTFd](https://github.com/CTFd/CTFd) to send webhook notifications for various events during a Capture The Flag (CTF) competition. 

## Features
- **Event Types**:
  - `challenge_created`: Fired when a new challenge is added.
  - `firstblood`: Triggered when a challenge is solved for the first time.
  - `challenge_solved`: Sent for every challenge solve.
  - `ctf_started`: Notifies when the CTF begins.
  - `team_created`: Alerts when a new team is created.
  - `scoreboard_update`: Provides periodic updates of the top 5 teams/users (debounced to reduce frequency).
	- *Custom Events*: Define your own events (e.g., `user_signin`) with payloads and metadata.
- **Configurable Webhooks**: Add multiple webhook URLs with event subscriptions and optional `HMAC secrets` via the admin panel.
- **Automatic Event UI**: Each event type registered appears in the admin UI with a checkbox for each webhook URL, allowing flexible subscriptions.
- **Generated Documentation**: Event metadata (name, description, sample data) is displayed in the admin UI for easy reference.
- **Logging**: Tracks webhook success/failure with timestamps and error messages.
- **Debounced Scoreboard Updates**: Limits `scoreboard_update` events to once every 5 minutes to prevent spamming during high solve rates.

## Demo

https://github.com/user-attachments/assets/1f41140d-0ab4-4820-8f3d-b372114cd22a

## Installation
1. **Clone the Repository into CTFd Plugins Directory**:
   - Navigate to your CTFd installation’s plugins directory and clone the plugin there:
     ```bash
     cd /path/to/CTFd/CTFd/plugins/
     git clone https://github.com/Babidiii/webhoogz.git
     ```
2. **Restart CTFd**:
   - **If using Docker Compose**:
     - From your CTFd root directory (where `docker-compose.yml` is located):
       ```bash
       docker-compose down
       docker-compose up -d
       ```
     - This restarts all services and loads the plugin.
3. **Configure Webhooks**:
   - Log in as an admin, navigate to `/admin/webhoogz`, and add your webhook URLs with desired event subscriptions.

## Usage
- **Admin Interface**: Access `/admin/webhoogz` to manage webhook configurations and view logs.
- **Event Payloads**: Each event sends a JSON payload with an `"event"` field and a `"data"` object. See the "Available Events" section in the admin UI for sample structures.
- **HMAC Security**: Optionally set an HMAC secret per webhook URL for signed requests (falls back to `WEBHOOK_SECRET` env var if unset).
- **Event Documentation**: The admin UI automatically displays each event’s `display_name`, `description`, and `sample_data` (as defined in `event_definitions.py`), helping admins understand event purposes and payloads.

## Adding New Event Types

You can define custom event types using the `WebhookEvenRegistry` class in `webhook_registry.py`. Each event requires:

- A unique `event_id` (e.g., `user_signin`).
- A `display_name` for the admin UI.
- A `description` explaining the event's purpose.
- A `sample_data` dictionary showing the expected payload structure.
- A `generate_payload` function to create the actual payload

**Example:**

```py
# In event_definitions.py
from .events import event_registry

@event_registry.event(
    event_id="user_signin",
    display_name="User Sign-In",
    description="Triggered when a user logs into CTFd.",
    sample_data={"user_id": 123, "username": "example_user", "timestamp": "2025-04-11T12:00:00Z"}
)
def generate_user_signin_payload(user):
    return {
        "user_id": user.id,
        "username": user.name,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

**Triggering the Event:**

Hook into CTFd’s login process (e.g., via a custom route or signal) to call:

```py
from .webhooks import send_webhook
send_webhook("user_signin", {"user_id": user.id, "username": user.name})
```

### Scoreboard Update Delay
- The `scoreboard_update` event is debounced to fire at most once every 5 minutes, even though it’s triggered by every solve (`Solves.after_insert`).
- **Why**: Prevents overwhelming external services during rapid solve bursts.
- **Customization**: Edit `SCOREBOARD_UPDATE_INTERVAL` in `__init__.py` (default: `timedelta(minutes=5)`) to adjust the delay (e.g., 10 minutes: `timedelta(minutes=10)`).

## Notes
- **Dependencies**: Requires CTFd 3.x+ for `CTFd.utils.scores.get_standings`. For older versions, modify the `scoreboard_update`.
- **Performance**: The `scoreboard_update` uses `get_standings()` for efficient sorting, but `Teams.query.count()` and `Users.query.count()` might be slow with large datasets—consider caching if needed.
- **Persistence**: The debounce timer (`last_scoreboard_update`) resets on server restart. For persistent timing, store it in CTFd’s config (not implemented here).
- **CTF Mode**: `top_teams` or `top_users` populates based on the `TEAMS` setting in CTFd.

## Troubleshooting
- **ImportError: `get_standings` not found**:
  - Ensure you’re on CTFd 3.x+ and use `from CTFd.utils.scores import get_standings`.
  - For older versions (< 3.0), try `from CTFd.utils import get_standings` or implement a manual standings query.
- **Frequent Updates**: If `scoreboard_update` fires too often, verify the debounce logic in `scoreboard_update_hook`.
- **No Events**: Check logs for webhook errors and ensure URLs are reachable.

## License

This project is licensed under the **GNU Affero General Public License v3.0** (**AGPL-3.0**). Each source file includes an AGPL-3.0 notice for clarity. See the [LICENSE](LICENSE.txt) file for the full license text.

### Key Points of the AGPL License

- **Network Use**: If you modify and use the software over a network, you must make the source code available to all users who interact with it.
- **Copyleft**: Any modifications or derivative works must also be licensed under the AGPL, ensuring that all changes remain open source.
- **Patent Grant**: Contributors provide an express grant of patent rights, allowing users to freely use the software without concerns over patent claims. 
- **No Sublicensing**: You cannot relicense the code under different terms; the AGPL's provisions must accompany all distributions and modifications.
