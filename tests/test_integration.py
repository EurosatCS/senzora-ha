"""End-to-end tests against a mocked API."""

from datetime import timedelta

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util

from custom_components.eurosat_meters.const import BASE_URL, DOMAIN

LAST = f"{BASE_URL}/cnt/apiMeterState/lastData"
LIST = f"{BASE_URL}/cnt/apiMeterState/gpsUnitMeterList"
KEY = "123;abcdef"
ROWS = [
    {"gps_unit_id": 155332170, "gps_unit_imei": "2CF7F12050208431", "meter_id": 147520,
     "time": 1794826274, "value": 1897, "probe_id": 0, "probe_sn": "", "measure_unit": "KWh"},
    {"gps_unit_id": 155279527, "gps_unit_imei": "CC0DE70000009DD0", "meter_id": 113855,
     "time": 1794783638, "value": 6.96, "probe_id": 0, "probe_sn": "", "measure_unit": "m3"},
]


async def test_flow_and_sensors(hass, aioclient_mock):
    aioclient_mock.get(LAST, json=ROWS)
    aioclient_mock.get(LIST, json=[{"id": 113855, "title": "Vodoměr sklep"}])

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": KEY})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eurosat 123"
    await hass.async_block_till_done()
    assert aioclient_mock.mock_calls[0][3]["X-API-KEY"] == KEY

    energy = hass.states.get("sensor.eurosat_2cf7f12050208431_meter_147520")
    assert energy.state == "1897"
    assert energy.attributes["unit_of_measurement"] == "kWh"
    assert energy.attributes["device_class"] == "energy"
    assert energy.attributes["state_class"] == "total_increasing"
    assert energy.attributes["measured_at"].startswith("2026-11-1")

    water = hass.states.get("sensor.eurosat_cc0de70000009dd0_vodomer_sklep")
    assert water.state == "6.96"
    assert water.attributes["unit_of_measurement"] == "m³"
    assert water.attributes["device_class"] == "water"

    # second attempt with the same key is rejected
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": KEY})
    assert result["type"] is FlowResultType.ABORT

    # new value + new meter appear on next poll; missing meter goes unavailable
    aioclient_mock.clear_requests()
    aioclient_mock.get(LAST, json=[
        {**ROWS[0], "value": 1900},
        {**ROWS[0], "meter_id": 999, "value": 21.5, "measure_unit": "°C"},
    ])
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=61))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get("sensor.eurosat_2cf7f12050208431_meter_147520").state == "1900"
    assert hass.states.get("sensor.eurosat_2cf7f12050208431_meter_999").attributes["device_class"] == "temperature"
    assert hass.states.get("sensor.eurosat_cc0de70000009dd0_vodomer_sklep").state == "unavailable"


async def test_bad_key(hass, aioclient_mock):
    aioclient_mock.get(LAST, status=401)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "bad"})
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_and_options(hass, aioclient_mock):
    aioclient_mock.get(LAST, status=401)
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": KEY}, unique_id="123_home")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert flows[0]["step_id"] == "reauth_confirm"

    aioclient_mock.clear_requests()
    aioclient_mock.get(LAST, json=ROWS)
    aioclient_mock.get(LIST, status=500)  # labels are best-effort
    result = await hass.config_entries.flow.async_configure(flows[0]["flow_id"], {"api_key": "123;new"})
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.data["api_key"] == "123;new"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 1440})
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval == timedelta(minutes=1440)
