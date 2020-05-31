from evalenv.lib import *
from typing import Callable, List

if __name__ == '__main__':
  ask = lambda: "hi"

  class Log:
    def __init__(self, log: List[str]) -> None:
      self.log = log
    def replace(self, log: List[str]) -> None:
      self.log = log
    def add(self, line: str) -> "Log":
      self.log.append(line)
      return self

  log = Log([])
  env = EvalEnv[str, Log, None, str](
    ask, 
    Write[Log, str](
      lambda _log: log.replace(_log.log), 
      lambda: log, 
      lambda log, err: log.add(f"ERROR {err}")
    ),
    lambda: None,
    lambda _: None,
    str
  )

  r1 = env.eval(1, 
    lambda log, i: log.add(f"Adding 1 to {i}"),
    lambda x: x + 1)
  r2 = env.bindEval(r1,
    lambda log, i: log.add(f"Dividing r1: {i} by zero"),
    lambda x: x / 0)
  r3 = env.bindEval(r2,
    lambda log, i: log.add(f"Adding 1 to r2: {i}"),
    lambda x: x + 1)
  r4 = env.bindEval(r1,
    lambda log, i: log.add(f"Adding 1 to r1: {i}"),
    lambda x: x + 1)
  r5 = env.bindEval(r1.bindApply(r2, lambda n1, n2: Right(n1 + n2)),
    lambda log, i: log.add(f"Adding 1 to r1+r2: {i}"),
    lambda x: x + 1)
  r7 = env.bindEval(r1.bindApply(r4, lambda n1, n2: Right(n1 + n2)),
    lambda log, i: log.add(f"Adding 2 to r1+r4: {i}"),
    lambda x: x + 2)

  r8 = env.readEval("there", 
    lambda r: lambda log, s: log.add(f"Appending {s} to {r}"),
    lambda r: lambda s: f"{r} {s}")

  env.bindLog(r2, 
    lambda log, i: log.add(f"Logging failed result {i}"))

  env.bindLog(r4,
    lambda log, i: log.add(f"Logging successful result {i}"))

  print(r2)
  print(r5)
  print(r7)
  print(r8)

  print(env.write.writer().log)
