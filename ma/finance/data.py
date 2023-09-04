import zope.interface
import pandas as pd


class MyInterface(zope.interface.Interface):
    x = zope.interface.Attribute("symbol")

    def load_data(self, x):
        pass


@zope.interface.implementer(MyInterface)
class MyClass:
    def load_data(self, x):
        return x**2


obj = MyInterface()

print(obj.load_data(2))
