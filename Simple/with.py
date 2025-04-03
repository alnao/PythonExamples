# see https://www.youtube.com/watch?v=qfN6_Kv6E-Y
import time
from types import TracebackType
from typing import Self,Any,Type

class Timer:
    def __init__(self,name:str)->None :
        self.name = name
        #self.start_time = None
    def __enter__(self) -> 'Timer':
        self._start_time = time.perf_counter()
        print(f"Starting timer: {self.name}")
        return self
    def __exit__(self,exc_type:Type[BaseException] | None ,exc_value: Any | None ,traceback:TracebackType | None ) -> None:
        self._end_time : float = time.perf_counter()
        elapsed_time = self._end_time - self._start_time
        print(f"Elapse time of {self.name} is {elapsed_time:.4f} seconds")
        print(exc_type,exc_value,traceback)
        if exc_type is not None:
            print(f"An exception occurred: {exc_value}")
    def __str__(self) -> str:
        return f"Timer({self.name})"
def mainTimer() -> None:
    with Timer("My Timer") as timer:
        time.sleep(2)
        print(timer)
        #raise ValueError("An error occurred")
class FileReader :
    def __init__(self,filename:str)->None:
        self.filename = filename
    def __enter__(self) -> Self:
        self.file = open(self.filename,'r')
        return self
    def __exit__(self,exc_type:Type[BaseException] | None ,exc_value: Any | None ,traceback:TracebackType | None ) -> None:
        self.file.close()
        print(f"File {self.filename} closed")
    def read_lines(self) -> list[str]:
        return self.file.readlines()

def mainFilereader(file_path:str = "test.txt") -> None:
    print("-----------------")
    print(f"Content of the file: {file_path}" )
    with FileReader(file_path) as file_reader:
        lines = file_reader.read_lines()
        for line in lines:
            print(line.strip())
        #raise ValueError("An error occurred")

if __name__ == "__main__":
    mainTimer()
    mainFilereader("/mnt/Dati/alnao.sh")
