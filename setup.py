from setuptools import find_packages, setup

setup(
    name='hypermediachannels',
    version="0.0.2",
    url='https://github.com/hishnash/hypermediachannels',
    author='Matthaus Woolard',
    author_email='matthaus.woolard@gmail.com',
    description="Hyper Media Channels Rest Framework.",
    long_description=open('README.rst').read(),
    license='MIT',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'channels>=2.1.1',
        'Django>=2.0.0',
        'djangochannelsrestframework==0.0.2',
        'channelsmultiplexer==0.0.2'
    ],
    extras_require={
        'tests': [
            'pytest~=3.3',
            "pytest-django~=3.1",
            "pytest-asyncio~=0.8",
            'coverage~=4.4',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
