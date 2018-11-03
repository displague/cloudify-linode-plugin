# #######
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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
import os
from cloudify import ctx, Version
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from linode_api4 import LinodeClient
from linode_api4.errors import ApiError


def load_token():
    """ XXX
    This will load a security token from a local file called token.txt
    A token can be obtained from Linode by creating a personal access token.
    https://www.linode.com/docs/platform/api/getting-started-with-the-linode-api/#get-an-access-token
    :return: the security token, as a string
    :raises: NonRecoverableError if token is not present
    """
    cwd = os.path.dirname(__file__)
    token_path = os.path.join(cwd, 'token.txt')
    if not os.path.isfile(token_path):
        msg = 'Missing security token file "%s".' % token_path
        ctx.logger.debug(msg)
        raise NonRecoverableError(msg)
    with open(token_path, 'r') as f:
        return f.read()

def get_client():
    """ XXX
    This will get a LinodeClient prepared with an API Token and User-Agent
    :return: the Linode Client
    """
    return LinodeClient(token=load_token(), user_agent="Cloudify/{}".format(version))

def available_images():
    """ XXX
    image specifiers are used to provision Linodes.
    :return: a list of available image specifiers
    """
    client = get_client()
    return [d.id for d in client.images() ]


def available_regions():
    """ XXX
    region specifiers are used to provision Linodes in a particular data center ('region').
    Note: Not all options are available on all regions.
    :return: a list of available region specifiers
    """
    client = get_client()
    return [d.id for d in client.regions() ]


def available_instance_types(region):
    """ XXX
    :param region: region specifier for which to return slug sizes
    :return: all available slug sizes
    """
    client = get_client()
    return [d.id for d in client.linode.types() ]


def generate_linode_label():
    """ XXX
    :return: a name for linodes where they're not provided from the recipe
    """
    return "Cloudify-Linode"


@operation
def create(linode_label=None, region=None, image=None, instance_type='g6-nanode-1', backups=False):
    """ XXX
    Tell the API to create a linode. Note that not all combinations of options are possible
    :param linode_label: formal name
    :param region: region to choose
    :param image: image to use
    :param instance_type: size slug - this value determines RAM, CPU, bandwidth, and cost of the Linode.
    :param backups: whether to use a backup
    :return: None
    """
    def first_unless_none(param, load_func):
        if param is None:
            return load_func()[0]
        return param

    ctx.logger.info("Creating a new Linode linode.")
    ctx.logger.debug("Create operation executing with params: linode_label = '{0}', region = '{1}', image = '{2}', instance_type = '{3}', backups = '{4}'.".format(linode_label, region, image, instance_type, backups))

    if linode_label is not None:
        _label = linode_label
    else:
        _label = generate_linode_label()

    _image = first_unless_none(image, available_images())
    _region = first_unless_none(region, available_regions())
    _instance_type = first_unless_none(instance_type, available_instance_types())  # works even if user passes None

    ctx.logger.debug("Computed values for name = '{0}', image = '{1}', region = '{2}', instance_type = '{3}.'".format(_label, _image, _region, _instance_type))

    client = get_client()
    d = client.linode.instance_create(ltype=_instance_type,  region=_region, image=_image,
                      label=_label, backups=backups)
    d.create()
    # TODO need to check back later to see that the start operation has failed or succeeded or is still processing
    pass


def get_linode(linode_id):
    """ XXX
    searches all linodes for the one with the given linode_id
    :param linode_id: the one we're looking for
    :return: linode, or None
    """
    def has_id(linode):
        return linode.id == linode_id

    client = get_client()
    if linode_id is None:
        raise NonRecoverableError("linode_id is required.")
    else:
        try:
            linode = client.load(Instance, linode_id)
        except ApiError as err:
            if err.status in [403,404]:
                return None
            msg = linode_does_not_exist_for_operation("retrieve", linode_id)
            ctx.logger.debug(msg)
            raise NonRecoverableError(msg)
        else:
           return linode
 


def linode_does_not_exist_for_operation(op, linode_id):
    """ Creates an error message when Linodes are unexpectedly not found for some operation
    :param op: operation for which a Linode does not exist
    :param linode_id: id that we expected to find
    :return: a snotty message
    """
    return "Attempted to {0} a linode with id '{1}', but no \
    such Linode exists in the system.".format(op, linode_id)


@operation
def start(linode_id=None):
    """ XXX
    Starts a new Linode, if it exists, otherwise creates a new one and starts it. does not check back for success.
    :param linode_id:
    :return: None
    """
    def start_linode(linode):
        ctx.logger.debug("Executing action '{0}' for linode '{1}'..." % ["boot", str(linode)])
        linode.boot()

    if linode_id is None:
        ctx.logger.info("Creating, then starting a new linode.")
        start_linode(create())
    else:
        d = get_linode(linode_id)
        if d is None:
            msg = linode_does_not_exist_for_operation("start", linode_id)
            ctx.logger.debug(msg)
            raise NonRecoverableError(msg)
        else:
            ctx.logger.info("Starting existing linode. Linode id = '{0}'.".format(linode_id))
            start_linode(linode)

    # TODO need to check back later to see that the start operation has failed or succeeded or is still processing
    pass


@operation
def stop(linode_id):
    """ XXX
    Asks the API to destroy a linode, if it exists. Does not check back for success.
    :param linode_id:
    :return: None
    """
    d = get_linode(linode_id)
    if d is None:
        msg = linode_does_not_exist_for_operation("stop", linode_id)
        ctx.logger.debug(msg)
        raise NonRecoverableError(msg)
    else:
        ctx.logger.info("Stopping linode with linode id = '{0}'.".format(linode_id))
        d.destroy()
    # TODO need to check back later to see that the start operation has failed or succeeded or is still processing
    pass


def main():
    create()


if __name__ == '__main__':
    main()