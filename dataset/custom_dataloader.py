from __future__ import print_function
import torchvision
from torch.utils.data import DataLoader
from torchvision import transforms
import torch
from torch import *


class MyIter(object):
  """An iterator."""
  def __init__(self, my_loader):
    self.my_loader = my_loader
    self.loader_iters = [iter(loader) for loader in self.my_loader.loaders]

  def __iter__(self):
    return self

  def __next__(self):
    # When the shortest loader (the one with minimum number of batches)
    # terminates, this iterator will terminates.
    # The `StopIteration` raised inside that shortest loader's `__next__`
    # method will in turn gets out of this `__next__` method.
    batches = [loader_iter.next() for loader_iter in self.loader_iters]
    return self.my_loader.combine_batch(batches)

  # Python 2 compatibility
  next = __next__

  def __len__(self):
    return len(self.my_loader)

  
class MyLoader(object):
  """This class wraps several pytorch DataLoader objects, allowing each time 
  taking a batch from each of them and then combining these several batches 
  into one. This class mimics the `for batch in loader:` interface of 
  pytorch `DataLoader`.
  Args: 
    loaders: a list or tuple of pytorch DataLoader objects
  """
  def __init__(self, loaders):
    self.loaders = loaders

  def __iter__(self):
    return MyIter(self)

  def __len__(self):
    return min([len(loader) for loader in self.loaders])

  # Customize the behavior of combining batches here.
  def combine_batch(self, batches):
    t = torch.stack(batches, dim=0).pin_memory()
    return t

