# JUDO ZEWA i-SAFE for Home Assistant

Custom Home Assistant integration for JUDO ZEWA i-SAFE / ZEWA i-SAFE FILT / PROM-i-SAFE devices with the local JUDO REST API.

> Status: extended implementation. It is based on the public JUDO command-line API documentation for device type `0x44`. Test carefully before using write actions such as closing/opening the leakage protection or changing leakage limits.

## Features

### Sensors

- Total water volume
- Absence/leakage limits: flow, water amount, extraction duration
- Sleep mode duration
- Learning mode state and remaining learning water
- Device date/time
- Seven programmable absence time periods
- Installation date, serial number, device type and software version

### Binary sensors

- Learning mode active

### Buttons

- Reset messages
- Open/close leakage protection
- Start/stop sleep mode
- Start/stop vacation mode
- Start micro-leakage test
- Start learning mode

### Number entities

- Configure absence/leakage flow limit
- Configure absence/leakage water amount limit
- Configure absence/leakage extraction duration limit
- Configure sleep-mode duration

### Select entities

- Configure automatic micro-leakage test mode
- Configure vacation-mode type (`Aus`, `U1`, `U2`, `U3`)

Note: the JUDO API documents the vacation-mode type as a write command only. The select entity therefore has an optimistic state after Home Assistant writes it, but it cannot read the current value back after a restart.

## Services

The integration registers additional domain services under `judo_zewa_isafe` so that every documented ZEWA i-SAFE FILT command is addressable.

### Write/configuration services

- `judo_zewa_isafe.set_leakage_settings`
  - API command `50`
  - Writes vacation-mode type, max. flow, max. volume and max. duration in one command.
- `judo_zewa_isafe.set_vacation_mode_type`
  - API command `56`
  - Writes `0 = Aus`, `1 = U1`, `2 = U2`, `3 = U3`.
- `judo_zewa_isafe.set_device_datetime`
  - API command `5A`
  - Writes device date/time.
- `judo_zewa_isafe.sync_device_datetime`
  - API command `5A`
  - Writes the current Home Assistant time to the device.
- `judo_zewa_isafe.set_absence_period`
  - API command `61`
  - Writes one absence period `0..6`.
- `judo_zewa_isafe.delete_absence_period`
  - API command `62`
  - Deletes one absence period `0..6`.

### Read/response services

These services return data in the Home Assistant service response.

- `judo_zewa_isafe.get_device_datetime`
  - API command `59`
- `judo_zewa_isafe.get_absence_period`
  - API command `60`
- `judo_zewa_isafe.get_day_statistics`
  - API command `FB`
  - Returns 3-hour buckets in liters.
- `judo_zewa_isafe.get_week_statistics`
  - API command `FC`
  - Returns weekday buckets in liters.
- `judo_zewa_isafe.get_month_statistics`
  - API command `FD`
  - Returns day buckets in liters.
- `judo_zewa_isafe.get_year_statistics`
  - API command `FE`
  - Returns month buckets in liters.

If multiple JUDO devices are configured, pass the optional `config_entry_id` field to a service call. With exactly one configured device, `config_entry_id` can be omitted.

## API command coverage for ZEWA i-SAFE FILT / device type 0x44

| Command | Function | Integration mapping |
| --- | --- | --- |
| `63` | Reset message | Button |
| `51` | Close leakage protection | Button |
| `52` | Open leakage protection | Button |
| `54` | Start sleep mode | Button |
| `55` | Stop sleep mode | Button |
| `57` | Start vacation mode | Button |
| `58` | Stop vacation mode | Button |
| `5C` | Start micro-leakage test | Button |
| `5D` | Start learning mode | Button |
| `5E` | Read absence limits | Sensors + number entities |
| `50` | Write leakage settings | Service |
| `53` | Write sleep duration | Number entity |
| `66` | Read sleep duration | Sensor + number entity |
| `56` | Write vacation-mode type | Select + service |
| `64` | Read learning-mode status | Binary sensor + sensor |
| `65` | Read micro-leakage mode | Select |
| `59` | Read device date/time | Sensor + service |
| `5A` | Write device date/time | Services |
| `5B` | Set micro-leakage mode | Select |
| `5F` | Write absence limits | Number entities |
| `60` | Read absence period | Sensors + service |
| `61` | Write absence period | Service |
| `62` | Delete absence period | Service |
| `FF` | Read device type | Device info + sensor |
| `06` | Read serial number | Device info + sensor |
| `01` | Read software version | Device info + sensor |
| `0E` | Read commissioning date | Sensor |
| `28` | Read total water volume | Sensor |
| `FB` | Day statistics | Service |
| `FC` | Week statistics | Service |
| `FD` | Month statistics | Service |
| `FE` | Year statistics | Service |

## Installation via HACS custom repository

1. Push this repository to GitHub.
2. In Home Assistant, open **HACS**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add your GitHub repository URL.
5. Select category **Integration**.
6. Install **JUDO ZEWA i-SAFE**.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration → JUDO ZEWA i-SAFE**.

## Configuration

The config flow asks for:

- Host/IP address of the JUDO device
- Port, default `80`
- Username, commonly `admin` on the connectivity module
- Password, commonly `Connectivity` unless changed
- Scan interval, default `60` seconds, minimum `30` seconds

## Notes

- Communication is local over `http://<device>:<port>/api/rest/<command>`.
- Supported device type is `0x44`, used by ZEWA i-SAFE / ZEWA i-SAFE FILT / PROM-i-SAFE according to the JUDO API command document. The previous package also keeps `0x68` in the supported list for compatibility.
- Some commands have immediate physical effect. Validate behavior on the device before using them in automations.
- Statistics are exposed as response services rather than permanent entities because they are queried for an arbitrary date/week/month/year.

## Manual installation

Copy `custom_components/judo_zewa_isafe` to `<config>/custom_components/judo_zewa_isafe`, restart Home Assistant, then add the integration through the UI.


## Version 0.2.1

- Behebt das Laden des Config Flows, indem optionale Service-Response-Imports aus dem Paketimport entfernt und die externe `async_timeout`-Abhängigkeit durch `asyncio.timeout` ersetzt wurde.


## Branding / Logo

Diese Integration enthält lokale Brand-Assets im Ordner `custom_components/judo_zewa_isafe/brand/`.
Das Brand-Set ist produktbezogen gestaltet: JUDO-Herstellerlogo plus `ZEWA i-SAFE FILT`-Kennzeichnung, jeweils als Light-/Dark-Variante und als normale/@2x-Auflösung.
Ab Home Assistant 2026.3 werden diese lokalen Brand-Bilder direkt für die Integrationsdarstellung verwendet.
