from setuptools import find_packages, setup
import versioneer


setup(
    name='pyilluminate',
    version=versioneer.get_version(),
    url='https://github.com/ramonaoptics/pyilluminate',
    author='Ramona Optics, Inc.',
    author_email='info@ramonaoptics.com',
    license='BSD',
    python_requires='>=3.6',
    install_requires=[
        'pyserial',
        'xarray',
        'dataclasses; python_version<"3.7"',
    ],
    packages=find_packages(),
    cmdclass=versioneer.get_cmdclass(),
)
