import sys
import pkgutil


def load_krogon_plugin_click_commands(root_click_group):
    for (_, name, _) in pkgutil.iter_modules(sys.path):
        if not name.startswith('krogon_'):
            continue
        plugin_name = name.replace('krogon_', '')
        cli_module_name = name + '.' + plugin_name + '_cli'
        try:
            module = __import__(cli_module_name)
            click_cli_group = module \
                .__getattribute__(plugin_name + '_cli') \
                .__getattribute__(plugin_name)
            root_click_group.add_command(click_cli_group)
        except ModuleNotFoundError:
            continue
        except AttributeError:
            continue


