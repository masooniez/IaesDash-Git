from tqdm.notebook import tqdm
class tqdn():
  def __init__(self, list):
    self.tqdm = tqdm(list)
  def __iter__(self):
    for item in self.tqdm:
      yield self.tqdm, item