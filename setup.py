#!/usr/bin/env python
from setuptools import find_packages, setup

import os
import subprocess
import time

version_file = 'fluxsr/version.py'


def readme():
    with open('README.md', encoding='utf-8') as f:
        content = f.read()
    return content


def get_git_hash():

    def _minimal_ext_cmd(cmd):
        env = {}
        for k in ['SYSTEMROOT', 'PATH', 'HOME']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env).communicate()[0]
        return out

    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        sha = out.strip().decode('ascii')
    except OSError:
        sha = 'unknown'

    return sha


def get_hash():
    if os.path.exists('.git'):
        sha = get_git_hash()
        return sha
    else:
        return 'unknown'


def write_version_py():
    content = f"""# GENERATED VERSION FILE
# TIME: {time.asctime()}
__version__ = '1.4.2'
__gitsha__ = '{get_hash()}'
version_info = (1, 4, 2)
"""
    with open(version_file, 'w') as f:
        f.write(content)


def get_requirements(filename='requirements.txt'):
    here = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(here, filename), 'r') as f:
        requires = [line.replace('\n', '') for line in f.readlines()]
    return requires


if __name__ == '__main__':
    write_version_py()
    setup(
        name='fluxsr',
        description='A refined super-resolution framework built on the shoulders of BasicSR',
        long_description=readme(),
        long_description_content_type='text/markdown',
        author='Lin Ell',
        author_email='linjack833@gmail.com',
        url='https://github.com/lack9921/FluxSR',
        packages=find_packages(exclude=('options', 'datasets', 'experiments', 'results', 'tb_logger', 'wandb')),
        include_package_data=True,
        classifiers=[
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
        ],
        license='Apache-2.0',
        setup_requires=[],
        tests_require=['pytest'],
        install_requires=get_requirements(),
        ext_modules=[],
        zip_safe=False,
    )
