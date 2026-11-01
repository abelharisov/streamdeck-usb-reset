#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/IOCFPlugIn.h>
#include <IOKit/usb/IOUSBLib.h>
#include <mach/mach_error.h>
#include <stdio.h>
#include <string.h>

static int number(io_service_t service, CFStringRef key) {
    CFTypeRef value = IORegistryEntryCreateCFProperty(service, key, kCFAllocatorDefault, 0);
    int result = -1;
    if (value && CFGetTypeID(value) == CFNumberGetTypeID())
        CFNumberGetValue(value, kCFNumberIntType, &result);
    if (value) CFRelease(value);
    return result;
}

int main(int argc, char **argv) {
    int reset = argc == 3 && strcmp(argv[1], "--reset") == 0;
    if (!reset && !(argc == 2 && strcmp(argv[1], "--list") == 0)) {
        fprintf(stderr, "Usage: %s --list | --reset SERIAL\n", argv[0]);
        return 2;
    }
    io_iterator_t iterator = 0;
    IOReturn result = IOServiceGetMatchingServices(kIOMainPortDefault,
        IOServiceMatching("IOUSBHostDevice"), &iterator);
    if (result != kIOReturnSuccess) return 1;
    io_service_t target = 0, service;
    int matches = 0;
    while ((service = IOIteratorNext(iterator))) {
        if (number(service, CFSTR("idVendor")) == 0x0fd9 &&
            number(service, CFSTR("idProduct")) == 0x009a) {
            char serial[256] = "";
            CFTypeRef value = IORegistryEntryCreateCFProperty(service,
                CFSTR("USB Serial Number"), kCFAllocatorDefault, 0);
            if (value && CFGetTypeID(value) == CFStringGetTypeID())
                CFStringGetCString(value, serial, sizeof(serial), kCFStringEncodingUTF8);
            if (value) CFRelease(value);
            printf("Stream Deck Neo 0FD9:009A serial=%s location=%08x\n",
                serial, number(service, CFSTR("locationID")));
            if (reset && serial[0] && strcmp(serial, argv[2]) == 0) {
                matches++;
                if (!target) { target = service; IOObjectRetain(target); }
            }
        }
        IOObjectRelease(service);
    }
    IOObjectRelease(iterator);
    if (!reset) return 0;
    if (matches != 1) {
        fprintf(stderr, "Expected exactly one Neo with requested serial; found %d. No reset performed.\n", matches);
        if (target) IOObjectRelease(target);
        return 1;
    }
    IOCFPlugInInterface **plugin = NULL;
    IOUSBDeviceInterface500 **device = NULL;
    SInt32 score = 0;
    result = IOCreatePlugInInterfaceForService(target, kIOUSBDeviceUserClientTypeID,
        kIOCFPlugInInterfaceID, &plugin, &score);
    IOObjectRelease(target);
    if (result != kIOReturnSuccess || !plugin) {
        fprintf(stderr, "Create USB interface: 0x%08x (%s)\n", result, mach_error_string(result));
        return 1;
    }
    HRESULT query = (*plugin)->QueryInterface(plugin,
        CFUUIDGetUUIDBytes(kIOUSBDeviceInterfaceID500), (LPVOID *)&device);
    (*plugin)->Release(plugin);
    if (query || !device) { fprintf(stderr, "QueryInterface failed: %d\n", (int)query); return 1; }
    result = (*device)->USBDeviceOpen(device);
    if (result == kIOReturnSuccess) {
        result = (*device)->USBDeviceReEnumerate(device, 0);
        printf("USBDeviceReEnumerate: 0x%08x (%s)\n", result, mach_error_string(result));
        (*device)->USBDeviceClose(device);
    } else {
        fprintf(stderr, "USBDeviceOpen: 0x%08x (%s). Quit Stream Deck before retrying.\n", result, mach_error_string(result));
    }
    (*device)->Release(device);
    return result == kIOReturnSuccess ? 0 : 1;
}
