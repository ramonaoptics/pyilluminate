from setuptools import find_packages, setup


# Loads _version.py module without importing the whole package.
def get_version_and_cmdclass(pkg_path):
    import os
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location(
        'version', os.path.join(pkg_path, '_version.py'),
    )
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__, module.get_cmdclass(pkg_path)


version, cmdclass = get_version_and_cmdclass('pyilluminate')

setup(
    name='pyilluminate',
    url='https://github.com/ramonaoptics/pyilluminate',
    author='Ramona Optics, Inc.',
    author_email='info@ramonaoptics.com',
    license='BSD',
    python_requires='>=3.7',
    install_requires=[
        'pyserial',
        'multiuserfilelock',
        'xarray',
    ],
    packages=find_packages(),
    version=version,
    cmdclass=cmdclass,
)
