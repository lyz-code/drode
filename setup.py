import logging
import os
import shutil

from setuptools import find_packages, setup
from setuptools.command.install import install

log = logging.getLogger(__name__)

# Get the version from drode/version.py without importing the package
exec(compile(open('drode/version.py').read(),
             'drode/version.py', 'exec'))


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)
        try:
            data_directory = os.path.expanduser("~/.local/share/drode")
            os.makedirs(data_directory)
            log.info("Data directory created")
        except FileExistsError:
            log.info("Data directory already exits")

        config_path = os.path.join(data_directory, 'config.yaml')
        if os.path.isfile(config_path) and os.access(config_path, os.R_OK):
            log.info(
                "Configuration file already exists, check the documentation "
                "for the new version changes."
            )
        else:
            shutil.copyfile('assets/config.yaml', config_path)
            log.info("Copied default configuration template")


setup(
    name='drode',
    version=__version__, # noqa: F821
    description='Wrapper over Drone API to make deployments an easier task',
    author='lyz',
    author_email='lyz@riseup.net',
    license='GPLv3',
    long_description=open('README.md').read(),
    packages=find_packages(exclude=('tests',)),
    entry_points={'console_scripts': ['drode = drode:main']},
    cmdclass={
        "install": PostInstallCommand,
    },
    install_requires=[
        "argcomplete>=1.11.1",
        "boto3>=1.13.24",
        "ruamel.yaml>=0.16.10",
        "requests>=2.23.0",
        "tabulate>=0.8.7"
    ]
)
