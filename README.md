# JUDO ZEWA i-SAFE for Home Assistant

Custom Home Assistant integration for JUDO ZEWA i-SAFE / ZEWA i-SAFE FILT devices with the local JUDO REST API.

> Status: initial implementation. It is based on the public JUDO command-line API documentation. Test carefully before using write actions such as closing/opening the leakage protection.

## Features

### Sensors

- Total water volume
- Absence/leakage limits: flow, water amount, extraction duration
- Sleep mode duration
- Learning mode state and remaining learning water
- Installation date, serial number, device type and software version

### Controls

- Open/close leakage protection
- Start/stop sleep mode
- Start/stop vacation mode
- Start micro-leakage test
- Start learning mode
- Reset messages
- Configure absence/leakage limits
- Configure sleep-mode duration
- Configure automatic micro-leakage test mode

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
- Supported device type is `0x44`, used by ZEWA i-SAFE / ZEWA i-SAFE FILT / PROM-i-SAFE according to the JUDO API command document.
- Some commands have immediate physical effect. Validate behavior on the device before using them in automations.

## Manual installation

Copy `custom_components/judo_zewa_isafe` to `<config>/custom_components/judo_zewa_isafe`, restart Home Assistant, then add the integration through the UI.
