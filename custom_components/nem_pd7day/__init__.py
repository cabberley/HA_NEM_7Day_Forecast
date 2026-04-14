"""The NEM PD7DAY integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_REGIONS, DEFAULT_REGIONS, DOMAIN, PLATFORMS, REGION_OPTIONS
from .coordinator import NEMPD7DayCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NEM PD7DAY from a config entry."""
    coordinator = NEMPD7DayCoordinator(hass=hass, entry=entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await _async_remove_deselected_regions(hass, entry)
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_remove_deselected_regions(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entities/devices for regions no longer selected."""
    selected_regions = entry.options.get(
        CONF_REGIONS,
        entry.data.get(CONF_REGIONS, DEFAULT_REGIONS),
    )
    selected_regions_lower = {region.lower() for region in selected_regions}

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    stale_regions: set[str] = set()

    prefix = f"{entry.entry_id}_"
    for entity_entry in entries:
        unique_id = entity_entry.unique_id
        if not unique_id.startswith(prefix):
            continue

        remainder = unique_id[len(prefix) :]
        region_key, _, _ = remainder.partition("_")
        if not region_key:
            continue

        if region_key.upper() not in REGION_OPTIONS:
            continue

        if region_key not in selected_regions_lower:
            stale_regions.add(region_key.upper())
            entity_registry.async_remove(entity_entry.entity_id)

    for region in stale_regions:
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, f"{entry.entry_id}_{region}")}
        )
        if device is not None:
            device_registry.async_remove_device(device.id)
