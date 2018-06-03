from setuptools import find_packages, setup
import versioneer


setup(name='pyIlluminate',
      version=versioneer.get_version(),
      url='https://bitbucket.org/opticalwavefrontlabs/pyilluminate',
      author='Optical Wavefront Laboratories, LLC.',
      author_email='info@opticalwavefrontlabs.com',
      license='BSD',
      install_requires=['pyserial'],
      packages=find_packages(),
      cmdclass=versioneer.get_cmdclass(),
      )
