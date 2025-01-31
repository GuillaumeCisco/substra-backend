import argparse
import os
import json
import shutil
import tempfile
import time
import zipfile
import logging

import substra

from termcolor import colored

logging.basicConfig(filename='populate.log',
                    format='[%(asctime)-15s: %(levelname)s] %(message)s')

dir_path = os.path.dirname(os.path.realpath(__file__))

USER, PASSWORD = ('admin', 'admin')
SUBSTRA_FOLDER = os.getenv('SUBSTRA_PATH', '/substra')
server_path = f'{SUBSTRA_FOLDER}/servermedias'

client = substra.Client()


PUBLIC_PERMISSIONS = {'public': True, 'authorized_ids': []}


def setup_config(network='docker'):
    print('Init config in /tmp/.substrabac for owkin and chunantes')
    if network == 'docker':
        client.add_profile('owkin', 'http://owkin.substrabac:8000', '0.0',
                           user=USER, password=PASSWORD)
        client.add_profile('chunantes', 'http://chunantes.substrabac:8001', '0.0',
                           user=USER, password=PASSWORD)
        client.add_profile('clb', 'http://clb.substrabac:8002', '0.0',
                           user=USER, password=PASSWORD)
    if network == 'skaffold':
        # the usernames and passwords are defined in the skaffold.yaml file
        client.add_profile('owkin', 'http://substrabac.node-1', '0.0',
                           user='node-1', password='node-1pwd')
        client.add_profile('chunantes', 'http://substrabac.node-2', '0.0',
                           user='node-2', password='node-2pwd')
        client.add_profile('clb', 'http://substrabac.node-3', '0.0',
                           user='node-3', password='node-3pwd')


def zip_folder(path, destination):
    zipf = zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(path):
        for f in files:
            abspath = os.path.join(root, f)
            archive_path = os.path.relpath(abspath, start=path)
            zipf.write(abspath, arcname=archive_path)
    zipf.close()


def get_or_create(data, profile, asset, local=True):

    client.set_profile(profile)

    method_kwargs = {}
    if not local:
        method_kwargs['local'] = False

    method = getattr(client, f'add_{asset}')

    try:
        r = method(data, **method_kwargs)

    except substra.exceptions.AlreadyExists as e:
        print(colored(e, 'cyan'))
        key_or_keys = e.pkhash

    else:
        print(colored(json.dumps(r, indent=2), 'green'))

        key_or_keys = [x.get('pkhash', x.get('key'))
                       for x in r] if isinstance(r, list) else r.get('pkhash', r.get('key'))

    return key_or_keys


def update_datamanager(data_manager_key, data, profile):
    client.set_profile(profile)
    try:
        r = client.update_dataset(data_manager_key, data)

    except substra.exceptions.InvalidRequest as e:
        # FIXME if the data manager is already associated with the objective
        #       backend answer with a 400 and a raw error coming from the
        #       ledger.
        #       this case will be handled soon, with the fabric SDK.
        print(colored(str(e), 'red'))

    else:
        print(colored(json.dumps(r, indent=2), 'green'))


def do_populate():

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-o', '--one-org', action='store_const', dest='nb_org', const=1,
                       help='Launch populate with one org')
    group.add_argument('-tw', '--two-orgs', action='store_const', dest='nb_org', const=2,
                       help='Launch populate with two orgs')
    group.add_argument('-th', '--three-orgs', action='store_const', dest='nb_org', const=3,
                       help='Launch populate with three orgs')
    parser.add_argument('-a', '--archive', action='store_true',
                        help='Launch populate with archive data samples only')
    parser.add_argument('-s', '--skaffold', action='store_true',
                        help='Launch populate with skaffold (K8S) network')
    parser.set_defaults(nb_org=2)
    args = vars(parser.parse_args())

    network_type = 'skaffold' if args['skaffold'] else 'docker'
    setup_config(network_type)

    if args['nb_org'] == 1:
        org_0 = org_1 = org_2 = 'owkin'
    elif args['nb_org'] == 2:
        org_0 = org_2 = 'owkin'
        org_1 = 'chunantes'
    elif args['nb_org'] == 3:
        org_0 = 'owkin'
        org_1 = 'chunantes'
        org_2 = 'clb'
    else:
        raise Exception(f"Number of orgs {args['nb_org']} not in [1, 2, 3]")

    print(f'will create datamanager with {org_1}')
    # create datamanager with org1
    data = {
        'name': 'ISIC 2018',
        'data_opener': os.path.join(dir_path, './fixtures/chunantes/datamanagers/datamanager0/opener.py'),
        'type': 'Images',
        'description': os.path.join(dir_path, './fixtures/chunantes/datamanagers/datamanager0/description.md'),
        'permissions': PUBLIC_PERMISSIONS,
    }
    data_manager_org1_key = get_or_create(data, org_1, 'dataset')

    ####################################################

    train_data_sample_keys = []

    if not args['archive']:
        print(f'register train data (from server) on datamanager {org_1} (will take datamanager creator as worker)')
        data_samples_path = ['./fixtures/chunantes/datasamples/train/0024306',
                             './fixtures/chunantes/datasamples/train/0024307',
                             './fixtures/chunantes/datasamples/train/0024308']
        for d in data_samples_path:
            try:
                shutil.copytree(os.path.join(dir_path, d),
                                os.path.join(server_path, d))
            except FileExistsError:
                pass
        data = {
            'paths': [os.path.join(server_path, d) for d in data_samples_path],
            'data_manager_keys': [data_manager_org1_key],
            'test_only': False,
        }
        train_data_sample_keys = get_or_create(data, org_1, 'data_samples', local=False)
    else:
        print(f'register train data on datamanager {org_1} (will take datamanager creator as worker)')
        data = {
            'paths': [
                os.path.join(dir_path, './fixtures/chunantes/datasamples/train/0024306'),
                os.path.join(dir_path, './fixtures/chunantes/datasamples/train/0024307'),
                os.path.join(dir_path, './fixtures/chunantes/datasamples/train/0024308')
            ],
            'data_manager_keys': [data_manager_org1_key],
            'test_only': False,
        }
        train_data_sample_keys = get_or_create(data, org_1, 'data_samples')

    ####################################################

    print(f'create datamanager, test data and objective on {org_0}')
    data = {
        'name': 'Simplified ISIC 2018',
        'data_opener': os.path.join(dir_path, './fixtures/owkin/datamanagers/datamanager0/opener.py'),
        'type': 'Images',
        'description': os.path.join(dir_path, './fixtures/owkin/datamanagers/datamanager0/description.md'),
        'permissions': PUBLIC_PERMISSIONS,
    }
    data_manager_org0_key = get_or_create(data, org_0, 'dataset')

    print(f'create datamanager, test data and objective on {org_1} (should say "already exists")')
    data = {
        'name': 'Simplified ISIC 2018',
        'data_opener': os.path.join(dir_path, './fixtures/owkin/datamanagers/datamanager0/opener.py'),
        'type': 'Images',
        'description': os.path.join(dir_path, './fixtures/owkin/datamanagers/datamanager0/description.md'),
        'permissions': PUBLIC_PERMISSIONS,
    }
    get_or_create(data, org_1, 'dataset')

    ####################################################

    print('register test data')
    data = {
        'paths': [
            os.path.join(dir_path, './fixtures/owkin/datasamples/test/0024900'),
            os.path.join(dir_path, './fixtures/owkin/datasamples/test/0024901')
        ],
        'data_manager_keys': [data_manager_org0_key],
        'test_only': True,
    }
    test_data_sample_keys = get_or_create(data, org_0, 'data_samples')

    ####################################################

    print('register test data 2')
    data = {
        'paths': [
            os.path.join(dir_path, './fixtures/owkin/datasamples/test/0024902'),
            os.path.join(dir_path, './fixtures/owkin/datasamples/test/0024903')
        ],
        'data_manager_keys': [data_manager_org0_key],
        'test_only': True,
    }
    get_or_create(data, org_0, 'data_samples')

    ####################################################

    print('register test data 3')
    data = {
        'paths': [
            os.path.join(dir_path, './fixtures/owkin/datasamples/test/0024904'),
            os.path.join(dir_path, './fixtures/owkin/datasamples/test/0024905')
        ],
        'data_manager_keys': [data_manager_org0_key],
        'test_only': True,
    }
    get_or_create(data, org_0, 'data_samples')

    ####################################################

    with tempfile.TemporaryDirectory() as tmp_dir:
        print('register objective')
        objective_path = os.path.join(
            dir_path, './fixtures/chunantes/objectives/objective0/')

        zip_path = os.path.join(tmp_dir, 'metrics.zip')
        zip_folder(objective_path, zip_path)
        data = {
            'name': 'Skin Lesion Classification Objective',
            'description': os.path.join(dir_path, './fixtures/chunantes/objectives/objective0/description.md'),
            'metrics_name': 'macro-average recall',
            'metrics': zip_path,
            'permissions': PUBLIC_PERMISSIONS,
            'test_data_sample_keys': test_data_sample_keys,
            'test_data_manager_key': data_manager_org0_key
        }

        objective_key = get_or_create(data, org_0, 'objective')

        ####################################################

        print('register objective without data manager and data sample')
        objective_path = os.path.join(
            dir_path, './fixtures/chunantes/objectives/objective0/')

        zip_path = os.path.join(tmp_dir, 'metrics2.zip')
        zip_folder(objective_path, zip_path)
        data = {
            'name': 'Skin Lesion Classification Objective',
            'description': os.path.join(dir_path, './fixtures/owkin/objectives/objective0/description.md'),
            'metrics_name': 'macro-average recall',
            'metrics': zip_path,
            'permissions': PUBLIC_PERMISSIONS,
        }

        get_or_create(data, org_0, 'objective')

    ####################################################

    # update datamanager
    print('update datamanager')
    data = {
        'objective_key': objective_key
    }
    update_datamanager(data_manager_org1_key, data, org_0)

    ####################################################

    # register algo
    print('register algo')
    data = {
        'name': 'Logistic regression',
        'file': os.path.join(dir_path, './fixtures/chunantes/algos/algo3/algo.tar.gz'),
        'description': os.path.join(dir_path, './fixtures/chunantes/algos/algo3/description.md'),
        'permissions': PUBLIC_PERMISSIONS,
    }
    algo_key = get_or_create(data, org_2, 'algo')

    ####################################################

    print('register algo 2')
    data = {
        'name': 'Neural Network',
        'file': os.path.join(dir_path, './fixtures/chunantes/algos/algo0/algo.tar.gz'),
        'description': os.path.join(dir_path, './fixtures/chunantes/algos/algo0/description.md'),
        'permissions': PUBLIC_PERMISSIONS,
    }
    algo_key_2 = get_or_create(data, org_1, 'algo')

    ####################################################

    data = {
        'name': 'Random Forest',
        'file': os.path.join(dir_path, './fixtures/chunantes/algos/algo4/algo.tar.gz'),
        'description': os.path.join(dir_path, './fixtures/chunantes/algos/algo4/description.md'),
        'permissions': PUBLIC_PERMISSIONS,
    }
    algo_key_3 = get_or_create(data, org_1, 'algo')

    ####################################################

    # create traintuple
    print('create traintuple')
    data = {
        'algo_key': algo_key,
        'objective_key': objective_key,
        'data_manager_key': data_manager_org1_key,
        'train_data_sample_keys': train_data_sample_keys[:2]
        # This traintuple should succeed.
        # It doesn't have a tag, so it can be used as a test
        # of the "non-bundled" display in substra-frontend.
    }
    traintuple_key = get_or_create(data, org_1, 'traintuple')

    print('create second traintuple')
    data = {
        'algo_key': algo_key_2,
        'data_manager_key': data_manager_org1_key,
        'objective_key': objective_key,
        'train_data_sample_keys': train_data_sample_keys[:2],
        'tag': '(should fail) My super tag'
    }

    get_or_create(data, org_1, 'traintuple')

    print('create third traintuple')
    data = {
        'algo_key': algo_key_3,
        'data_manager_key': data_manager_org1_key,
        'objective_key': objective_key,
        'train_data_sample_keys': train_data_sample_keys[:2],
        'tag': '(should fail) My other tag'
    }

    get_or_create(data, org_1, 'traintuple')

    ####################################################

    client.set_profile(org_1)
    res = client.get_traintuple(traintuple_key)
    print(colored(json.dumps(res, indent=2), 'green'))

    # create testtuple
    print('create testtuple')
    data = {
        'traintuple_key': traintuple_key,
        'tag': 'substra',
    }

    testtuple_key = get_or_create(data, org_1, 'testtuple')

    client.set_profile(org_1)
    res_t = client.get_testtuple(testtuple_key)
    print(colored(json.dumps(res_t, indent=2), 'yellow'))

    testtuple_status = None
    traintuple_status = None

    client.set_profile(org_1)

    while traintuple_status not in ('done', 'failed') or testtuple_status not in ('done', 'failed'):
        res = client.get_traintuple(traintuple_key)
        res_t = client.get_testtuple(testtuple_key)
        if traintuple_status != res['status'] or testtuple_status != res_t['status']:
            traintuple_status = res['status']
            testtuple_status = res_t['status']
            print('')
            print('-' * 100)
            print(colored(json.dumps(res, indent=2), 'green'))
            print(colored(json.dumps(res_t, indent=2), 'yellow'))
        else:
            print('.', end='', flush=True)

        time.sleep(3)

    ####################################################
    # Compute plan

    print('create compute plan')
    traintuples_data = [
        {
            "data_manager_key": data_manager_org1_key,
            "train_data_sample_keys": [train_data_sample_keys[0], train_data_sample_keys[2]],
            "traintuple_id": "dummy_traintuple_id",
            "in_models_ids": [],
            "tag": "",
        },
    ]
    testtuples_data = [
        # {
        #     "traintuple_id": "dummy_traintuple_id",
        #     "tag": "",
        # }
    ]
    compute_plan_data = {
        "algo_key": algo_key,  # logistic regression, org2
        "objective_key": objective_key,  # org 0
        "traintuples": traintuples_data,
        "testtuples": testtuples_data,
    }
    # until both chaincode, backend and sdk can handle compute plan collisions, we need to have a
    # generic try-except so that this script can run multiple times in a row
    try:
        client.set_profile(org_1)
        res = client.add_compute_plan(compute_plan_data)
        print(colored(json.dumps(res, indent=2), 'green'))
    except:  # noqa: E722
        print(colored('Could not create compute plan', 'red'))


if __name__ == '__main__':
    try:
        do_populate()
    except substra.exceptions.HTTPError as e:
        print(colored(str(e), 'red'))
        exit(1)
