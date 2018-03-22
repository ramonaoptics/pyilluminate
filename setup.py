import ast
import re

from pathlib import Path
from setuptools import setup, find_packages


def get_setup_info(module_path):
    init_file = Path(module_path) / '__init__.py'
    with open(init_file, 'r') as f:
        contents = f.read()

    module = ast.parse(contents)
    docstring = ast.get_docstring(module)

    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              contents, re.M)
    if version_match:
        return (version_match.group(1), docstring)

    raise RuntimeError("Unable to find version string.")


(version, docstring) = get_setup_info('pyilluminate')

print(docstring)

setup(name='pyIlluminate',
      version=version,
      description=docstring,
      url='https://bitbucket.org/opticalwavefrontlabs/pyilluminate',
      author='Optical Wavefront Laboratories, LLC.',
      author_email='info@opticalwavefrontlabs.com',
      license='BSD',
      packages=find_packages(),
      )
