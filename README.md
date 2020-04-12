# dbus-smappee

NOTE: this project was never fully completed.

This application reads data published by your [SMAPPEE][smappee] energy monitor
from MQTT and turns it into a grid meter service on dbus. This allows
Venus to use your [SMAPPEE][smappee] as a grid meter.

## Running

    git clone git@github.com:izak/dbus-smappee.git
    cd dbus-smappee
    git submodule update --init
    python dbus_smappee.py 127.0.0.1

## How it works

The configuration of the sensors determines how many meters or phases you get.
The channels published by the smappee are grouped by channelType and phase, and
then regrouped by taking a channel from each phase in turn and making up
current meters, until we run out.

Only one meter is allocated from CONSUMPTION channels. This becomes a grid
meter. The first matching CT (or CTs where more than one phase is
defined) becomes the grid meter.

All channels of type PRODUCTION are striped across phases and turned into
current meters. This is done in numeric order.

The grid meter is named `com.victronenergy.grid.smappee_XX`, where `XX` is an
integer. The other meters (of the PRODUCTION type) are named
`com.victronenergy.pvinverter.smappee_XX`.

[smappee]: https://www.smappee.com/
