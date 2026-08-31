"""Tests that enforce beginner-readable public API documentation."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import unittest

import mhtml_etl_gateway


class DocstringCoverageTests(unittest.TestCase):
    """Require useful docstrings for every shipped public symbol."""

    def test_public_api_docstrings_are_complete(self) -> None:
        """All public modules, classes, functions, methods, and properties are documented."""
        missing: list[str] = []
        package_path = list(mhtml_etl_gateway.__path__)
        module_names = [mhtml_etl_gateway.__name__]
        module_names.extend(
            module_info.name
            for module_info in pkgutil.walk_packages(
                package_path,
                prefix=f"{mhtml_etl_gateway.__name__}.",
            )
            if not module_info.name.endswith(".__main__")
        )
        for module_name in sorted(module_names):
            module = importlib.import_module(module_name)
            if not inspect.getdoc(module):
                missing.append(module_name)
            for name, value in inspect.getmembers(module):
                if (
                    name.startswith("_")
                    or getattr(value, "__module__", None) != module_name
                ):
                    continue
                if (
                    inspect.isclass(value) or inspect.isfunction(value)
                ) and not inspect.getdoc(value):
                    missing.append(f"{module_name}.{name}")
                if inspect.isclass(value):
                    for member_name, member in inspect.getmembers(value):
                        if member_name.startswith("_"):
                            continue
                        if isinstance(member, property):
                            if not inspect.getdoc(member):
                                missing.append(f"{module_name}.{name}.{member_name}")
                        elif inspect.isfunction(member) and not inspect.getdoc(member):
                            missing.append(f"{module_name}.{name}.{member_name}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
