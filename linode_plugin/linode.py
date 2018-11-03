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

from linode_api4 import LinodeClient

from cloudify import ctx, Version
from cloudify.decorators import operation
# from cloudify.exceptions import RecoverableError

from . import common


CREDENTIALS_FILE_PATHS = [
    os.path.join(os.path.expanduser('~'), '.cloudify', 'credentials'),
    os.path.join(os.sep, 'etc', 'cloudify', 'credentials')
]


# Allow, in plugin.yaml, to provide the number of retries and retry interval
# (and maybe logic) for an operation. This should be in Cloudify


@operation
def create(args, **_):
    """Create a linode

    if existing resource provided:
        if the resource actually exists:
            use it
        else:
            if create if missing:
                create the resource
            else:
                fail since it doesn't exist but should
    else:
        assert quota if possible
        create resource even if one already exists of the same name(property)
        verify created
        use the created resource
    set the resource's context (the resource will have a uuid, instance_id, node_id, deployment_id and blueprint_id)  # NOQA
    set the resource's properties
    """
    # TODO: look for an available linode of the same type if it exists
    # and use that instead if a property is provided where the user asks
    # to `find_existing_resource`

    # TODO: should this be abstracted?
    credentials = _get_credentials(args)

    linode = _create_linode(args, credentials)
    if not _linode_created(linode):
        ctx.abort_operation('Failed to create resource')
    _use_resource(linode.id)
    _set_linode_context()
    _set_linode_properties(linode)


@operation
def delete(args, **_):
    """Destroy a linode

    if the resource wasn't created by us:
        if user asks to delete externally provisioned resources:
            delete resource
    else:
        get the resource
        delete it
        verify that it was deleted
    """
    credentials = _get_credentials(args)

    resource_id = ctx.instance.runtime_properties['resource_id']
    _delete_linode(resource_id, credentials)


@operation
def stop(args, **_):
    """Shutdown a linode

    get the resource
    stop it
    verify that it's stopped
    """
    credentials = _get_credentials(args)

    resource_id = ctx.instance.runtime_properties['resource_id']
    _stop_linode(resource_id, credentials)
    # TODO: try power_off if shutdown is not successful


@operation
def start(args, **_):
    """Power a linode on

    get the resource
    stop it
    verify that it's stopped
    """
    credentials = _get_credentials(args)

    resource_id = ctx.instance.runtime_properties['resource_id']
    _start_linode(resource_id, credentials)


def _create_linode(args, token):
    ctx.logger.info('Creating Linode...')
    ctx.logger.debug('Linode arguments: {0}'.format(args))

    linode = linode.Linode(
        token=token,
        name=args.get('name', _generate_name()),
        region=args['region'],
        image=args['image'],
        instance_type=args['instance_type'],
        backups=args.get('backups', True))
    linode.create()

    return linode


def _delete_linode(resource_id, credentials):
    ctx.logger.info('Destroying linode...')
    linode = _get_linode(resource_id, credentials)
    if linode:
        linode.destroy()
        _assert_completed(linode)
    if _get_linode(resource_id, credentials):
        raise ctx.abort_operation('Linode not destroyed')
    else:
        ctx.logger.info('Linode destroyed successfully')


def _stop_linode(resource_id, credentials):
    ctx.logger.info('Shutting linode down...')
    linode = _get_linode(resource_id, credentials)
    if linode:
        linode.shutdown()
        _assert_completed(linode)


def _start_linode(resource_id, credentials):
    ctx.logger.info('Powering linode on...')
    linode = _get_linode(resource_id, credentials)
    if linode:
        linode.power_on()
        _assert_completed(linode)


def _use_resource(resource_id):
    ctx.logger.info('Using resource {0}...'.format(resource_id))
    ctx.instance.runtime_properties['resource_id'] = resource_id


def _get_linode(resource_id, token):
    manager = linode.Manager(token=token)
    for linode in manager.get_all_linodes():
        if linode.id == resource_id:
            return linode
    return None


def _linode_created(linode, args):
    return _assert_completed(linode)


def _set_linode_context():
    ctx.logger.debug('Setting linode context...')
    ctx.instance.runtime_properties['resource_context'] = dict(
        uuid=str(uuid.uuid4()),
        node_instance_id=ctx.node_instance.id,
        node_id=ctx.node.id,
        deployment_id=ctx.deployment.id,
        blueprint_id=ctx.blueprint.id,
    )


def _set_linode_properties(linode):
    ctx.logger.debug('Setting linode properties...')
    # TODO: Make this idempotent (well.. it is.. but.. really)
    ctx.instance.runtime_properties['resource_properties'] = dict(
        # The id is assigned above. Even though it's a property of
        # the resource, we shouldn't have two sources or truth
        label=linode.label,
        image=linode.image.id,
        type=linode.type.id,
        region=linode.region.id,
        disk=linode.specs.disk,
        memory=linode.specs.memory,
        vcpus=linode.specs.vcpus,
        tags=linode.tags,
        created=linode.created,
        backups=linode.backups.enabled)


def _assert_completed(linode):
    linode_status = _get_linode_status(linode)
    if linode_status == 'shutting_down':
        ctx.operation.retry(
            message='Waiting for operation to complete. Retrying...',
            retry_after=30)
    elif linode_status == 'offline':
        ctx.logger.info('Linode shutdown successfully')
    else:
        ctx.abort_operation('Linode shutdown failed')


def _get_linode_status(linode):
    return linode.status


def _get_credentials(args):
    credentials = args.get('token')
    credentials = credentials or \
        common._get_credentials('linode').get('token')
    if not credentials:
        ctx.abort_operation(
            'Could not retrieve credentials. '
            'You should either supply credentials in the blueprint, '
            'provide a credentials file to look in or have credential files '
            'under one of: {0}'.format(CREDENTIALS_FILE_PATHS))


def _get_client():
    """ XXX
    This will get a LinodeClient prepared with an API Token and User-Agent
    :return: the Linode Client
    """
    return LinodeClient(token=_get_credentials(), user_agent="Cloudify/{}".format(version))


def _generate_name():
    return 'test-linode'
