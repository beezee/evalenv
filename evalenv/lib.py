from abc import abstractmethod, ABC
from typing import Callable, Generic, TypeVar

Writer = TypeVar("Writer")
Reader = TypeVar("Reader")
State = TypeVar("State")
Error = TypeVar("Error")

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
D = TypeVar("D")

class foldEither(Generic[A, B, C]):
  
  def __init__(
    self, left: Callable[[A], C], right: Callable[[B], C]
  ) -> None:
    self.left = left
    self.right = right

  def __call__(self, either: "Either[A, B]") -> C:
    if isinstance(either, Left):
      return self.left(either.left)
    elif isinstance(either, Right):
      return self.right(either.right)
    raise TypeError("Args must be of type Either")

class Either(Generic[A, B]):

  def fold(self,
    left: Callable[[A], C],
    right: Callable[[B], C]
  ) -> C:
    return foldEither[A, B, C](left, right)(self)

  def bindApply(
    self, either: "Either[A, C]", fn: Callable[[B, C], "Either[A, D]"]
  ) -> "Either[A, D]":
    return foldEither[A, B, Either[A, D]](
      lambda e: Left(e),
      lambda b: foldEither[A, C, Either[A, D]](
        lambda e: Left(e),
        lambda c: fn(b, c))(either))(self)

  def apply(
    self, either: "Either[A, C]", fn: Callable[[B, C], D]
  ) -> "Either[A, D]":
    return self.bindApply(either, lambda b, c: Right(fn(b, c)))

class Left(Either[A, B]):

  def __init__(self, left: A) -> None:
    self.left = left

  def __str__(self) -> str:
    return f"Left({self.left})"

class Right(Either[A, B]):

  def __init__(self, right: B) -> None:
    self.right = right

  def __str__(self) -> str:
    return f"Right({self.right})"

class Write(Generic[Writer, Error]):

  def __init__(
    self, 
    tell: Callable[[Writer], None],
    writer: Callable[[], Writer],
    err: Callable[[Writer, Error], Writer]
  ) -> None:
    self.tell = tell
    self.writer = writer
    self.err = err
  
  def tell_error(self, err: Error) -> None:
    return self.tell(self.err(self.writer(), err))

  def contramap_error(
    self, fn: Callable[[A], Error]
  ) -> "Write[Writer, A]":
    return Write(
      self.tell,
      self.writer,
      lambda w, a: self.err(w, fn(a))
    )

  def dimap(
    self, pre: Callable[[A], Writer], post: Callable[[Writer], A]
  ) -> "Write[A, Error]":
    return Write(
      lambda a: self.tell(pre(a)),
      lambda: post(self.writer()),
      lambda w, e: post(self.err(pre(w), e))
    )
    

class EvalEnv(Generic[Reader, Writer, State, Error], ABC):
  def __init__(self,
    ask: Callable[[], Reader],
    write: Write[Writer, Error],
    get: Callable[[], State],
    put: Callable[[State], None],
    handle: Callable[[Exception], Error],
  ) -> None:
    self.ask = ask
    self.write = write
    self.get = get
    self.put = put
    self.handle = handle

  def modify(self, fn: Callable[[State], State]) -> None:
    return self.put(fn(self.get()))

  def map_reader(
    self, fn: Callable[[Reader], A]
  ) -> "EvalEnv[A, Writer, State, Error]":
    return EvalEnv(
        lambda: fn(self.ask()), 
        self.write,
        self.get,
        self.put,
        self.handle
    )

  def dimap_writer(
    self, fn: Callable[[Write[Writer, Error]], Write[A, Error]]
  ) -> "EvalEnv[Reader, A, State, Error]":
    return EvalEnv(
      self.ask,
      fn(self.write),
      self.get,
      self.put,
      self.handle
    )

  def dimap_state(
    self, pre: Callable[[A], State], post: Callable[[State], A]
  ) -> "EvalEnv[Reader, Writer, A, Error]":
    return EvalEnv(
      self.ask,
      self.write,
      lambda: post(self.get()),
      lambda s: self.put(pre(s)),
      self.handle
    )

  def dimap_error(
    self, pre: Callable[[A], Error], post: Callable[[Error], A]
  ) -> "EvalEnv[Reader, Writer, State, A]":
    return EvalEnv(
      self.ask,
      self.write.contramap_error(pre),
      self.get,
      self.put,
      lambda e: post(self.handle(e))
    )

  def tap_error(
    self, fn: Callable[[Exception], None]
  ) -> "EvalEnv[Reader, Writer, State, Error]":
    def tapped(e: Exception) -> Error:
      fn(e)
      return self.handle(e)
    return EvalEnv(
      self.ask,
      self.write,
      self.get,
      self.put,
      tapped
    )

  def eval(
    self, args: A, writer: Callable[[Writer, A], Writer], 
    fn: Callable[[A], B]
  ) -> Either[Error, B]:
    try:
      self.write.tell(writer(self.write.writer(), args))
      return Right(fn(args))
    except Exception as e:
      handled = self.handle(e)
      self.write.tell_error(handled)
      return Left(handled)

  def bindEval(
    self, args: Either[Error, A], 
    writer: Callable[[Writer, A], Writer],
    fn: Callable[[A], B]
  ) -> Either[Error, B]:
    return args.fold(
      lambda e: Left(e),
      lambda a: self.eval(a, writer, fn)
    )

  def log(
    self, args: A, writer: Callable[[Writer, A], Writer]
  ) -> Either[Error, None]:
    return self.eval(args, writer, lambda a: None)

  def bindLog(
    self, args: Either[Error, A], writer: Callable[[Writer, A], Writer]
  ) -> Either[Error, None]:
    return self.bindEval(args, writer, lambda a: None)
    
  def readEval(
    self, args: A, 
    writer: Callable[[Reader], Callable[[Writer, A], Writer]],
    fn: Callable[[Reader], Callable[[A], B]]
  ) -> Either[Error, B]:
    return self.eval(args, writer(self.ask()), fn(self.ask()))

  def bindReadEval(
    self, args: Either[Error, A], 
    writer: Callable[[Reader], Callable[[Writer, A], Writer]],
    fn: Callable[[Reader], Callable[[A], B]]
  ) -> Either[Error, B]:
    return self.bindEval(args, writer(self.ask()), fn(self.ask()))
