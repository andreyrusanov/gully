import os
import typing


class VariablesProvider(typing.Protocol):
    def __init__(self, *args, options: typing.Dict, **kwargs):
        ...

    def get(self, key: str) -> typing.Optional[typing.Any]:
        ...

    @classmethod
    def option_name(cls) -> str:
        """
        Provider's option name in the `options` kwargs of the variable reader
        """
        ...


class EnvVariablesProvider:
    """
    Simple provider to read variables from environment
    """
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def option_name(cls) -> str:
        return 'environ'

    def get(self, key: str) -> typing.Optional[typing.Any]:
        if key not in os.environ:
            raise KeyError
        return os.environ[key]


class EnvFileProvider:
    """
    Reads variables from env file;
    The provider is lazy - it reads entire file on the first call and caches it
    """
    def __init__(self, *args, options: typing.Dict, **kwargs):
        self.path = options.get('path', '.env')
        self.values = {}
        if not os.path.exists(self.path):
            if options.get('require_file', False):
                raise Exception(f"File does not exist: {self.path}")
        else:
            self.values = self._read_file()

    @classmethod
    def option_name(cls):
        return 'env_file'

    def _read_file(self):
        variables = {}
        with open(self.path) as f:
            for line in f:
                if line.startswith('#') or line.strip() == '':
                    continue
                key, value = line.strip().split('=', 1)
                variables[key.strip()] = value.strip()
        return variables

    def get(self, key: str) -> typing.Optional[typing.Any]:
        if key not in self.values:
            raise KeyError
        return self.values[key]


class _emptyType:  # noqa
    ...


_empty = _emptyType()


class VariableReader:

    default_providers: typing.Tuple[typing.Type[VariablesProvider]] = (
        EnvVariablesProvider,
        EnvFileProvider,
    )

    def __init__(self, providers: typing.Tuple[VariablesProvider] = tuple(), **options):
        self.providers: typing.List[VariablesProvider] = []

        for provider in (providers or self.default_providers):
            self.providers.append(
                provider(options=options.get(provider.option_name(), {}))
            )

    def get(self, key: str, default: typing.Any = _empty, callback: typing.Callable = _empty) -> typing.Any:
        value = _empty
        for provider in self.providers:
            try:
                value = provider.get(key)
            except KeyError:
                continue
            break

        if value is _empty:
            if default is _empty:
                raise KeyError(key)
            return default
        if callback is not _empty:
            value = callback(value)

        return value

    @staticmethod
    def value_to_bool(value: typing.Any) -> bool:
        if isinstance(value, str):
            return value.lower() in {'y', 'yes', 'true', '1'}
        elif isinstance(value, bool):
            return value
        elif isinstance(value, int):
            return value == 1
        raise TypeError(f"Can't convert value of type {type(value)} to bool")

    def bool(self, key: str, default: typing.Any = _empty, callback: typing.Callable = _empty) -> typing.Any:
        return self.__typed_get(key, default, callback, self.value_to_bool)

    def str(self, key: str, default: typing.Any = _empty, callback: typing.Callable = _empty) -> typing.Any:
        return self.__typed_get(key, default, callback, str)

    def int(self, key: str, default: typing.Any = _empty, callback: typing.Callable = _empty) -> typing.Any:
        return self.__typed_get(key, default, callback, int)

    def __typed_get(self, key: str, default: typing.Any, callback: typing.Callable, t: typing.Any) -> bool:
        value = self.get(
            key,
            default,
            lambda v: t(v) if callback is _empty
            else lambda v: callback(t(v)))
        return value
