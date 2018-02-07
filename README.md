# dbus-smappee

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
The channels published by the smappee are grouped by phase, and then regrouped
by taking a channel from each phase in turn and making up current meters, until
we run out.

The meters are named `com.victronenergy.grid.smappee_XX`, where `XX` is an
integer.

[smappee]: https://www.smappee.com/
