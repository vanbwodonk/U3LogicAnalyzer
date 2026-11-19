#!/usr/bin/env bash
# ============================================================================
# build_linux.sh - build U3LogicAnalyzer on Linux only
#
# Builds the in-tree libsigrok (with the WCH CH32H417 driver),
# libsigrokcxx, libsigrokdecode and the LogicAnalyzer application.
# macOS and Windows are intentionally not handled here.
#
# Usage:
#   ./build_linux.sh              # release build
#   ./build_linux.sh --debug      # debug build
#   ./build_linux.sh --clean      # remove the build tree first
#   ./build_linux.sh --run        # build, then start the application
#   ./build_linux.sh --clean --debug --run
#
# Environment:
#   BUILD_DIR   build directory (default: ./build/linux)
#   JOBS        parallel build jobs (default: nproc)
# ============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
CLEAN=0
DEBUG=0
RUN=0

for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=1 ;;
        --debug) DEBUG=1 ;;
        --run) RUN=1 ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "[error] unknown option: $arg" >&2
            echo "try: $0 --help" >&2
            exit 2
            ;;
    esac
done

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "[error] build_linux.sh only supports Linux; use build_macos.sh or build_windows.sh otherwise" >&2
    exit 1
fi

if [[ $DEBUG -eq 1 ]]; then
    BUILD_TYPE=Debug
else
    BUILD_TYPE=Release
fi

BUILD_DIR="${BUILD_DIR:-$ROOT_DIR/build/linux}"
PREFIX="$BUILD_DIR/install"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
missing=()

for cmd in cmake pkg-config gcc g++; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done

for module in Qt5Core Qt5Gui Qt5Widgets Qt5Svg Qt5Network glib-2.0 glibmm-2.4 libusb-1.0; do
    pkg-config --exists "$module" 2>/dev/null || missing+=("pkg-config:$module")
done

if ! command -v python3 >/dev/null 2>&1; then
    missing+=("python3")
elif ! python3 -c 'import sysconfig' >/dev/null 2>&1; then
    missing+=("python3")
fi

# Optional, but needed for the full hardware driver set and some features.
missing_optional=()
check_optional_any() {
    local module
    for module in "$@"; do
        pkg-config --exists "$module" 2>/dev/null && return 0
    done
    missing_optional+=("$1")
}
check_optional_any hidapi hidapi-hidraw hidapi-libusb
for module in libzip libserialport libftdi1 nettle bluez zlib; do
    pkg-config --exists "$module" 2>/dev/null || missing_optional+=("$module")
done

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "[error] missing build dependencies:" >&2
    printf '  - %s\n' "${missing[@]}" >&2
    echo "" >&2
    echo "Arch Linux:" >&2
    echo "  sudo pacman -S --needed base-devel cmake ninja pkgconf qt5-base qt5-svg \\" >&2
    echo "      qt5-tools glib2 glibmm libusb hidapi libzip boost libserialport \\" >&2
    echo "      libftdi nettle bluez-libs zlib python" >&2
    echo "" >&2
    echo "Debian/Ubuntu:" >&2
    echo "  sudo apt install build-essential cmake ninja-build pkg-config \\" >&2
    echo "      qtbase5-dev qttools5-dev libqt5svg5-dev libglib2.0-dev \\" >&2
    echo "      libglibmm-2.4-dev libusb-1.0-0-dev libserialport-dev libftdi1-dev \\" >&2
    echo "      libnettle-dev libieee1284-3-dev libbluetooth-dev libhidapi-dev \\" >&2
    echo "      libzip-dev libboost-dev libboost-filesystem-dev \\" >&2
    echo "      libboost-serialization-dev python3-dev" >&2
    exit 1
fi

if [[ ${#missing_optional[@]} -gt 0 ]]; then
    echo "[warning] optional dependencies not found: ${missing_optional[*]}"
    echo "          some hardware drivers/features will be disabled"
fi

# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------
if command -v ninja >/dev/null 2>&1; then
    GENERATOR=(-G Ninja)
else
    GENERATOR=()
fi

CMAKE_COMMON=(
    "${GENERATOR[@]}"
    -DCMAKE_INSTALL_PREFIX="$PREFIX"
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE"
    -DDISABLE_WERROR=ON
)
if [[ $DEBUG -eq 1 ]]; then
    CMAKE_COMMON+=(-DCMAKE_EXPORT_COMPILE_COMMANDS=ON)
fi

if [[ $CLEAN -eq 1 ]]; then
    if [[ -z "$BUILD_DIR" || "$BUILD_DIR" == "/" ]]; then
        echo "[error] refusing to clean BUILD_DIR=$BUILD_DIR" >&2
        exit 1
    fi
    echo "[clean] removing $BUILD_DIR"
    rm -rf "$BUILD_DIR"
fi
mkdir -p "$BUILD_DIR"

echo "============================================"
echo " U3LogicAnalyzer (Linux) Build"
echo "============================================"
echo "Repo:       $ROOT_DIR"
echo "Build type: $BUILD_TYPE"
echo "Build dir:  $BUILD_DIR"
echo "Jobs:       $JOBS"
echo ""

# ---------------------------------------------------------------------------
# 1/4: libsigrok (upstream drivers + wch-ch32h417)
# ---------------------------------------------------------------------------
echo "===== 1/4: libsigrok ====="
cmake -S "$ROOT_DIR/libsigrok" -B "$BUILD_DIR/libsigrok_build" \
    "${CMAKE_COMMON[@]}"
cmake --build "$BUILD_DIR/libsigrok_build" -j "$JOBS"
cmake --install "$BUILD_DIR/libsigrok_build"

export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export CMAKE_PREFIX_PATH="$PREFIX${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"

# ---------------------------------------------------------------------------
# 2/4: libsigrokcxx C++ bindings
# ---------------------------------------------------------------------------
echo ""
echo "===== 2/4: libsigrokcxx ====="
cmake -S "$ROOT_DIR/libsigrok/bindings/cxx" -B "$BUILD_DIR/libsigrokcxx_build" \
    "${CMAKE_COMMON[@]}"
cmake --build "$BUILD_DIR/libsigrokcxx_build" -j "$JOBS"
cmake --install "$BUILD_DIR/libsigrokcxx_build"

# ---------------------------------------------------------------------------
# 3/4: libsigrokdecode + decoders
# ---------------------------------------------------------------------------
echo ""
echo "===== 3/4: libsigrokdecode ====="
cmake -S "$ROOT_DIR/libsigrokdecode" -B "$BUILD_DIR/libsigrokdecode_build" \
    "${CMAKE_COMMON[@]}"
cmake --build "$BUILD_DIR/libsigrokdecode_build" -j "$JOBS"
cmake --install "$BUILD_DIR/libsigrokdecode_build"
echo "[ok] decoders: $(find "$PREFIX/share/libsigrokdecode/decoders" -mindepth 1 -maxdepth 1 -type d | wc -l)"

# ---------------------------------------------------------------------------
# 4/4: U3LogicAnalyzer
# ---------------------------------------------------------------------------
echo ""
echo "===== 4/4: LogicAnalyzer ====="
APP_CMAKE_OPTS=(
    "${CMAKE_COMMON[@]}"
    -DCMAKE_PREFIX_PATH="$PREFIX"
    -DENABLE_DECODE=ON
    -DENABLE_FLOW=OFF
    -DENABLE_TESTS=OFF
    -DENABLE_SIGNALS=ON
    -DSTATIC_PKGDEPS_LIBS=OFF
    -DCMAKE_SKIP_RPATH=OFF
)
if [[ $DEBUG -eq 1 ]]; then
    APP_CMAKE_OPTS+=(-DENABLE_STACKTRACE=OFF)
fi

cmake -S "$ROOT_DIR" -B "$BUILD_DIR/pulseview_build" "${APP_CMAKE_OPTS[@]}"
cmake --build "$BUILD_DIR/pulseview_build" -j "$JOBS"

APP="$BUILD_DIR/pulseview_build/LogicAnalyzer"

echo ""
echo "============================================"
echo " Build complete: $APP"
echo "============================================"

if [[ $RUN -eq 1 ]]; then
    echo "Starting LogicAnalyzer..."
    exec env \
        LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
        SIGROKDECODE_DIR="$PREFIX/share/libsigrokdecode/decoders" \
        "$APP"
else
    echo ""
    echo "Run with:"
    echo "  LD_LIBRARY_PATH=\"$PREFIX/lib\" \\"
    echo "  SIGROKDECODE_DIR=\"$PREFIX/share/libsigrokdecode/decoders\" \\"
    echo "  \"$APP\""
    echo ""
    echo "or: $0 --run"
fi
