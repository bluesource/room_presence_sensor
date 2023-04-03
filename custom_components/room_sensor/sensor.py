import logging
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle, dt
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_RESOURCE,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_USERNAME,
    EntityCategory,
)
from homeassistant.components.sensor import PLATFORM_SCHEMA

import voluptuous as vol
from datetime import datetime, timedelta
from exchangelib import (
    Credentials,
    Account,
    EWSDateTime,
    DELEGATE,
    Configuration,
    EWSDate,
)

_LOGGER = logging.getLogger(__name__)

CONF_CALENDARS = "calendars"
CONF_SERVER = "server"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        # pylint: disable=no-value-for-parameter
        vol.Required(CONF_SERVER): cv.string,
        vol.Inclusive(CONF_USERNAME, "authentication"): cv.string,
        vol.Inclusive(CONF_PASSWORD, "authentication"): cv.string,
        vol.Optional(CONF_CALENDARS, default=[]): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_EMAIL): cv.string,
                    }
                )
            ],
        ),
    }
)


def setup_platform(hass, config, add_devices, disc_info=None):
    """Set up the  sensor."""
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    server = config.get(CONF_SERVER)

    credentials = Credentials(username=username, password=password)

    devices = []

    # Create additional calendars based on custom filtering rules
    for cust_calendar in config[CONF_CALENDARS]:
        email = cust_calendar[CONF_EMAIL]

        config = Configuration(server=server, credentials=credentials)

        account = Account(
            primary_smtp_address=email,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )

        device_id = email
        devices.append(RoomPresenceSensor(email, device_id, account))

    add_devices(devices, True)


MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)


class RoomPresenceSensor(SensorEntity):
    """Representation of a presence sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["free", "normal", "high"]
    _entity_category = (EntityCategory.DIAGNOSTIC,)

    def __init__(self, name, resource, acount):
        """Initialize the sensor."""
        self._name = name
        self.account = acount
        self._resource = resource
        self._state = "free"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if the sensor is on."""
        return self._state != "free"

    def update(self):
        """Get the latest data from the REST API."""
        try:
            server_tz = self.account.default_timezone

            start = EWSDate.today()

            end = start + timedelta(days=1)

            appointments = self.account.calendar.filter(start__range=(start, end))

            today = EWSDateTime.now(tz=server_tz)

            found_appointment_with_prio = "free"
            for item in appointments:
                if item.start <= today <= item.end:
                    # _LOGGER.debug(
                    #     "Found calender item in which is active now: "
                    #     + item.subject
                    #     + "starts: "
                    #     + item.start
                    #     + " ends: "
                    #     + item.end
                    # )
                    if item.importance == "High":
                        found_appointment_with_prio = "high"
                    else:
                        found_appointment_with_prio = "normal"

            self._attr_native_value = found_appointment_with_prio

        except:
            _LOGGER.error("Error fetching data")


# serien teste mit löschen, anders licht mi importance High
