#!/usr/bin/env python


import gobject
import platform
import argparse
import logging
import sys
import os
import dbus
import time

# add the path to our own packages for import
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/velib_python'))
from vedbus import VeDbusService
from settingsdevice import SettingsDevice

GeneratorInputService = "none"
GeneratorService = "none"
GeneratorInputState = None
GeneratorManualStart = None
RunningCondition = None
lastState = 0
dbusGeneratorForwardService = None
searchDelay = 99
lastSyncError = False
syncErrorDelay = 0

# the main loop for this program
# it searchs for a generator digital input and a generator startstop service
# if both are found, the digital input state is passed on to the startstop /ManualStart parameter
#
# /ManualStart is updated only if the digital input is out of sync
# in addition, a manual run is not started if the generator is running due to some automatic run condition
# this prevents a manual run from being piled on to an automatic run.
#
# a stop sync error exists if the generator digital input indicates Stopped
# but Venus wants the generator to be running

def GeneratorInputSyncLoop():

    global GeneratorInputService
    global GeneratorInputState
    global GeneratorService
    global GeneratorManualStart
    global RunningCondition
    global lastState
    global dbusGeneratorForwardService
    global searchDelay
    global lastSyncError
    global syncErrorDelay

    syncError = False

    try:
        TheBus = dbus.SystemBus()
        
        # this little dbus service makes checking for stop sync error in the GUI much easier
        # /StopSyncError flags the condition where a run condition exists but the generator was stopped externally
        if dbusGeneratorForwardService == None:
            logging.info ("Creating forwarding dBus service")
            dbusGeneratorForwardService = VeDbusService("com.victronenergy.generator.Forwarding")
            dbusGeneratorForwardService.add_mandatory_paths(
                processname=__file__,
                processversion=0,
                connection='generator',
                deviceinstance=0,
                productid=None,
                productname=None,
                firmwareversion=None,
                hardwareversion=None,
                connected=0)
            dbusGeneratorForwardService.add_path ('/StopSyncError', value=False)
            dbusGeneratorForwardService.add_path ('/DigitalInputService', value="")
            dbusGeneratorForwardService.add_path ('/GeneratorService', value="")
            dbusGeneratorForwardService.add_path ('/InputState', value=0)
            dbusGeneratorForwardService.add_path ('/ManualStart', value=0)
            dbusGeneratorForwardService.add_path ('/RunningCondition', value=0)
            dbusGeneratorForwardService.add_path ('/ForwardingActive', value=False)

        # search for services every 10 seconds in case there is a change
        if searchDelay > 10:
            newInputService = ""
            newGeneratorService = ""
            for service in TheBus.list_names():
                if service.startswith("com.victronenergy.digitalinput") \
                        and TheBus.get_object(service, '/Type').GetValue() == 9:
                    newInputService = service
                if service.startswith ("com.victronenergy.generator.startstop"):
                    newGeneratorService = service
 
            # update services
            if newInputService != GeneratorInputService:
                GeneratorInputService = newInputService
                dbusGeneratorForwardService['/DigitalInputService'] = GeneratorInputService
                if GeneratorInputService != "":
                    logging.info ("Found generator digital input service at %s", GeneratorInputService)
                else:
                    logging.info ("NO generator digital input service")

            if newGeneratorService != GeneratorService:
                GeneratorService = newGeneratorService
                dbusGeneratorForwardService['/GeneratorService'] = GeneratorService
                if GeneratorService != "":
                    logging.info ("Found generator startstop service at %s", GeneratorService)
                else:
                    logging.info ("NO generator startstop service")

            searchDelay = 0
        else:
            searchDelay += 1

        # get object pointers if services exist
        if GeneratorInputService == "" or GeneratorInputService == "none":
            GeneratorInputState = None
        else:
            GeneratorInputState = TheBus.get_object(GeneratorInputService, '/State')

        if GeneratorService == "" or GeneratorService == "none":
            GeneratorManualStart = None
            RunningCondition = None
        else:
            GeneratorManualStart = TheBus.get_object(GeneratorService, '/Generator0/ManualStart')
            RunningCondition = TheBus.get_object(GeneratorService, '/Generator0/RunningByConditionCode')


        # collect service values
        serviceCount = 0
        if GeneratorInputState != None:
            inputState = GeneratorInputState.GetValue()
            serviceCount += 1
        else:
            inputState = 0
        if GeneratorManualStart != None and RunningCondition != None:
            manualRun = GeneratorManualStart.GetValue()
            runningCondition = RunningCondition.GetValue()
            serviceCount += 1
        else:
            manualRun = 0
            runningCondition = 0

        # update forwarding service values
        dbusGeneratorForwardService['/InputState'] = inputState
        dbusGeneratorForwardService['/ManualStart'] = manualRun
        dbusGeneratorForwardService['/RunningCondition'] = runningCondition

        # both services WERE found - activate forwarding and forward changes if appropriate
        if serviceCount == 2:
            dbusGeneratorForwardService['/ForwardingActive'] = True

            # detect state changes and pass on to generator startstop service
            if inputState != lastState:
                # starting and no conditional run active (runningCondition includes a manual run)
                if inputState == 10 and runningCondition == 0:
                    logging.info ("Forwarding manual start")
                    GeneratorManualStart.SetValue(1)
                # stopping and manual run is active
                elif inputState == 11 and manualRun == 1:
                    logging.info ("Forwarding manual stop")
                    GeneratorManualStart.SetValue(0)

            # set stop sync error flag after a 30 second delay
            # sync error is cleared above and therefore propogares immediately
            if inputState == 11 and runningCondition != 0:
                if syncErrorDelay > 5:
                    syncError = True
                else:
                    syncErrorDelay += 1
            else:
                syncErrorDelay = 0

            if syncError != lastSyncError:
                dbusGeneratorForwardService['/StopSyncError'] = syncError
                if syncError:
                    logging.info ("Stop Sync Error detected")
                else:
                    logging.info ("Stop Sync Error cleared")
                lastSyncError = syncError


        # both services were NOT found - deactivate forwarding
        else:
            dbusGeneratorForwardService['/ForwardingActive'] = False
            dbusGeneratorForwardService['/StopSyncError'] = False
            syncError = False
            lastSyncError = False
            inputState = 0

    except dbus.DBusException:
        logging.info ("dbus exception")
        GeneratorInputService = "none"
        GeneratorService = "none"
        inputState = 0

    lastState = inputState
    return True



def main():

    from dbus.mainloop.glib import DBusGMainLoop

# set logging level to include info level entries
    logging.basicConfig(level=logging.INFO)

# Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    logging.info (">>>>>> Generator digital input forwarding beginning <<<<<<")

# periodically look for SeeLevel service - 1 second (in mS)
    gobject.timeout_add(1000, GeneratorInputSyncLoop)

    mainloop = gobject.MainLoop()
    mainloop.run()

# Always run our main loop so we can process updates
main()
