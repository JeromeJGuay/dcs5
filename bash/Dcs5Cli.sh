
echo "conda activate dcs5"
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]:-$0}"; )" &> /dev/null && pwd 2> /dev/null; )";
python3 "${SCRIPT_DIR}/../dcs5/cli_app.py"