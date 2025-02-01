class LoggerWrapper:
    def __init__(self, base_instance):
        """
        Initialize the wrapper with the base instance.
        :param base_instance: Instance of the base class to wrap.
        """
        self._base_instance = base_instance

    def __getattr__(self, name):
        """
        Intercept attribute access and add logging for methods.
        :param name: Name of the attribute being accessed.
        :return: The wrapped method or the original attribute.
        """
        attr = getattr(self._base_instance, name)

        # If it's a callable (method), wrap it with logging
        if callable(attr):

            def logged_method(*args, **kwargs):
                print(f"Calling method: {name}")
                print(f"Arguments: {args}, Keyword Arguments: {kwargs}")
                result = attr(*args, **kwargs)
                print(f"Result: {result}")
                return result

            return logged_method
        return attr
