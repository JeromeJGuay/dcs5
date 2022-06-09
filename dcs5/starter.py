
from controller import Dcs5Controller
from utils import resolve_relative_path

DEFAULT_CONTROLLER_CONFIGURATION_FILE = "configs/default_configuration.json"
DEFAULT_DEVICES_SPECIFICATION_FILE = "devices_specifications/default_devices_specification.json"
XT_BUILTIN_SETTINGS = "static/control_box_parameters.json"


def start_dcs5_controller(
        config_path=resolve_relative_path(DEFAULT_CONTROLLER_CONFIGURATION_FILE, __file__),
        devices_specifications_path=resolve_relative_path(DEFAULT_DEVICES_SPECIFICATION_FILE, __file__),
        control_box_settings_path=resolve_relative_path(XT_BUILTIN_SETTINGS, __file__)
):

    controller = Dcs5Controller(
        config_path=config_path,
        devices_specifications_path=devices_specifications_path,
        control_box_settings_path=control_box_settings_path
    )

    controller.start_client()

    if controller.client.isconnected:
        controller.sync_controller_and_board()
        controller.start_listening()

    return controller


if __name__ == "__main__":
    from dcs5.logger import init_logging
    init_logging()
    c = start_dcs5_controller()