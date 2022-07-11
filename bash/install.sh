#!/bin/bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
TARGET="${HOME}/.local/share/applications/dcs5.desktop"    
HEADER="DESKTOP ENTRY"
NAME="Dcs5 Cli App"
EXEC="${SCRIPT_DIR}/Dcs5Cli.sh;$SHELL:"
ICON="${SCRIPT_DIR}/bigfin.png"

cat > ${TARGET} <<-END
[Desktop Entry]
Type=Application
Name=${NAME}
Exec=${EXEC}
Icon=${ICON}
Terminal=true

END



