"""Setup."""

import subprocess

from setuptools import find_packages, setup
from setuptools.command.install import install as SetuptoolsInstall


class ABPIInstall(SetuptoolsInstall):
    """Custom installation."""

    def run(self):
        print("Compiling LCD control library...")
        compile_lcd = subprocess.Popen(
            ["make"], stdout=subprocess.PIPE, cwd="lcd"
        )
        if compile_lcd.wait() != 0:
            raise RuntimeError("could not compile lcd module")
        print("Compiling user I/O server...")
        compile_io = subprocess.Popen(
            ["make"], stdout=subprocess.PIPE, cwd="io"
        )
        if compile_io.wait() != 0:
            raise RuntimeError("could not compile user_io module")
        super().run()


setup(
    name="autobrew",
    version="0.1",
    packages=find_packages(),
    package_dir={"": "."},
    package_data={
        "abpi": ["data/fonts/*", "lcd/screen.lib", "data/drivers/*"]
    },
    dependency_links=["git+https://github.com/brunosmmm/hbussd.git"],
    install_requires=["pyzmq>=17.0.0"],
    author="Bruno Morais",
    author_email="brunosmmm@gmail.com",
    description="AutoBrew",
    cmdclass={"install": ABPIInstall},
    scripts=["io/ab_user", "autobrew"],
)
