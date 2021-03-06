# #######
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import linode

from cloudify import ctx
from cloudify.decorators import operation
# from cloudify.exceptions import NonRecoverableError


@operation
def create(args=None, **_):
    """Create an SSH key
    """
    ctx.logger.info('Creating SSH Key...')
    ctx.logger.debug('SSH Key arguments: {0}'.format(args))
    user_ssh_key = _get_ssh_key(args['key_source'])
    key = linode.SSHKey(
        token=args['token'],
        name=args['ssh_key_name'],
        public_key=user_ssh_key,
        **args)
    key.create()


def _get_ssh_key(source):
    pass
