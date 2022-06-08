from controller import Dcs5Controller

XT_BUILTIN_SETTINGS = "./static/control_box_parameters.json"
DEFAULT_DEVICES_SPECIFICATION_FILE = "./devices_specification/default_devices_specification.json"
DEFAULT_CONTROLLER_CONFIGURATION_FILE = "configs/default_configuration.json"


def launch_dcs5(
        config_path: str = DEFAULT_CONTROLLER_CONFIGURATION_FILE,
        devices_specifications_path: str = DEFAULT_DEVICES_SPECIFICATION_FILE,
        control_box_settings_path: str = XT_BUILTIN_SETTINGS
):

    controller = Dcs5Controller(
        config_path=config_path,
        devices_specifications_path=devices_specifications_path,
        control_box_settings_path=control_box_settings_path
    )

    controller.start_client(controller.config.client.mac_address)

    if controller.client_isconnected:
        controller.sync_controller_and_board()
        controller.start_listening()

    return controller


if __name__ == "__main__":
    c = launch_dcs5()