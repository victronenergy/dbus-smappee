#!/usr/bin/python -u

import sys, os
import json
import logging
from itertools import groupby, count, izip_longest, izip
from collections import defaultdict
from argparse import ArgumentParser
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'ext', 'velib_python'))

from dbus.mainloop.glib import DBusGMainLoop
import dbus
import gobject
from vedbus import VeDbusService
from settingsdevice import SettingsDevice

from bridge import MqttGObjectBridge

VERSION = '0.1'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# We define these classes to avoid connection sharing to dbus. This is to allow
# more than one service to be held by a single python process.
class SystemBus(dbus.bus.BusConnection):
	def __new__(cls):
		return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SYSTEM)

class SessionBus(dbus.bus.BusConnection):
	def __new__(cls):
		return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SESSION)

def dbusconnection():
    return SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus()

class Meter(object):
    """ Represent a meter object on dbus. """

    def __init__(self, host, base, instance):
        self.instance = instance
        self.service = service = VeDbusService(
            "{}.smappee_{:02d}".format(base, instance), bus=dbusconnection())

        # Add objects required by ve-api
        service.add_path('/Management/ProcessName', __file__)
        service.add_path('/Management/ProcessVersion', VERSION)
        service.add_path('/Management/Connection', host)
        service.add_path('/DeviceInstance', instance)
        service.add_path('/ProductId', 0xFFFF) # 0xB012 ?
        service.add_path('/ProductName', "SMAPPEE current meter")
        service.add_path('/FirmwareVersion', None)
        service.add_path('/Serial', None)
        service.add_path('/Connected', 1)

        service.add_path('/Ac/Energy/Forward', None)
        service.add_path('/Ac/Energy/Reverse', None)
        service.add_path('/Ac/L1/Current', None)
        service.add_path('/Ac/L1/Energy/Forward', None)
        service.add_path('/Ac/L1/Energy/Reverse', None)
        service.add_path('/Ac/L1/Power', None)
        service.add_path('/Ac/L1/Voltage', None)
        service.add_path('/Ac/L2/Current', None)
        service.add_path('/Ac/L2/Energy/Forward', None)
        service.add_path('/Ac/L2/Energy/Reverse', None)
        service.add_path('/Ac/L2/Power', None)
        service.add_path('/Ac/L2/Voltage', None)
        service.add_path('/Ac/L3/Current', None)
        service.add_path('/Ac/L3/Energy/Forward', None)
        service.add_path('/Ac/L3/Energy/Reverse', None)
        service.add_path('/Ac/L3/Power', None)
        service.add_path('/Ac/L3/Voltage', None)
        service.add_path('/Ac/Power', None)

    def set_path(self, path, value):
        if self.service[path] != value:
            self.service[path] = value

class Bridge(MqttGObjectBridge):
    def __init__(self, meters, *args, **kwargs):
        super(Bridge, self).__init__(*args, **kwargs)
        self.meters = meters

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
        except ValueError:
            logger.warning('Malformed payload received')

        # Voltages
        voltages = dict((d['phaseId'], d['voltage']) for d in data['voltages'])

        # Simple solution: Assume the channels make up some kind of
        # 3-phase meter. Group them by phase, sort them by id, then
        # pair them up into meters.
        phases = {i: [] for i in range(3)}
        for phase, channels in groupby(data.get('channelPowers', ()),
                lambda x: x['phaseId']):
            phases[phase].extend(sorted(channels))

        spread = izip_longest(phases[0], phases[1], phases[2])
        for c, phasedata in izip(count(), spread):
            meter = self.meters[c]
            totalpower = totalforward = totalreverse = 0
            for phase in xrange(3):
                d = phasedata[phase]
                if d is not None:
                    # Fill in the values
                    line = '/Ac/L{}'.format(phase+1)
                    meter.set_path('{}/Current'.format(line), d['current'])
                    meter.set_path('{}/Energy/Forward'.format(line), round(d['importEnergy']/3600000, 1))
                    meter.set_path('{}/Energy/Reverse'.format(line), round(d['exportEnergy']/3600000, 1))
                    meter.set_path('{}/Power'.format(line), d['power'])
                    meter.set_path('{}/Voltage'.format(line), voltages.get(phase, None))

                    totalpower += d['power']
                    totalforward += d['importEnergy']
                    totalreverse += d['exportEnergy']

            # Update the totals
            meter.set_path('/Ac/Power', totalpower)
            meter.set_path('/Ac/Energy/Forward', round(totalforward/3600000, 1))
            meter.set_path('/Ac/Energy/Reverse', round(totalreverse/3600000, 1))

        for meter in self.meters.itervalues():
            meter.set_path('/FirmwareVersion', data.get('firmwareVersion'))
            meter.set_path('/Serial', data.get('serialNr'))

    def _on_connect(self, client, userdata, di, rc):
        self._client.subscribe('servicelocation/+/realtime', 0)

def main():
    parser = ArgumentParser(description=sys.argv[0])
    parser.add_argument('--servicebase',
        help='Base service name on dbus, default is com.victronenergy.grid',
        default='com.victronenergy.grid')
    parser.add_argument('host', help='MQTT Host')
    args = parser.parse_args()

    DBusGMainLoop(set_as_default=True)

    # Meters, allocated on demand, device instance is automatically incremented
    metercount = count()
    meters = defaultdict(lambda: Meter(args.host, args.servicebase, metercount.next()))

    # MQTT connection
    bridge = Bridge(meters, args.host)

    mainloop = gobject.MainLoop()
    mainloop.run()

if __name__ == "__main__":
    main()

# TODO
# subscribe to servicelocation/+/realtime
# update other fields when these change
