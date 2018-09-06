"""setup.py: setuptools control."""

from setuptools import setup

PROJECT_NAME = 'asninja'

setup(
    name=PROJECT_NAME,
    version="1.2.1",
    packages=[
        PROJECT_NAME,
        PROJECT_NAME + '.toolchains'
    ],
    entry_points={
        "console_scripts": ['{0} = {0}.{0}:main'.format(PROJECT_NAME)]
    },
    install_requires=[
        'ninja_syntax>=1.6.0'
    ],
    author='Alexander Lunegov',
    author_email='alunegov@gmail.com',
    url='https://github.com/alunegov/AtmelStudioToNinja',
    description='Convert Atmel Studio project file to Ninja build file',
    license='MIT'
)
