from io import StringIO
import sys


def main(cache, key):
    if key is None:
        # handle all cache keys
        pass

    file_extension = key[key.rindex("."):]
    print(f'{key=}')
    print(f'{file_extension=}')
    print(f'{cache=}')
    if key in cache.keys():
        item = cache[key]
    else:
        return {'result': 'cache key not found'}

    if file_extension == '.json':
        print(f'{item=}')
        return item

    if file_extension == '.parquet':
        old_stdout = sys.stdout
        sys.stdout = my_stdout = StringIO()
        item.info()
        sys.stdout = old_stdout
        item_stats = my_stdout.getvalue()
        return item, item_stats
