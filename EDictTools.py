import re

entryRegex = r'(.*)\s\[(.*)\]\s\/(.*)'
entryKatakanaRegex = r'(.*)\s\/(.*)'

edict = []

class EdictEntry:
    def __init__(self, word, reading, restOfEntry):
        self.word = word
        self.reading = reading
        self.restOfEntry = restOfEntry

    def __str__(self):
        return "{} = {} {}".format(self.word, self.reading, self.restOfEntry)

def findEntries(inputText):
    possibleEntries = []
    for entry in edict:
        if entry.word == inputText:
            possibleEntries.append(entry)

    if not possibleEntries:
        print('Failed to find "{}" in edict'.format(inputText))
    return possibleEntries

def loadEdict():
    global edict
    if not edict:
        print('Loading Edict...')
        edictFile = open('edict/edict', 'r', encoding='euc-jp')
        for line in edictFile:
            isKatakana = False
            entryMatch = re.search(entryRegex, line)
            if not entryMatch:
                # Loan words only have katakana readings
                entryMatch = re.search(entryKatakanaRegex, line)
                if not entryMatch:
                    print("Error: could not parse dictionary line: \n\t{}".format(line))
                    continue
                else:
                    isKatakana = True
            if isKatakana:
                edict.append(EdictEntry(entryMatch.group(1), entryMatch.group(1), entryMatch.group(2)))
            else:
                edict.append(EdictEntry(entryMatch.group(1), entryMatch.group(2), entryMatch.group(3)))
        print('Loading Edict complete. {} entries found'.format(len(edict)))
                
                
loadEdict()

if __name__ == '__main__':
    # print(findEntries('一回目')[0].reading)
    print(findEntries('日中')[0].reading)
