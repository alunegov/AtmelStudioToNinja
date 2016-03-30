from setuptools import setup


setup(
    name="asninja",
    version="1.0",
    packages=[
        'asninja',
        'asninja.toolchains'
    ],
    install_requires=[
        'ninja_syntax>=1.6.0'
    ],
    author='Alexander Lunegov',
    author_email='alunegov@gmail.com',
    url='https://github.com/alunegov/AtmelStudioToNinja',
    description='Convert Atmel Studio .cproj/.cppproj file to .ninja file',
    license='MIT'
)
