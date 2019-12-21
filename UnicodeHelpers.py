# -*- coding:utf-8 -*-

# From
# https://stackoverflow.com/questions/30069846/how-to-find-out-chinese-or-japanese-character-in-a-string-in-python

ranges = [
  {"from": ord(u"\u3300"), "to": ord(u"\u33ff")},         # compatibility ideographs
  {"from": ord(u"\ufe30"), "to": ord(u"\ufe4f")},         # compatibility ideographs
  {"from": ord(u"\uf900"), "to": ord(u"\ufaff")},         # compatibility ideographs
  {"from": ord(u"\U0002F800"), "to": ord(u"\U0002fa1f")}, # compatibility ideographs
  {'from': ord(u'\u3040'), 'to': ord(u'\u309f')},         # Japanese Hiragana
  {"from": ord(u"\u30a0"), "to": ord(u"\u30ff")},         # Japanese Katakana
  {"from": ord(u"\u2e80"), "to": ord(u"\u2eff")},         # cjk radicals supplement
  {"from": ord(u"\u4e00"), "to": ord(u"\u9fff")},
  {"from": ord(u"\u3400"), "to": ord(u"\u4dbf")},
  {"from": ord(u"\U00020000"), "to": ord(u"\U0002a6df")},
  {"from": ord(u"\U0002a700"), "to": ord(u"\U0002b73f")},
  {"from": ord(u"\U0002b740"), "to": ord(u"\U0002b81f")},
  {"from": ord(u"\U0002b820"), "to": ord(u"\U0002ceaf")}  # included as of Unicode 8.0
]

katakanaRange = {"from": ord(u"\u30a0"), "to": ord(u"\u30ff")} # Japanese Katakana

# "The Alphabet"
latinRanges = [
  {"from": ord(u"\u0042"), "to": ord(u"\u005a")}, # Uppercase A-Z
  {"from": ord(u"\u0061"), "to": ord(u"\u007a")} # Lowercase a-z
]
  

def is_cjk(char):
  return any([range["from"] <= ord(char) <= range["to"] for range in ranges])

def is_katakana(char):
  return katakanaRange["from"] <= ord(char) <= katakanaRange["to"]

def is_latin(char):
  return any([range["from"] <= ord(char) <= range["to"] for range in latinRanges])

def cjk_substrings(string):
  i = 0
  while i<len(string):
    if is_cjk(string[i]):
      start = i
      while is_cjk(string[i]): i += 1
      yield string[start:i]
    i += 1

if __name__ == '__main__':
  string = "sdf344asfasf天地方益3権sdfsdf"
  for sub in cjk_substrings(string):
    string = string.replace(sub, "(" + sub + ")")
  print(string)
  katakanaStr = 'ボーリング'
  for char in katakanaStr:
    print("{} is katakana: {}".format(char, is_katakana(char)))
  testStr = 'this is ボーリング'
  for char in testStr:
    print("{} is latin: {}".format(char, is_latin(char)))
