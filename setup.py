########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from setuptools import setup

setup(
    name='cloudify-linode-plugin',
    version='0.1',
    author='Marques Johansson',
    author_email='marques@linode.com',
    description='A cloudify plugin for managing Linode Instances',
    packages=['linode_plugin'],
    license='LICENSE',
    zip_safe=False,
    install_requires=[
        "requests==2.20.0",
        "linode_api4==2.0.0",
        "cloudify-plugins-common>=4.0a2",
    ]
)
