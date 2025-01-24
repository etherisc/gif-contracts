import questionary
import click
import re
from simple_term_menu import TerminalMenu
from brownie import network


class Prompt:

    INTERACTIVE = True

    def executeFunctionOrObject(self, param):
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
        # else:
        #    raise ValueError(
        #        "Parameter must be a function or a dictionary with 'function' and 'args' keys")

    def menu(self, options):
        terminal_menu = TerminalMenu(options)
        menu_entry_index = terminal_menu.show()
        selection = options[menu_entry_index]
        return selection

    def dictMenu(self, dictOptions):
        # Convert keys to list and make a menu
        selection = self.menu(list(dictOptions.keys()))
        # Get the method that corresponds to the selected key
        selected_function = dictOptions.get(selection)
        self.executeFunctionOrObject(selected_function)  # Invoke the method
        return selection

    def qText(self, prompt, validate):
        response = questionary.text(prompt.ljust(30), validate=validate).ask()
        return response

    def enterCurrency(self, prompt, scale=1, lowerBound=0.1, upperBound=100000):
        def validateCurrency(value):
            try:
                # Convert the input to a number
                number = float(value)
                # Check if the number is within the range
                if lowerBound <= number <= upperBound:
                    return True
                else:
                    return f"Please enter a number between {lowerBound} and {upperBound}."
            except ValueError:
                return "Invalid input. Please enter a valid number."

        response = self.qText(prompt, validate=validateCurrency)
        return int(round(float(response) * 10 ** scale))

    def enterNumber(self, prompt, lowerBound, upperBound):
        def validateNumber(value):
            try:
                # Convert the input to a number
                number = int(value)
                # Check if the number is within the range
                if lowerBound <= number <= upperBound:
                    return True
                else:
                    return f"Please enter a number between {lowerBound} and {upperBound}."
            except ValueError:
                return "Invalid input. Please enter a valid number."

        response = self.qText(prompt, validate=validateNumber)
        return int(response)

    def enterFloat(self, prompt, lowerBound, upperBound):
        def validateFloat(value):
            try:
                # Convert the input to a number
                number = float(value)
                # Check if the number is within the range
                if lowerBound <= number <= upperBound:
                    return True
                else:
                    return f"Please enter a number between {lowerBound} and {upperBound}."
            except ValueError:
                return "Invalid input. Please enter a valid number."

        response = self.qText(prompt, validate=validateFloat)
        return float(response)

    def enterString(self, prompt, regex):
        def validateString(value):
            r = re.compile(regex)
            if r.match(value):
                return True
            return "Invalid input. Please enter a valid string."
        response = self.qText(prompt, validate=validateString)
        return response

    def setInteractive(self, interactive):
        self.INTERACTIVE = interactive

    def confirm(self, text):
        if self.INTERACTIVE:
            return click.confirm((
                f"This action will alter the state of "
                f"the blockchain <{network.show_active()}>. "
                f"The action is '{text}'. "
                f"Do you want to proceed?"
            ))
        else:
            return True


# Prompt object
prompt = Prompt()
confirm = prompt.confirm
