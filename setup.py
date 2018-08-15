from setuptools import find_packages, setup
import versioneer


setup(name='pyIlluminate',
      version=versioneer.get_version(),
      url='https://bitbucket.org/opticalwavefrontlabs/pyilluminate',
      author='Ramona Optics, Inc.',
      author_email='info@ramonaoptics.com',
      license='BSD',
      install_requires=['pyserial',
                        'xarray'],
      packages=find_packages(),
      cmdclass=versioneer.get_cmdclass(),
      )
