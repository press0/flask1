import json
import os
import os.path
import sys
import glob
import boto3
import pandas as pd

DEBUG = True
LOCAL_DATA_DIR = '../data/'

AWS_DATA_DIR = 'idh/'
AWS_BUCKET_NAME = 'lgima-dev-3pdh-data-bucket'


def get_cache_item_from_remote_file(path):
    """ :param path: relative path including file name under LOCAL_DATA_DIR """
    try:
        s3 = boto3.client('s3',
                          aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                          aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                          )
        print('copy remote object s3://' +
              f'{AWS_BUCKET_NAME + "/" + AWS_DATA_DIR + path}' +
              ' to local file ' + f'{LOCAL_DATA_DIR + path}')
        s3.download_file(AWS_BUCKET_NAME, AWS_DATA_DIR + path, LOCAL_DATA_DIR + path)
        return get_cache_item_from_local_file(path)
    except Exception as e:
        print(f'local file not found {path} {e}')
        return None


def get_cache_item_from_local_file(path):
    """ :param path: relative path including file name under LOCAL_DATA_DIR """
    file_name, file_extension = os.path.splitext(path)
    # todo: size, date

    if file_extension == '.json':
        try:
            f = open(LOCAL_DATA_DIR + path)
            file_content = json.load(f)
            cache_entry = {path: file_content}
            return cache_entry
        except Exception as e:
            print(f'local file not found {path}')
            return None
    elif file_extension == '.parquet':
        try:
            file_content = pd.read_parquet(LOCAL_DATA_DIR + path, engine='pyarrow')
            cache_entry = {path: file_content}
            return cache_entry
        except Exception as e:
            print(f'local file not found {path} {e}')
            return None


def validate_file_extension(path):
    if path is None or len(path) < 3:
        valid = False
        return_val = {'exception': f'bad path {path}'}
        return valid, return_val
    else:
        file_name, file_extension = os.path.splitext(path)
    if file_extension != '.json' and file_extension != '.parquet':
        valid = False
        return_val = {'exception': f'file type {file_extension} not yet supported'}
    else:
        valid = True
        return_val = None
        return valid, return_val


def validate_file_exists(path):
    if os.path.isfile(LOCAL_DATA_DIR + path):
        return True, None
    else:
        return False, f'file does not exist {LOCAL_DATA_DIR + path}'


def delete_file(path):
    try:
        os.remove(LOCAL_DATA_DIR + path)
        return True, None
    except OSError as e:
        return False, f'error deleting file {LOCAL_DATA_DIR + path} {e}'


def evict_cache_entry(path):
    del s3cache[path]
    print(f'cache entry evicted {path}')
    valid, return_val = validate_file_exists(path)
    if valid:
        valid, return_val = delete_file(path)
        if valid:
            print(f'file deleted {path}')
        else:
            print(f'file not deleted {path} {return_val}')
    else:
        print(f'{return_val}')
        return valid, return_val


def debug(valid, return_val):
    if DEBUG:
        print(f'valid:{valid} return_val:{return_val}')


def delete(path):
    if path in s3cache:
        valid, return_val = evict_cache_entry(path)
    else:
        valid = False
        return_val = 'cache_item not found'
    if valid:
        return_val = {'cache_item deleted': path}
        debug(valid, return_val)
        return return_val if valid else {'error': return_val}


def read(path):
    if path in s3cache:
        valid = True
        return_val = s3cache.get(path)
        print('cache hit, key=' + f'{path}')
    else:
        cache_item = get_cache_item_from_local_file(path)
        if cache_item is not None:
            s3cache.update(cache_item)
            valid = True
            return_val = s3cache.get(path)
            print('cache update from local, key=' + f'{LOCAL_DATA_DIR + path}')
        else:
            cache_item = get_cache_item_from_remote_file(path)
            if cache_item is not None:
                s3cache.update(cache_item)
                valid = True
                return_val = s3cache.get(path)
                print('cache update from remote, key=' + f'{AWS_DATA_DIR + path}')
            else:
                valid = False
                return_val = 'remote file not found ' + f'{AWS_DATA_DIR + path}'
                print(return_val)
    debug(valid, return_val)
    return return_val if valid else {'error': return_val}


def head(path, options):
    telemetry_path = os.path.join(os.getcwd(), '') if path is None else os.path.join(path, '')  # trailing slash
    telemetry_recursive_option = False if options is None else True
    return_val = {}
    cache = []
    local_data_files = []
    telemetry = []
    for key in s3cache.keys():
        cache.append(key)
    return_val['cache'] = cache
    return_val['memory'] = sys.getsizeof(s3cache)
    for filename in glob.iglob(LOCAL_DATA_DIR + '**', recursive=True):
        local_data_files.append(filename)
    return_val['local_data_files'] = local_data_files
    for filename in glob.iglob(telemetry_path + '**', recursive=telemetry_recursive_option):
        telemetry.append(filename)
    return_val['telemetry'] = telemetry
    return return_val


def get(path=None, command='read', options=None):
    if command == 'head':
        print(f'path {path} command {command} options {options}')
        return head(path, options)
    valid, return_val = validate_file_extension(path)
    print(f'valid {valid} path {path} command {command} options {options}')
    if not valid:
        return return_val
    if command == 'read':
        return read(path)
    if command == 'delete':
        return delete(path)

dummy_content1 = {'foo': 'bar', 'foobar': 1}
dummy_content2 = {'foo': 'bar', 'nested': dummy_content1}
s3cache = {'file1.json': dummy_content1, 'file3.json': {'foo': 'bar', 'nested': dummy_content2}}

if __name__ == '__main__':
    if len(sys.argv) == 2:
        get(sys.argv[1])
elif len(sys.argv) == 3:
    get(sys.argv[1], sys.argv[2])
else:
    print('unexpected')
