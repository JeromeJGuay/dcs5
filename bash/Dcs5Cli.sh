conda activate dcs
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
PATH="${SCRIPT_DIR}../dcs5/cli_app.py"
python3 ${PATH}

