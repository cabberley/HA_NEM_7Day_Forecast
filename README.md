<h1 align="center">
  <a href="https://aemo.com.au/"><img src="https://raw.githubusercontent.com/cabberley/HA_NEM_7Day_Forecast/main/ha_aemonem_logo.png" width="480"></a>
  <br>
  <i>AEMO NEM 7 Day Forecast Data Home Assistant Integration</i>
  <br>
  <h3 align="center">
    <i> Custom Home Assistant component for collecting AEMO NEM 7 Day Forecast Data. </i>
    <br>
  </h3>
</h1>

<p align="center">
  <img src="https://img.shields.io/github/v/release/cabberley/HA_NEM_7Day_Forecast?display_name=tag&include_prereleases&sort=semver" alt="Current version">
  <img alt="GitHub" src="https://img.shields.io/github/license/cabberley/HA_NEM_7Day_Forecast"> <img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/cabberley/HA_NEM_7Day_Forecast/hassfest.yml">
  <img alt="GitHub Issues or Pull Requests" src="https://img.shields.io/github/issues/cabberley/HA_NEM_7Day_Forecast"> <img alt="GitHub Downloads (all assets, all releases)" src="https://img.shields.io/github/downloads/cabberley/HA_NEM_7Day_Forecast/total">
 <img alt="GitHub User's stars" src="https://img.shields.io/github/stars/cabberley">

</p>
<p align="center">
    <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg"></a>
</p>
<p align="center">
  <a href="https://www.buymeacoffee.com/cabberley" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
</p>

This integration polls an ftp folder with for the 7 Day PreDispath Forecast for the National Electricity Market (NEM) from the Australian Energy Market Operator (AEMO). Creating a set of sensors for each Region of the market. The initial identification and code to pull out the wanted information used in this integration is courtesy of [Mark Purcell](https://github.com/purcell-lab), Using his suggested code, I have built this custom integration to make it easy for everyone to benefit from Mark's research!

The AEMO NEM 7 day Forecast is normally updated 3 times a day, this integration will check once an hour to see if there is a new file to download and update the sensors from. An Additional sensor is part of the integration to report the file date time that the data has come from and when HA last updated the data.

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cabberley&repository=HA_NEM_7Day_Forecast&category=integration)

To install this Home Assistant Custom Integration, either Click on the open HACS Repository or by manually copying the `custom_components/nem_pd7day` folder into your Home assistant `custom_components` folder.

> [!TIP]
> Don't forget to restart your Home Assistant after adding the integration to your HACS!

## Configuration

After adding the Integration to HACS go to your settings and add the Integration.
Complete the form and submit.

- Give your integration a name or leave the default
- Select which Market Regions you want to monitor

If successful you should now find a device for each market and the current data for it.

# Sensor explanations

The two main sensors state values are the datasets first and next pre dispatch prices and Do not actually reflect the current 5 or 30 minute estimates!

In the attributes for the current sensor you will find the next 7 days of forecast pricing for all future 30min periods as estimated by AEMO NEM.
The attribute structure is similar to other Integrations like Amber Electric and Solcast. Enabling you to generate a comparison set of future time period pricing.
