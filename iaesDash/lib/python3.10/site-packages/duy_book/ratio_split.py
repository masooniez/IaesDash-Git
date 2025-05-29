from torch.utils.data import random_split
def ratio_split(dataset, ratios):
  assert sum(ratios) == 1
  lengths = [int(r*len(dataset)) for r in ratios]
  lengths[-1] += len(dataset) - sum(lengths)
  return random_split(dataset, lengths)