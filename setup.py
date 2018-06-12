from setuptools import find_packages, setup

# Loads version.py module without importing the whole package.
def get_version_and_cmdclass(package_path):
    import os
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location('version',
                                   os.path.join(package_path, '_version.py'))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__, module.cmdclass


version, cmdclass = get_version_and_cmdclass('pyilluminate')



setup(name='pyIlluminate',
      version=version,
      url='https://bitbucket.org/opticalwavefrontlabs/pyilluminate',
      author='Optical Wavefront Laboratories, LLC.',
      author_email='info@opticalwavefrontlabs.com',
      license='BSD',
      install_requires=['pyserial'],
      packages=find_packages(),
      cmdclass=cmdclass,
      )
