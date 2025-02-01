import questionary
import click
import re
from simple_term_menu import TerminalMenu
from brownie import network


class Prompt:

    INTERACTIVE = True

    def menu(self, options):
        terminal_menu = TerminalMenu(options)
        menu_entry_index = terminal_menu.show()
        selection = options[menu_entry_index]
        return selection

    def dictMenu(self, dictOptions):
        # Convert keys to list and make a menu
        selection = self.menu(list(dictOptions.keys()))
        # Get the method that corresponds to the selected key
        selected = dictOptions.get(selection)
        return selected

    def qText(self, prompt, validate, default="", len=20, fill=" "):
        response = questionary.text(
            self.r_just_prompt(prompt, len, fill), validate=validate, default=default
        ).ask()
        return response

    def r_just_prompt(self, prompt, len=20, fill=" "):
        return prompt.ljust(len, fill) + ": "

    def enterCurrency(
        self,
        prompt,
        scale=1,
        lowerBound=0.1,
        upperBound=100000,
        default=0,
        len=20,
        fill=" ",
    ):
        def validateCurrency(value):
            try:
                # Convert the input to a number
                number = float(value)
                # Check if the number is within the range
                if lowerBound <= number <= upperBound:
                    return True
                else:
                    return (
                        f"Please enter a number between {lowerBound} and {upperBound}."
                    )
            except ValueError:
                return "Invalid input. Please enter a valid number."

        response = self.qText(
            prompt,
            validate=validateCurrency,
            default=f"{default:.2f}",
            len=len,
            fill=fill,
        )
        return int(round(float(response) * 10**scale))

    def enterNumber(
        self,
        prompt,
        lowerBound=0,
        upperBound=2**64,
        default=0,
        len=20,
        fill=" ",
    ):
        def validateNumber(value):
            try:
                # Convert the input to a number
                number = int(value)
                # Check if the number is within the range
                if lowerBound <= number <= upperBound:
                    return True
                else:
                    return (
                        f"Please enter a number between {lowerBound} and {upperBound}."
                    )
            except ValueError:
                return "Invalid input. Please enter a valid number."

        response = self.qText(
            prompt,
            validate=validateNumber,
            default=f"{default}",
            len=len,
            fill=fill,
        )
        return int(response)

    def enterFloat(
        self,
        prompt,
        lowerBound=0.0,
        upperBound=10**9,
        default=0.0,
        len=20,
        fill=" ",
    ):
        def validateFloat(value):
            try:
                # Convert the input to a number
                number = float(value)
                # Check if the number is within the range
                if lowerBound <= number <= upperBound:
                    return True
                else:
                    return (
                        f"Please enter a number between {lowerBound} and {upperBound}."
                    )
            except ValueError:
                return "Invalid input. Please enter a valid number."

        response = self.qText(
            prompt, validate=validateFloat, default=f"{default:.2f}", len=len, fill=fill
        )
        return float(response)

    def enterString(self, prompt, regex=r".*", default=""):
        def validateString(value):
            r = re.compile(regex)
            if r.match(value):
                return True
            return "Invalid input. Please enter a valid string."

        response = self.qText(
            prompt, validate=validateString, default=default, len=20, fill=" "
        )
        return response

    def enterBool(
        self,
        prompt,
        default=True,
        len=20,
        fill=" ",
    ):
        response = questionary.confirm(
            self.r_just_prompt(prompt, len=len, fill=fill), default=default
        ).ask()
        return response

    def setInteractive(self, interactive):
        self.INTERACTIVE = interactive

    def confirm(self, text):
        if self.INTERACTIVE:
            return click.confirm(
                (
                    f"This action will alter the state of "
                    f"the blockchain <{network.show_active()}>. \n"
                    f"The action is '{text}'. \n"
                    f"Do you want to proceed?"
                )
            )
        else:
            return True


# Prompt object
prompt = Prompt()
confirm = prompt.confirm
