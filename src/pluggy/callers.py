"""
Call loop machinery
"""
import sys

from ._result import HookCallError, _Result, _raise_wrapfail


def _multicall(hook_name, hook_impls, caller_kwargs, firstresult):
    """Execute a call into multiple python functions/methods and return the
    result(s).

    ``caller_kwargs`` comes from _HookCaller.__call__().
    """
    print("PLUGGY starting _multicall()", flush=True)
    __tracebackhide__ = True
    results = []
    excinfo = None
    try:  # run impl and wrapper setup functions in a loop
        teardowns = []
        try:
            for hook_impl in reversed(hook_impls):
                try:
                    args = [caller_kwargs[argname] for argname in hook_impl.argnames]
                except KeyError:
                    for argname in hook_impl.argnames:
                        if argname not in caller_kwargs:
                            raise HookCallError(
                                "hook call must provide argument %r" % (argname,)
                            )

                if hook_impl.hookwrapper:
                    print("PLUGGY calling into {!r} from {}".format(hook_impl.function.__qualname__, hook_impl.function.__globals__["__file__"]), flush=True)
                    try:
                        gen = hook_impl.function(*args)
                        next(gen)  # first yield
                        teardowns.append(gen)
                    except StopIteration:
                        _raise_wrapfail(gen, "did not yield")
                    finally:
                        print("PLUGGY returned from {!r}".format(hook_impl.function.__qualname__), flush=True)
                else:
                    print("PLUGGY calling into {!r} from {}".format(hook_impl.function.__qualname__, hook_impl.function.__globals__["__file__"]), flush=True)
                    res = hook_impl.function(*args)
                    print("PLUGGY returned from {!r}".format(hook_impl.function.__qualname__), flush=True)
                    if res is not None:
                        results.append(res)
                        if firstresult:  # halt further impl calls
                            break
        except BaseException:
            excinfo = sys.exc_info()
    finally:
        if firstresult:  # first result hooks return a single value
            outcome = _Result(results[0] if results else None, excinfo)
        else:
            outcome = _Result(results, excinfo)

        # run all wrapper post-yield blocks
        for gen in reversed(teardowns):
            try:
                gen.send(outcome)
                _raise_wrapfail(gen, "has second yield")
            except StopIteration:
                pass

        print("PLUGGY concluded _multicall()", flush=True)
        return outcome.get_result()
