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

from CTFd.models import db
from datetime import datetime


class WebhookLog(db.Model):
    """A database model for logging webhook requests in CTFd.

    This model stores details about webhook requests, including the configuration ID,
    URL, event type, status, response code, error messages, and timestamp. It is used
    to track the history and outcomes of webhook events triggered within the CTFd platform.
    """

    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, nullable=False)
    url = db.Column(db.String(255), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50))
    response_code = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
