import sys


def run(ns):
    failed = 0
    for name, fn in sorted(ns.items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except BaseException as e:
                failed += 1
                print("FAIL", name, "-", type(e).__name__, e)
    if failed:
        print(failed, "failed")
        sys.exit(1)
    print("all passed")
