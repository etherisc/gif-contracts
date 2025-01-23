from simple_term_menu import TerminalMenu


class Prompt:
    def execute_function_or_object(self, param):
        if callable(param):
            # If param is a function, call it without parameters
            return param()
        elif isinstance(param, dict) and 'function' in param and 'args' in param:
            # If param is a dictionary with 'function' and 'args', execute the function with arguments
            func = param['function']
            args = param['args']

            if not callable(func):
                raise ValueError(
                    "'function' in the dictionary must be callable")
            if not isinstance(args, (list, tuple)):
                raise ValueError(
                    "'args' in the dictionary must be a list or tuple")

            return func(*args)
        else:
            raise ValueError(
                "Parameter must be a function or a dictionary with 'function' and 'args' keys")

    def menu(self, options):
        terminal_menu = TerminalMenu(options)
        menu_entry_index = terminal_menu.show()
        selection = options[menu_entry_index]
        return selection

    def dict_menu(self, dict_options):
        # Convert keys to list and make a menu
        selection = self.menu(list(dict_options.keys()))
        # Get the method that corresponds to the selected key
        selected_function = dict_options.get(selection)
        self.execute_function_or_object(selected_function)  # Invoke the method
        return selection
