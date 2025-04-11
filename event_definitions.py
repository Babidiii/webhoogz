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

from CTFd.models import Users, Challenges, Teams
from CTFd.utils.scores import get_standings
from CTFd.utils import get_app_config
from datetime import datetime

from .events import event_registry


@event_registry.event(
    "challenge_created",
    "Challenge Created",
    "Triggered when a new challenge is created.",
    {"challenge": "BOF 1", "category": "pwn", "value": 100},
)
def generate_challenge_created_payload(challenge):
    return {
        "challenge": challenge.name,
        "category": challenge.category,
        "value": int(challenge.value),
    }


@event_registry.event(
    "firstblood",
    "First Blood",
    "Triggered when a challenge is solved for the first time.",
    {
        "category": "string",
        "username": "string",
        "challenge": "string",
        "timestamp": "string (ISO)",
    },
)
def generate_firstblood_payload(solve):
    user = Users.query.filter_by(id=solve.user_id).first()
    challenge = Challenges.query.filter_by(id=solve.challenge_id).first()
    return {
        "category": challenge.category,
        "username": user.name,
        "challenge": challenge.name,
        "timestamp": solve.date.isoformat(),
    }


@event_registry.event(
    "challenge_solved",
    "Challenge Solved",
    "Triggered when any challenge is solved.",
    {
        "category": "string",
        "username": "string",
        "challenge": "string",
        "timestamp": "string (ISO)",
    },
)
def generate_challenge_solved_payload(solve):
    user = Users.query.filter_by(id=solve.user_id).first()
    challenge = Challenges.query.filter_by(id=solve.challenge_id).first()
    return {
        "category": challenge.category,
        "username": user.name,
        "challenge": challenge.name,
        "timestamp": solve.date.isoformat(),
    }


@event_registry.event(
    "ctf_started", "CTF Started", "Triggered when the CTF begins.", {"status": "string"}
)
def generate_ctf_started_payload():
    return {"status": "The CTF has begun!"}


@event_registry.event(
    "scoreboard_update",
    "Scoreboard Update",
    "Triggered when the scoreboard changes (debounced every 5 mins).",
    {
        "timestamp": "string (ISO)",
        "total_teams": 50,
        "total_users": 100,
        "top_teams": [],
        "top_users": [],
    },
)
def generate_scoreboard_update_payload(user_id=None, team_id=None):
    timestamp = datetime.utcnow().isoformat()
    total_teams = Teams.query.count()
    total_users = Users.query.count()
    standings = get_standings(count=5)
    if get_app_config("TEAMS"):
        team_scores = [
            {
                "rank": i + 1,
                "team_id": int(entry.account_id),
                "team_name": entry.name,
                "score": int(entry.score),
            }
            for i, entry in enumerate(standings)
        ]
        top_users = []
    else:
        team_scores = []
        top_users = [
            {
                "rank": i + 1,
                "user_id": int(entry.account_id),
                "username": entry.name,
                "score": int(entry.score),
            }
            for i, entry in enumerate(standings)
        ]
    return {
        "timestamp": timestamp,
        "total_teams": total_teams,
        "total_users": total_users,
        "top_teams": team_scores,
        "top_users": top_users,
    }


@event_registry.event(
    "team_created",
    "Team Created",
    "Triggered when a new team is created.",
    {"team_name": "string", "timestamp": "string (ISO)"},
)
def generate_team_created_payload(team):
    return {"team_name": team.name, "timestamp": team.created.isoformat()}
