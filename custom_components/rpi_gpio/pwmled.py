"""Allows to configure a pwmled using RPi GPIO."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.fan import PLATFORM_SCHEMA, FanEntity
from homeassistant.const import (
    CONF_NAME,
    CONF_PORT,
    CONF_FANS,
    CONF_UNIQUE_ID,
    DEVICE_DEFAULT_NAME,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.reload import setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .. import DOMAIN, PLATFORMS, setup_pwm, write_pwm

CONF_PULL_MODE = "pull_mode"
CONF_PORTS = "ports"
CONF_INVERT_LOGIC = "invert_logic"

DEFAULT_INVERT_LOGIC = False

_FANS_LEGACY_SCHEMA = vol.Schema({cv.positive_int: cv.string})

_FAN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_PORT): cv.positive_int,
        vol.Optional(CONF_INVERT_LOGIC, default=DEFAULT_INVERT_LOGIC): cv.boolean,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)


PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend(
        {
            vol.Exclusive(CONF_PORTS, CONF_FANS): _FANS_LEGACY_SCHEMA,
            vol.Exclusive(CONF_FANS, CONF_FANS): vol.All(
                cv.ensure_list, [_FAN_SCHEMA]
            ),
            vol.Optional(CONF_INVERT_LOGIC, default=DEFAULT_INVERT_LOGIC): cv.boolean,
        },
    ),
    cv.has_at_least_one_key(CONF_PORTS, CONF_FANS),
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Raspberry PI GPIO devices."""
    setup_reload_service(hass, DOMAIN, PLATFORMS)

    fans = []

    fans_conf = config.get(CONF_FANS)
    if fans_conf is not None:
        for fan in fans_conf:
            fans.append(
                RPiGPIOFan(
                    fan[CONF_NAME],
                    fan[CONF_PORT],
                    fan[CONF_INVERT_LOGIC],
                    fan.get(CONF_UNIQUE_ID),
                )
            )

        add_entities(fans, True)
        return

    invert_logic = config[CONF_INVERT_LOGIC]

    ports = config[CONF_PORTS]
    for port, name in ports.items():
        fans.append(RPiGPIOFan(name, port, invert_logic))

    add_entities(fans)


class RPiGPIOFan(FanEntity):
    """Representation of a  Raspberry Pi GPIO."""

    def __init__(self, name, port, invert_logic, unique_id=None):
        """Initialize the pin."""
        self._attr_name = name or DEVICE_DEFAULT_NAME
        self._attr_unique_id = unique_id
        self._attr_should_poll = False
        self._port = port
        self._invert_logic = invert_logic
        self._state = False
        self._freq = 100 # frequency in Hz
        setup_pwm(self._port)
        write_pwm(self._port, self._freq, 0)

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the device on."""
        write_pwm(self._port, self._freq, 100)
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        write_pwm(self._port, self._freq, 0)
        self._state = False
        self.schedule_update_ha_state()
