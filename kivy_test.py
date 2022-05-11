import threading
import time

def decorate(method):
    def inner(self):
        a = self.a
        if a == 2:
            self.a = 0
        method(self)
        self.a = a

    return inner

class test_class:
    def __init__(self, a=2):
        self.a = a

    @decorate
    def do(self):
        print(self.a)


a=test_class(10)
#a.do()

#a=test_class(2)
#a.do()
def timer():
    return threading.Timer(5, a.do())

t = timer()
t.start()
t.cancel()
t = timer()
t.start()
t.cancel()
t = timer()
t.start()


