import pandas as pd
from psutil import cpu_count
from dask import dataframe as dd
from dask.multiprocessing import get
import timeit


def pd_apply(df, myfunc, *args, **kwargs):
    def wrapped():
        df.apply(myfunc, args=args, **kwargs)
    return wrapped


def dask_apply(df, npartitions, myfunc, *args, **kwargs):
    if type(df) == pd.DataFrame:
        kwargs.pop('meta')
        tmp = df.iloc[:2,:].apply(myfunc, args=args, **kwargs)
        meta = {c: tmp[c].dtype for c in tmp.columns}
        return dd.from_pandas(df, npartitions=npartitions).apply(myfunc, *args, axis=1, **kwargs, meta=meta).compute(get=get)
    else:
        meta = kwargs.pop('meta')
        try:
            return dd.from_pandas(df, npartitions=npartitions).map_partitions(myfunc, *args, **kwargs, meta=meta).compute(get=get)
        except:
            return dd.from_pandas(df, npartitions=npartitions).map(lambda x: myfunc(x, *args, **kwargs), meta=meta).compute(get=get)
        
    
def swiftapply(df, myfunc, *args, **kwargs):
    """
    Efficiently apply any function to a pandas dataframe or series
    in the fastest available manner
    :param df: The dataframe or series to apply the function to
    :param myfunc: The function you wish to apply
    :param args: The positional arguments of the function
    :param kwargs: The key word arguments of the function
        You can also specify npartitions and dask_threshold
        npartitions will affect the speed of dask multiprocessing
        dask_threshold is the maximum allowed time (in seconds) for a normal pandas apply
            before switching to a dask operation
    :return: The new dataframe/series with the function applied as quickly as possible
    """
    if 'npartitions' in kwargs.keys():
        npartitions = kwargs.pop('npartitions')
    else:
        npartitions = cpu_count() * 2
    if 'dask_threshold' in kwargs.keys():
        dask_threshold = kwargs.pop('dask_threshold')
    else:
        dask_threshold = 1
    
    if myfunc is not str:
        try:
            return myfunc(df, *args, **kwargs)
        except: 
            try:
                samp = df.iloc[:1000]
            except:
                samp = df.iloc[:df.shape[0]/10]

            wrapped = pd_apply(samp, myfunc, *args, **kwargs)
            n_repeats = 3
            timed = timeit.timeit(wrapped, number=n_repeats)
            samp_proc_est = timed/n_repeats
            est_apply_duration = samp_proc_est / len(samp) * df.shape[0]

            kwargs['meta'] = df.iloc[:2].apply(myfunc, *args, **kwargs)
            if (est_apply_duration > dask_threshold): 
                return dask_apply(df, npartitions, myfunc, *args, **kwargs)
            else:
                kwargs.pop('meta')
                return df.apply(myfunc, args=args, **kwargs)
    else:
        return df.astype(str)
