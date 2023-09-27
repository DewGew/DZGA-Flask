![GitHub release (latest by date)](https://img.shields.io/github/v/release/dewgew/DZGA-Flask?logo=github) [![Discord](https://img.shields.io/discord/664815298284748830?logo=discord)](https://discordapp.com/invite/AmJV6AC) [![Python Package](https://github.com/DewGew/DZGA-Flask/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/DewGew/DZGA-Flask/actions/workflows/python-app.yml)
# DZGA-Flask
Standalone implementation for [Domoticz Home Automation](https://www.domoticz.com/). It means that you can put this server wherever you want, even on another machine. You need to setup a project in Actions on Google Console. You find instructions below.

Required:
- latest Domoticz stable 2023.2 or above.
- public url
- python >= 3.5
- Make local deployment available trough HTTPS with valid certificate with one of below:
  - SSL with own domain or dynamic DNS, require ssl key and ssl certficate
  - Use ngrok for a secure SSL tunnel with valid public HTTPS URL
  - Configure reverse proxy with valid certificate using Let's Encrypt

## Ubuntu, Raspbarry Pi Installation with autostart

Just open a terminal window and execute this command. Thats it!

```
bash <(curl -s https://raw.githubusercontent.com/DewGew/dzga-installer/master/dzgaboard_install.sh)
```