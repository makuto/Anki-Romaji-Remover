# -*- coding:utf-8 -*-
import argparse
import json
import romkan
import sys
import urllib.request
import UnicodeHelpers


argParser = argparse.ArgumentParser(
    description="""Automatically turn Romaji into Hiragana in an Anki deck.

This is for if you get bothered by Romaji's inaccuracy, or in my opinion, its somewhat misleading format.

This tool takes the name of a deck and the name of the field with Romaji, and converts it into Hiragana.

It preserves most anything which isn't romaji, so if you have e.g. "setsumei(suru)" it will convert it to "せつめい(する)".
"-" and "’" will be removed, however. This is because the romkan converter can get confused by these.
It doesn't hurt to run the script again on a deck which has already been wholly or partially converted.
Katakana will be output if a "written field" is provided to hint the script that it should use katakana.""")
argParser.add_argument('DeckName', type=str,
                       help='The name of the deck to modify. Add "quotes" if the name has spaces, e.g. "My Deck"')
argParser.add_argument('RomajiFieldName', type=str,
                       help='The name of the field which has Romaji you want to convert, e.g. "Front"')
argParser.add_argument('--written-field-name', type=str, dest='WrittenFieldName',
                       help='The name of the field which has what would actually be written in '
                       'realistic text (for example, kanji). This can be provided in order to '
                       'hint the converter that it should output katakana instead of hiragana, '
                       'if the word would normally be written as katakana')
argParser.add_argument('--soft-edit', action='store_const', const=True, default=False, dest='debugSoftEdit',
                       help='Do not make changes to the deck. Output all changes that would be made. '
                       'I recommend running the script with this option first, then look over the results '
                       'and confirm whether they are satisfactory.')

def formatAnkiConnectRequest(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invokeAnkiConnect(action, **params):
    requestJson = json.dumps(formatAnkiConnectRequest(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

def getNotes(deckName):
    cardsInDeck = invokeAnkiConnect('findCards', query='"deck:{}"'.format(deckName))
    if not cardsInDeck:
        print("No cards in deck '{}'".format(deckName))
        return []
    print("{} cards in deck '{}'".format(len(cardsInDeck), deckName))
    return invokeAnkiConnect('cardsToNotes', cards = cardsInDeck)

def sanitizeTextForConversion(fieldValue):
    # These confuse romkan, and aren't usually a part of the language anyhow
    return fieldValue.replace('-', ' ').replace('’', ' ')

def convertNotes(deckName, fieldToConvert, conversionHintField=None,
                 shouldEdit=True):
    notes = getNotes(deckName)
    notesInfo = invokeAnkiConnect('notesInfo', notes = notes)
    for currentNote in notesInfo:
        textToConvert = sanitizeTextForConversion(currentNote['fields'][fieldToConvert]['value'])
        
        if not textToConvert:
            print("\nWarning: Empty '{}' found in the following note, which may be malformed:".format(fieldToConvert))
            print(currentNote)
            continue
        
        hint = (sanitizeTextForConversion(currentNote['fields'][conversionHintField]['value'])
                if conversionHintField else None)

        convertedText = None

        # Chinese, Japanese, Korean
        foundCJK = False
        isAllKatakana = True
        for char in hint:
            if not UnicodeHelpers.is_katakana(char):
                isAllKatakana = False
            if UnicodeHelpers.is_cjk(char):
                foundCJK = True

        # Determine if the hint is all katakana via converting it and seeing if there is a change
        if hint:
            if isAllKatakana:
                # The hint is already all katakana; just use it. This fixes problems where romkan won't
                # convert continuations properly: from input "booringu" the converter outputs ボオリング instead of ボーリング
                convertedText = hint
            elif not foundCJK:
                # There are no Japanese characters; it's probably an initialism or acronym, e.g. 'WWW'
                # Convert to katakana
                convertedText = romkan.to_katakana(textToConvert)
                
        # It's not katakana, or we don't have a hint. All hiragana
        if not convertedText:
            convertedText = romkan.to_hiragana(textToConvert)

        # No conversion
        if not convertedText:
            print("ERROR: No conversion for text '{}'".format(textToConvert))
            continue
        
        for char in convertedText:
            if UnicodeHelpers.is_latin(char):
                print("Warning: conversion did not result in purely Japanese output. There may be "
                      "a typo in the romaji, or the romaji format is not understood.")
                break

        # Already converted
        if textToConvert == convertedText:
            continue

        if hint:
            print("'{}' -> '{}' (hint '{}')".format(currentNote['fields'][fieldToConvert]['value'], convertedText, hint))
        else:
            print("'{}' -> '{}'".format(currentNote['fields'][fieldToConvert]['value'], convertedText))
                
        if shouldEdit:
            pass

if __name__ == '__main__':
    print('Anki Romaji Remover: Convert Romaji into Hiragana')

    if len(sys.argv) == 1:
        argParser.print_help()
        exit()
    args = argParser.parse_args()

    shouldEdit = not args.debugSoftEdit
    if shouldEdit:
        answer = input("\nWARNING: This script will modify your Anki deck.\n"
                       "This script's creator is not liable for loss of data!\n"
                       "If you want to preview changes, run with --soft-edit.\n"
                       "\nHave you created a backup of your decks? (yes or no) ")
        shouldEdit = answer.lower() in ['yes', 'y']

    if not shouldEdit and not args.debugSoftEdit:
        print("Please back up your data via Anki->File->Export->Anki Collection Package")
    else:
        convertNotes(args.DeckName, args.RomajiFieldName,
                     conversionHintField=args.WrittenFieldName,
                     shouldEdit=shouldEdit and not args.debugSoftEdit)
