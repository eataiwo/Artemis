#!/usr/bin/env python

"""
==================================================
Project: ARTEMIS
Author: TJ Taiwo
Description: Script to interface with the nanotec motor controller C5-E-1-11.
Projects referenced/used:
NanoLib - https://en.nanotec.com/products/9985-nanolib-software-integration-for-motor-controllers
==================================================
Notes:

==================================================
"""

"""
From NanoLib-Python_User_Manual 7.1

A typical workflow looks like this:
1. Start by scanning for hardware with NanoLibAccessor.listAvailableBusHardware ().
2. Set the communication settings with BusHardwareOptions ().
3. Open the hardware connection with NanoLibAccessor.openBusHardwareWithProtocol ().
4. Scan the bus for connected devices with NanoLibAccessor.scanDevices ().
5. Add a device with NanoLibAccessor.addDevice ().
6. Connect to the device with NanoLibAccessor.connectDevice ().
7. After finishing the operation, disconnect the device with NanoLibAccessor.disconnectDevice ().
8. Remove the device with NanoLibAccessor.removeDevice ().
9. Close the hardware connection with NanoLibAccessor.closeBusHardware ().
10.Familiarize yourself with the class's following public member functions:
"""

from nanotec_nanolib import Nanolib
from time import sleep
import struct


class ScanBusCallback(Nanolib.NlcScanBusCallback):  # override super class
    def __init__(self):
        super().__init__()

    def callback(self, info, devicesFound, data):
        if info == Nanolib.BusScanInfo_Start:
            print('Scanning bus.')
        elif info == Nanolib.BusScanInfo_Progress:
            if (data & 1) == 0:
                print('.', end='', flush=True)
        elif info == Nanolib.BusScanInfo_Finished:
            print('\nScan finished.')

        return Nanolib.ResultVoid()


callbackScanBus = ScanBusCallback()


# I will refactor this in a separate script later
class NanoLibController:
    """
    A class used to control the Nanolib C5-E-1-11 motor controller.

    Attributes
    ----------
    nanolib_accessor : Nanolib.NanoLibAccessor
        A pointer to the nanolib accessor in the nanolib

    """

    def __init__(self):
        """Creates and stores the nanolib accessor.

        Note: call this function before calling another function
        """
        self.nanolib_accessor: Nanolib.NanoLibAccessor = Nanolib.getNanoLibAccessor()

    def setup(self):
        # Set logging level
        self.set_logging_level(Nanolib.LogLevel_Info)

    def set_logging_level(self, log_level):
        """Set the logging level

        Parameters
        ----------
        log_level
            The log level, can be
            - LogLevel_Off
            - LogLevel_Trace
            - LogLevel_Debug
            - LogLevel_Info (default)
            - LogLevel_Warn
            - LogLevel_Error
        """
        if (self.nanolib_accessor is None):
            raise Exception('Error: NanolibHelper().setup() is required')

        self.nanolib_accessor.setLoggingLevel(log_level)

    def get_bus_hardware(self):
        """Get a list of available bus hardware.

        Note: only supported bus hardware is taken into account.

        Returns
        -------
        list
            a list of Nanolib.BusHardwareId found
        """

        bus_hardware = self.nanolib_accessor.listAvailableBusHardware()

        if bus_hardware.hasError():
            raise Exception('Error: listAvailableBusHardware() - ' + bus_hardware.getError())

        elif bus_hardware.getResult().empty():
            raise Exception('No bus hardware found.')

        else:
            print('\nAvailable bus hardware:\n')

            line_num = 0
            # just for better overview: print out available hardware
            for bus_hardware_id in bus_hardware.getResult():
                print('{}. {} with protocol: {}'.format(line_num, bus_hardware_id.getName(),
                                                        bus_hardware_id.getProtocol()))
                if bus_hardware_id.getName() == 'Nanotec VCP':
                    self.nanotec_vcp = line_num
                line_num += 1

        return bus_hardware.getResult()

    @staticmethod
    def select_bus(bus_hardwares):
        i = 0
        nanotec_vcp = ''
        # just for better overview: print out available hardware
        for bus_hardware in bus_hardwares:
            if 'Nanotec VCP' in bus_hardware.getName():
                nanotec_vcp = i
            i += 1

        if nanotec_vcp == '':
            raise Exception('No USB Nanotec Controller Found')
        return nanotec_vcp

    @staticmethod
    def bus_hardware_options(bus_hw_id: Nanolib.BusHardwareId):
        """Create bus hardware options object.

        Returns
        ----------
        bus_hardware_option : Nanolib.BusHardwareOptions
             A set of options for opening the bus hardware
        """

        bus_hardware_option = Nanolib.BusHardwareOptions()

        # now add all options necessary for opening the bus hardware
        if bus_hw_id.getProtocol() == Nanolib.BUS_HARDWARE_ID_PROTOCOL_CANOPEN:
            # in case of CAN bus it is the baud rate
            bus_hardware_option.addOption(
                Nanolib.CanBus().BAUD_RATE_OPTIONS_NAME,
                Nanolib.CanBaudRate().BAUD_RATE_1000K
            )

            if (bus_hw_id.getBusHardware() == Nanolib.BUS_HARDWARE_ID_IXXAT):
                # in case of HMS IXXAT we need also bus number
                bus_hardware_option.addOption(
                    Nanolib.Ixxat().ADAPTER_BUS_NUMBER_OPTIONS_NAME,
                    Nanolib.IxxatAdapterBusNumber().BUS_NUMBER_0_DEFAULT
                )
            print(
                '\nSelected bus hardware is  {} with protocol: {}'.format(bus_hw_id.getName(), bus_hw_id.getProtocol()))

        elif bus_hw_id.getProtocol() == Nanolib.BUS_HARDWARE_ID_PROTOCOL_MODBUS_RTU:
            # in case of Modbus RTU it is the serial baud rate
            bus_hardware_option.addOption(
                Nanolib.Serial().BAUD_RATE_OPTIONS_NAME,
                Nanolib.SerialBaudRate().BAUD_RATE_19200
            )
            # and serial parity
            bus_hardware_option.addOption(
                Nanolib.Serial().PARITY_OPTIONS_NAME,
                Nanolib.SerialParity().EVEN
            )

            print(
                '\nSelected bus hardware is  {} with protocol: {}'.format(bus_hw_id.getName(), bus_hw_id.getProtocol()))

        elif ((bus_hw_id.getProtocol() == Nanolib.BUS_HARDWARE_ID_PROTOCOL_MODBUS_VCP) or
              (bus_hw_id.getProtocol() == Nanolib.BUS_HARDWARE_ID_PROTOCOL_MODBUS_TCP)):
            # in case of Modbus VCP/TCP, nothing is needed
            print(
                '\nSelected bus hardware is  {} with protocol: {}'.format(bus_hw_id.getName(), bus_hw_id.getProtocol()))
        else:
            raise Exception('Error: unknown protocol')

        return bus_hardware_option

    def open_bus_hardware(self, bus_hw_id: Nanolib.BusHardwareId, bus_hw_options: Nanolib.BusHardwareOptions):
        """Opens the bus hardware with given id and options.

        Parameters
        ----------
        bus_hw_id : Nanolib.BusHardwareId
            The bus hardware Id taken from function NanoLibHelper.get_bus_hardware()
        bus_hw_options : Nanolib.BusHardwareOptions
            The hardware options taken from NanoLibHelper.create_bus_hardware_options()
        """
        result = self.nanolib_accessor.openBusHardwareWithProtocol(bus_hw_id, bus_hw_options)

        if (result.hasError()):
            raise Exception('Error: openBusHardwareWithProtocol() - ' + result.getError())

    def close_bus_hardware(self, bus_hw_id: Nanolib.BusHardwareId):
        """Closes the bus hardware (access no longer possible after that).

        Note: the call of the function is optional because the nanolib will cleanup the
        bus hardware itself on closing.

        Parameters
        ----------
        bus_hw_id : Nanolib.BusHardwareId
            The bus hardware Id taken from function NanoLibHelper.get_bus_hardware()
        """
        result = self.nanolib_accessor.closeBusHardware(bus_hw_id)

        if (result.hasError()):
            raise Exception('Error: closeBusHardware() - ' + result.getError())

    def scan_bus(self, bus_hw_id: Nanolib.BusHardwareId):
        """Scans bus and returns all found device ids.

        CAUTION: open bus hardware first with NanoLibHelper.open_bus_hardware()

        Note: this functionality is not available on all bus hardwares. It is assumed that
        this example runs with CANopen where the scan is possible.

        Parameters
        ----------
        bus_hw_id : Nanolib.BusHardwareId
            The bus hardware to scan

        Returns
        ----------
        list : Nanolib.DeviceId
            List with found devices
        """
        result = self.nanolib_accessor.scanDevices(bus_hw_id, callbackScanBus)

        if result.hasError():
            raise Exception('Error: scanDevices() - ' + result.getError())

        if result.getResult().size() == 0:
            raise Exception('No devices found.')

        print("Found Device: {}".format(result.getResult()[0].toString()))

        return result.getResult()

    def create_device(self, device_id: Nanolib.DeviceId):
        """Create a Nanolib device from given device id.

        Parameters
        ----------
        device_id : Nanolib.DeviceId
            The bus device id

        Returns
        ----------
        device_handle : Nanolib.DeviceHandle
        """
        device_handle = self.nanolib_accessor.addDevice(device_id).getResult()

        return device_handle

    def connect_device(self, device_handle: Nanolib.DeviceHandle):
        """Connects Device with given device handle.

        Parameters
        ----------
        device_handle : Nanolib.DeviceHandle
            The device handle of the device connect to
        """
        result = self.nanolib_accessor.connectDevice(device_handle)
        print('Now connected')

        if (result.hasError()):
            raise Exception('Error: connectDevice() - ' + result.getError())

    def disconnect_device(self, device_handle: Nanolib.DeviceHandle):
        """Disconnects Device with given device handle.

        Note: the call of the function is optional because the Nanolib will cleanup the
        devices on bus itself on closing.

        Parameters
        ----------
        device_handle : Nanolib.DeviceHandle
            The device handle of the device disconnect from
        """
        result = self.nanolib_accessor.disconnectDevice(device_handle)

        if (result.hasError()):
            raise Exception('Error: disconnectDevice() - ' + result.getError())

    def read_number(self, device_handle: Nanolib.DeviceHandle, od_index: Nanolib.OdIndex):
        """Reads out a number from given device

        Note: the interpretation of the data type is up to the user.

        Parameters
        ----------
        device_handle : Nanolib.DeviceHandle
            The handle of the device to read from
        od_index : Nanolib.OdIndex
            The index and sub-index of the object dictionary to read from

        Returns
        ----------
        int
            The number read from the device
        """
        result = self.nanolib_accessor.readNumber(device_handle, od_index)

        if (result.hasError()):
            raise Exception(self.create_error_message('read_number', device_handle, od_index, result.getError()))

        return result.getResult()

    def write_number(self, device_handle: Nanolib.DeviceHandle, value, od_index: Nanolib.OdIndex, bit_length):
        """Writes given value to the device.

        Parameters
        ----------
        device_handle: Nanolib.DeviceHandle
            The handle of the device to write to
        value : int
            The value to write to the device
        od_index: Nanolib.OdIndex
            The index and sub-index of the object dictionary to write to
        bit_length : int
            The bit length of the object to write to, either 8, 16 or 32
            (see manual for all the bit lengths of all objects)
        """
        result = self.nanolib_accessor.writeNumber(device_handle, value, od_index, bit_length)

        if (result.hasError()):
            raise Exception(self.create_error_message('write_number', device_handle, od_index, result.getError()))

    def read_array(self, device_handle: Nanolib.DeviceHandle, od_index: Nanolib.OdIndex):
        """Reads out an od object array.

        Note: the interpretation of the data type is up to the user. Signed integer
        are interpreted as unsigned integer.

        Parameters
        ----------
        device_handle: Nanolib.DeviceHandle
            The handle of the device to read from
        od_index: Nanolib.OdIndex
            The index and sub-index of the object dictionary to read from

        Returns
        ----------
        list : int
            List of ints
        """
        result = self.nanolib_accessor.readNumberArray(device_handle, od_index.getIndex())

        if (result.hasError()):
            raise Exception(
                self.create_error_message('Error: cannot read array', device_handle, od_index, result.getError()))

        return result.getResult()

    def read_string(self, device_handle: Nanolib.DeviceHandle, od_index: Nanolib.OdIndex):
        """Reads out string from device

        Parameters
        ----------
        device_handle: Nanolib.DeviceHandle
            The handle of the device to read from
        od_index: Nanolib.OdIndex
            The index and sub-index of the object dictionary to read from

        Returns
        ----------
        str
            The read out string
        """
        result = self.nanolib_accessor.readString(device_handle, od_index)

        if (result.hasError()):
            raise Exception(
                self.create_error_message('Error: cannot read string', device_handle, od_index, result.getError()))

        return result.getResult()

    @staticmethod
    def decode_status(status_word):
        state = {"Not ready to switch on": [0, 16, 32, 48, 128, 160, 144, 176],
                 "Switch on disabled": [64, 80, 96, 112, 192, 208, 224, 240],
                 "Ready to switch on": [33, 49, 161, 177],
                 "Switched on": [35, 51, 163, 179],
                 "Operation Enabled": [39, 55, 167, 183],
                 "Quick stop active": [7, 23, 135, 151],
                 "Fault reaction active": [15, 31, 47, 63, 143, 159, 175, 191],
                 "Fault": [8, 24, 40, 56, 136, 152, 168, 184]
                 }

        filter = 0b0000000011111111
        status_word &= filter

        if status_word in state["Not ready to switch on"]:
            result = "Not ready to switch on"
        elif status_word in state["Switch on disabled"]:
            result = "Switch on disabled"
        elif status_word in state["Ready to switch on"]:
            result = "Ready to switch on"
        elif status_word in state["Switched on"]:
            result = "Switched on"
        elif status_word in state["Operation Enabled"]:
            result = "Operation Enabled"
        elif status_word in state["Quick stop active"]:
            result = "Quick stop active"
        elif status_word in state["Fault reaction active"]:
            result = "Fault reaction active"
        elif status_word in state["Fault"]:
            result = "Fault"
        else:
            result = "Cannot determine controller state"
        return result

    @staticmethod
    def decode_mode(mode):
        if mode == -2:
            result = "Auto setup"
        elif mode == -1:
            result = "Clock-direction mode"
        elif mode == 0:
            result = "No mode change/no mode assigned"
        elif mode == 1:
            result = "Profile Position Mode"
        elif mode == 2:
            result = "Velocity Mode"
        elif mode == 3:
            result = "Profile Velocity Mode"
        elif mode == 4:
            result = "Profile Torque Mode"
        elif mode == 5:
            result = "Reserved"
        elif mode == 6:
            result = "Homing Mode"
        else:
            result = "Error not able to determine mode"

        return result


if __name__ == '__main__':
    motorControl = NanoLibController()
    motorControl.setup()
    bus_hardware_ids = motorControl.get_bus_hardware()
    bus_id = motorControl.select_bus(bus_hardware_ids)
    bus_hw_options = motorControl.bus_hardware_options(bus_hardware_ids[bus_id])

    motorControl.open_bus_hardware(bus_hardware_ids[bus_id], bus_hw_options)
    device_ids = motorControl.scan_bus(bus_hardware_ids[bus_id])

    # I am expecting the only device to be the nanotec controller
    device_handle = motorControl.create_device(device_ids[0])

    motorControl.connect_device(device_handle)

    # add all the interesting stuff
    # status_num = motorControl.read_number(device_handle, Nanolib.OdIndex(0x3202, 0x00))

    status_word = motorControl.read_number(device_handle, Nanolib.OdIndex(0x6041, 0x00))
    state = motorControl.decode_status(status_word)

    # print(f"{status_num:b}")
    # print(f"{status_word:b}")
    # print(status_word)

    print(f"\nCurrent controller state: {state}")

    # Set profile position mode
    motorControl.write_number(device_handle, 1, Nanolib.OdIndex(0x6060, 0x00), 8)
    mode = motorControl.read_number(device_handle, Nanolib.OdIndex(0x6061, 0x00))
    mode = motorControl.decode_mode(mode)
    print(f"Controller mode: {mode}")

    control_word = motorControl.read_number(device_handle, Nanolib.OdIndex(0x6040, 0x00))
    print(control_word)
    print(f"{control_word:b}")

    motorControl.write_number(device_handle, 6, Nanolib.OdIndex(0x6040, 0x00), 16)
    sleep(2)
    motorControl.write_number(device_handle, 7, Nanolib.OdIndex(0x6040, 0x00), 16)
    sleep(2)
    motorControl.write_number(device_handle, 15, Nanolib.OdIndex(0x6040, 0x00), 16)

    control_word = motorControl.read_number(device_handle, Nanolib.OdIndex(0x6040, 0x00))
    print(control_word)
    print(f"{control_word:b}")
    status_word = motorControl.read_number(device_handle, Nanolib.OdIndex(0x6041, 0x00))
    print(f"{status_word:b}")
    state = motorControl.decode_status(status_word)
    print(f"\nCurrent controller state: {state}")
    # motorControl.write_number(device_handle, 0, Nanolib.OdIndex(0x607A, 0x00), 32)
    # sleep(0.5)
    # motorControl.write_number(device_handle, 31, Nanolib.OdIndex(0x6040, 0x00), 16)
    # motorControl.write_number(device_handle, 15, Nanolib.OdIndex(0x6040, 0x00), 16)
    # sleep(0.5)
    # motorControl.write_number(device_handle, 1000, Nanolib.OdIndex(0x607A, 0x00), 32)
    # motorControl.write_number(device_handle, 31, Nanolib.OdIndex(0x6040, 0x00), 16)
    # motorControl.write_number(device_handle, 15, Nanolib.OdIndex(0x6040, 0x00), 16)
    # sleep(0.5)
    # motorControl.write_number(device_handle, 0, Nanolib.OdIndex(0x607A, 0x00), 32)
    # motorControl.write_number(device_handle, 31, Nanolib.OdIndex(0x6040, 0x00), 16)
    # motorControl.write_number(device_handle, 15, Nanolib.OdIndex(0x6040, 0x00), 16)

    count = 1
    for x in range(4):
        motorControl.write_number(device_handle, 1000, Nanolib.OdIndex(0x607A, 0x00), 32)
        motorControl.write_number(device_handle, 0b11111, Nanolib.OdIndex(0x6040, 0x00), 16)
        motorControl.write_number(device_handle, 0b1111, Nanolib.OdIndex(0x6040, 0x00), 16)
        sleep(2)
        motorControl.write_number(device_handle, 0, Nanolib.OdIndex(0x607A, 0x00), 32)
        motorControl.write_number(device_handle, 0b11111, Nanolib.OdIndex(0x6040, 0x00), 16)
        motorControl.write_number(device_handle, 0b1111, Nanolib.OdIndex(0x6040, 0x00), 16)
        sleep(2)
        print(count)
        count += 1

    ''' Psedocode
    Check status 
    Set mode to profile position
    Set the parameters for profile position
        - Position mode 6040:00 bit 6 
        - Move command 6040:00 bit 5 and 9
        - Home offset 607C:00
        - Min position range limit 607B:01
        - Max position range limit 607B:02
        - Min position limit 607D:01
        - Max position limit 607D:02
        - Polarity  607E:00 bit 7
        - Motion profile type 6086:00
        - Profile velocity 6081:00
        - Profile acceleration 6083:00
        - Max acceleration 60C5:00
        - End velocity 6082:00
        - Profile deceleration 6084:00
        - Quick stop deceleration 6085:00
        - Max deceleration 60C6:00
        - Position window 6067:00
        - Position window time 6068:00
        - Following error window 6065:00
        - Follow error time out 6066:00
    Check all values were set correctly
    Activate Mode or Set "operation enabled" to see if that works
    Check status 
    Set new target position 607A:00
    Trigger new set point - set bit 4 in controlword ( Apparently if bit 4 is set to 1 and kept there the motor should move automatically, test this out) 
    Check status and check
        - Position actual value 6064:00
        - Target reached 6041:00
        - Set-point acknowledge 6041:00 bit 12
        - Following error 6041:00 bit 13
    
    
    
    '''
    motorControl.disconnect_device(device_handle)
    motorControl.close_bus_hardware(bus_hardware_ids[bus_id])
