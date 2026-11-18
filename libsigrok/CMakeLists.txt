cmake_minimum_required(VERSION 3.10)
project(libsigrok C)

include(GNUInstallDirs)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

option(DISABLE_WERROR "Build without -Werror" TRUE)
if(NOT DISABLE_WERROR)
    add_compile_options(-Werror)
endif()

# ============================================================================
# Dependencies
# ============================================================================
find_package(PkgConfig REQUIRED)

# glib-2.0 is mandatory.
pkg_check_modules(GLIB REQUIRED glib-2.0>=2.32.0)

# Optional libraries used by the hardware drivers and I/O modules.
pkg_check_modules(LIBUSB libusb-1.0>=1.0.16)
pkg_check_modules(LIBSERIALPORT libserialport>=0.1.1)
pkg_check_modules(LIBZIP libzip>=0.10)
pkg_check_modules(LIBFTDI libftdi1>=1.0)
pkg_check_modules(LIBGIO gio-2.0>=2.32.0)
pkg_check_modules(NETTLE nettle)
pkg_check_modules(ZLIB zlib)
pkg_check_modules(BLUEZ bluez)
pkg_check_modules(HIDAPI hidapi)
if(NOT HIDAPI_FOUND)
    pkg_check_modules(HIDAPI hidapi-hidraw)
endif()
if(NOT HIDAPI_FOUND)
    pkg_check_modules(HIDAPI hidapi-libusb)
endif()

find_path(IEEE1284_INCLUDE_DIR ieee1284.h)
find_library(IEEE1284_LIBRARY NAMES ieee1284)

# Windows/MinGW system libraries.
if(WIN32 OR MINGW)
    set(PLATFORM_LIBS ws2_32 setupapi ole32)
else()
    set(PLATFORM_LIBS m pthread dl)
endif()

# ============================================================================
# config.h generation helpers
# ============================================================================
include(CheckSymbolExists)
include(CheckIncludeFile)

check_include_file(dlfcn.h HAVE_DLFCN_H)
check_include_file(sys/mman.h HAVE_SYS_MMAN_H)
check_include_file(sys/ioctl.h HAVE_SYS_IOCTL_H)
check_include_file(sys/timerfd.h HAVE_SYS_TIMERFD_H)
check_include_file(fcntl.h HAVE_FCNTL_H)
check_include_file(unistd.h HAVE_UNISTD_H)
check_include_file(stdint.h HAVE_STDINT_H)
check_include_file(inttypes.h HAVE_INTTYPES_H)
check_include_file(sys/stat.h HAVE_SYS_STAT_H)
check_include_file(sys/types.h HAVE_SYS_TYPES_H)
check_include_file(strings.h HAVE_STRINGS_H)
check_include_file(poll.h HAVE_POLL_H)
check_include_file(sys/select.h HAVE_SELECT_H)

check_symbol_exists(strcasecmp "strings.h" HAVE_STRCASECMP)
check_symbol_exists(strncasecmp "strings.h" HAVE_STRNCASECMP)

if(LIBZIP_FOUND)
    set(CMAKE_REQUIRED_INCLUDES ${LIBZIP_INCLUDE_DIRS})
    set(CMAKE_REQUIRED_LIBRARIES ${LIBZIP_LIBRARIES})
    check_symbol_exists(zip_discard "zip.h" HAVE_ZIP_DISCARD)
endif()
if(LIBUSB_FOUND)
    set(CMAKE_REQUIRED_INCLUDES ${LIBUSB_INCLUDE_DIRS})
    set(CMAKE_REQUIRED_LIBRARIES ${LIBUSB_LIBRARIES})
    check_symbol_exists(libusb_os_handle "libusb.h" HAVE_LIBUSB_OS_HANDLE)
    check_symbol_exists(libusb_set_auto_detach_kernel_driver "libusb.h"
        HAVE_LIBUSB_SET_AUTO_DETACH_KERNEL_DRIVER)
endif()
if(LIBFTDI_FOUND)
    set(CMAKE_REQUIRED_INCLUDES ${LIBFTDI_INCLUDE_DIRS})
    set(CMAKE_REQUIRED_LIBRARIES ${LIBFTDI_LIBRARIES})
    check_symbol_exists(ftdi_tcioflush "ftdi.h" HAVE_FTDI_TCIOFLUSH)
endif()

if(HAVE_POLL_H)
    set(HAVE_POLL 1)
elseif(WIN32)
    set(HAVE_SELECT 1)
endif()
if(HAVE_SELECT_H AND NOT HAVE_POLL)
    set(HAVE_SELECT 1)
endif()

if(LIBZIP_FOUND)
    set(HAVE_LIBZIP 1)
endif()
if(LIBFTDI_FOUND)
    set(HAVE_LIBFTDI 1)
    set(CONF_LIBFTDI_VERSION "${LIBFTDI_VERSION}")
endif()
if(LIBGIO_FOUND)
    set(HAVE_LIBGIO_2_0 1)
endif()
if(NETTLE_FOUND)
    set(HAVE_LIBNETTLE 1)
    set(CONF_LIBNETTLE_VERSION "${NETTLE_VERSION}")
endif()
if(ZLIB_FOUND)
    set(HAVE_ZLIB 1)
    set(CONF_ZLIB_VERSION "${ZLIB_VERSION}")
endif()
if(BLUEZ_FOUND AND CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(HAVE_BLUETOOTH 1)
    set(HAVE_LIBBLUEZ 1)
    set(CONF_LIBBLUEZ_VERSION "${BLUEZ_VERSION}")
endif()
if(IEEE1284_INCLUDE_DIR AND IEEE1284_LIBRARY)
    set(HAVE_LIBIEEE1284 1)
endif()
if(HIDAPI_FOUND)
    set(HAVE_LIBHIDAPI 1)
    set(CONF_LIBHIDAPI_VERSION "${HIDAPI_VERSION}")
endif()
if(LIBUSB_FOUND)
    set(HAVE_LIBUSB_1_0 1)
    set(CONF_LIBUSB_1_0_VERSION "${LIBUSB_VERSION}")
endif()
if(LIBSERIALPORT_FOUND)
    set(HAVE_LIBSERIALPORT 1)
    set(CONF_LIBSERIALPORT_VERSION "${LIBSERIALPORT_VERSION}")
endif()
if(LIBZIP_FOUND)
    set(CONF_LIBZIP_VERSION "${LIBZIP_VERSION}")
endif()

# Determine the host.
if(WIN32 OR MINGW)
    set(CONF_HOST "x86_64-w64-mingw32")
else()
    set(CONF_HOST "${CMAKE_SYSTEM_PROCESSOR}-pc-${CMAKE_SYSTEM_NAME}")
endif()

set(HAVE_DRIVERS 1)
set(HAVE_HW_DEMO 1)
set(HAVE_HW_WCH_CH32H417 1)
set(HAVE_SERIAL_COMM 1)
if(ZLIB_FOUND)
    set(HAVE_INPUT_STF 1)
endif()
set(HAVE_UNALIGNED_LITTLE_ENDIAN_ACCESS 1)

# Size type (LP64 vs LLP64).
if(WIN32 OR MINGW)
    set(SIZEOF_UNSIGNED_LONG 4)
else()
    set(SIZEOF_UNSIGNED_LONG 8)
endif()
set(SIZEOF_UNSIGNED_INT 4)
if(SIZEOF_UNSIGNED_LONG EQUAL 8)
    set(HAVE_UINT64_T_UL 1)
elseif(SIZEOF_UNSIGNED_INT EQUAL 8)
    set(HAVE_UINT64_T_UI 1)
endif()

set(SR_PACKAGE_VERSION_MAJOR 0)
set(SR_PACKAGE_VERSION_MINOR 6)
set(SR_PACKAGE_VERSION_MICRO 0)
set(SR_PACKAGE_VERSION_STRING "0.6.0-ch32h417")
set(SR_LIB_VERSION_CURRENT 4)
set(SR_LIB_VERSION_REVISION 0)
set(SR_LIB_VERSION_AGE 0)
set(SR_LIB_VERSION_STRING "4:0:0")

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/config.h.cmake ${CMAKE_CURRENT_BINARY_DIR}/config.h)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/include/libsigrok/version.h.in ${CMAKE_CURRENT_BINARY_DIR}/include/libsigrok/version.h)

# ============================================================================
# Include directories
# ============================================================================
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/src/minilzo
    ${CMAKE_CURRENT_BINARY_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}/include
    ${GLIB_INCLUDE_DIRS}
)

foreach(dep LIBUSB LIBSERIALPORT LIBZIP LIBFTDI LIBGIO NETTLE ZLIB BLUEZ HIDAPI)
    if(${dep}_FOUND)
        include_directories(${${dep}_INCLUDE_DIRS})
        link_directories(${${dep}_LIBRARY_DIRS})
    endif()
endforeach()
link_directories(${GLIB_LIBRARY_DIRS})
if(IEEE1284_INCLUDE_DIR)
    include_directories(${IEEE1284_INCLUDE_DIR})
endif()

# ============================================================================
# Sources
# ============================================================================
# Build the complete upstream tree. All hardware drivers are compiled in;
# drivers whose optional dependencies are unavailable are excluded below.
file(GLOB_RECURSE LIBSIGROK_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.c"
)

# SCPI transports that need optional RPC/VISA/GPIB toolchains. The serial,
# TCP and USBTMC transports are always built.
list(FILTER LIBSIGROK_SOURCES EXCLUDE REGEX
    "/src/scpi/(scpi_vxi|vxi_clnt|vxi_xdr|scpi_visa|scpi_libgpib)\\.c$")

# Optional drivers: exclude when their required library is unavailable, or
# when they are Linux-only.
set(EXCLUDE_DRIVER_DIRS "")
if(NOT LIBFTDI_FOUND)
    list(APPEND EXCLUDE_DRIVER_DIRS
        asix-sigma chronovu-la ftdi-la ikalogic-scanaplus pipistrello-ols)
endif()
if(NOT LIBGIO_FOUND)
    list(APPEND EXCLUDE_DRIVER_DIRS mooshimeter-dmm)
endif()
if(NOT NETTLE_FOUND)
    list(APPEND EXCLUDE_DRIVER_DIRS rdtech-tc)
endif()
if(NOT (IEEE1284_INCLUDE_DIR AND IEEE1284_LIBRARY))
    list(APPEND EXCLUDE_DRIVER_DIRS hung-chang-dso-2100)
endif()
if(NOT HIDAPI_FOUND)
    list(APPEND EXCLUDE_DRIVER_DIRS dcttech-usbrelay)
endif()
if(NOT (LIBGIO_FOUND AND BLUEZ_FOUND))
    list(APPEND EXCLUDE_DRIVER_DIRS mooshimeter-dmm)
endif()
# libgpib is not part of the default build environment.
list(APPEND EXCLUDE_DRIVER_DIRS hp-3478a)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    # Linux-only kernel interfaces (sysfs GPIO, timerfd, ioctl).
    list(APPEND EXCLUDE_DRIVER_DIRS beaglelogic baylibre-acme)
endif()
if(WIN32)
    # POSIX-only direct serial/socket users.
    list(APPEND EXCLUDE_DRIVER_DIRS raspberrypi-pico ipdbg-la)
endif()
foreach(driver_dir ${EXCLUDE_DRIVER_DIRS})
    list(FILTER LIBSIGROK_SOURCES EXCLUDE REGEX
        "/src/hardware/${driver_dir}/")
endforeach()

if(NOT LIBZIP_FOUND)
    list(FILTER LIBSIGROK_SOURCES EXCLUDE REGEX "/src/output/srzip\\.c$")
endif()
if(NOT ZLIB_FOUND)
    list(FILTER LIBSIGROK_SOURCES EXCLUDE REGEX "/src/input/stf\\.c$")
endif()

# The linker-section based driver registry requires the start marker to be
# linked before all drivers and the stop marker after all drivers.
set(SR_DRIVER_LIST_START "${CMAKE_CURRENT_SOURCE_DIR}/src/driver_list_start.c")
set(SR_DRIVER_LIST_STOP "${CMAKE_CURRENT_SOURCE_DIR}/src/driver_list_stop.c")
list(REMOVE_ITEM LIBSIGROK_SOURCES ${SR_DRIVER_LIST_START} ${SR_DRIVER_LIST_STOP})
list(INSERT LIBSIGROK_SOURCES 0 ${SR_DRIVER_LIST_START})
list(APPEND LIBSIGROK_SOURCES ${SR_DRIVER_LIST_STOP})

# ============================================================================
# Library target
# ============================================================================
add_library(sigrok SHARED ${LIBSIGROK_SOURCES})

target_compile_definitions(sigrok PRIVATE MINILZO_HAVE_CONFIG_H)
if(NOT WIN32)
    target_compile_definitions(sigrok PRIVATE
        FIRMWARE_DIR="${CMAKE_INSTALL_PREFIX}/share/sigrok-firmware")
endif()

target_link_libraries(sigrok
    ${GLIB_LIBRARIES}
    ${PLATFORM_LIBS}
)
foreach(dep LIBUSB LIBSERIALPORT LIBZIP LIBFTDI LIBGIO NETTLE ZLIB BLUEZ HIDAPI)
    if(${dep}_FOUND)
        target_link_libraries(sigrok ${${dep}_LIBRARIES})
    endif()
endforeach()
if(HAVE_LIBIEEE1284)
    target_link_libraries(sigrok ${IEEE1284_LIBRARY})
endif()

set_target_properties(sigrok PROPERTIES
    OUTPUT_NAME sigrok
    VERSION 0.6.0
    SOVERSION 4
)

# ============================================================================
# Install
# ============================================================================
install(TARGETS sigrok
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/libsigrok/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/libsigrok
    FILES_MATCHING PATTERN "*.h"
)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/include/libsigrok/version.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/libsigrok
)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/config.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/libsigrok
)
# Also install to include root for C++ bindings compat.
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/config.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# ============================================================================
# pkg-config file
# ============================================================================
set(prefix ${CMAKE_INSTALL_PREFIX})
set(exec_prefix "\${prefix}")
set(libdir "\${exec_prefix}/lib")
set(includedir "\${prefix}/include")

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/libsigrok.pc.in ${CMAKE_CURRENT_BINARY_DIR}/libsigrok.pc @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/libsigrok.pc DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig)
